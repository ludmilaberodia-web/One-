// Controla a leitura: posição, avanço entre frases/trechos, pré-carregamento e troca de motor.

import { DeviceVoice, OpenAIVoice, ElevenLabsVoice } from './voices.js';

const CLOUD_CHUNK = 700;       // caracteres por requisição (bom equilíbrio entre prosódia e latência)
const CLOUD_FIRST_CHUNK = 260; // primeiro trecho menor: começa a falar mais rápido
const PREFETCH = 2;

export class Player extends EventTarget {
  constructor({ settings, audio }) {
    super();
    this.settings = settings;
    this.audio = audio;
    this.device = new DeviceVoice();
    this.cloud = {
      openai: new OpenAIVoice(audio, settings),
      elevenlabs: new ElevenLabsVoice(audio, settings),
    };
    this.flat = [];
    this.chStart = [];
    this.index = 0;
    this.playing = false;
    this.token = 0;
    this.chunk = null;
    this.cloudPaused = false;
    this.errorsInRow = 0;
    audio.addEventListener('timeupdate', () => this.onTimeUpdate());
  }

  load(book, chapters, pos = { chapter: 0, seg: 0 }) {
    // Interrompe sem emitir eventos: evita salvar a posição antiga no livro novo
    this.playing = false;
    this.token++;
    this.cloudPaused = false;
    this.chunk = null;
    this.device.stop();
    this.stopCloud();
    this.book = book;
    this.chapters = chapters;
    this.flat = [];
    this.chStart = [];
    chapters.forEach((c, ci) => {
      this.chStart.push(this.flat.length);
      c.segs.forEach((s, si) => this.flat.push({ text: s.text, ch: ci, si, para: s.para }));
    });
    const ch = Math.min(pos.chapter || 0, chapters.length - 1);
    this.index = Math.min(this.chStart[ch] + (pos.seg || 0), Math.max(0, this.flat.length - 1));
    this.emit('position', { start: this.index, end: this.index + 1 });
  }

  get engineName() {
    return this.settings().engine;
  }

  get position() {
    const s = this.flat[this.index];
    return s ? { chapter: s.ch, seg: s.si, percent: this.flat.length ? this.index / this.flat.length : 0 } : { chapter: 0, seg: 0, percent: 0 };
  }

  emit(type, detail) {
    this.dispatchEvent(new CustomEvent(type, { detail }));
  }

  // ---------- Controles ----------

  play() {
    if (!this.flat.length || this.playing) return;
    this.playing = true;
    this.emit('state', { playing: true });
    if (this.cloudPaused && this.chunk) {
      this.cloudPaused = false;
      this.currentCloud().resume().catch(() => this.restart());
      return;
    }
    this.run(++this.token);
  }

  pause() {
    if (!this.playing) return;
    this.playing = false;
    if (this.engineName !== 'device' && this.chunk && !this.audio.paused) {
      this.currentCloud().pause();
      this.cloudPaused = true;
    } else {
      this.token++;
      this.device.stop();
      this.stopCloud();
    }
    this.emit('state', { playing: false });
    this.emit('save');
  }

  toggle() {
    this.playing ? this.pause() : this.play();
  }

  stop() {
    this.playing = false;
    this.token++;
    this.cloudPaused = false;
    this.chunk = null;
    this.device.stop();
    this.stopCloud();
    this.emit('state', { playing: false });
  }

  // Reinicia a leitura na posição atual (ao trocar voz/velocidade de motor)
  restart() {
    const was = this.playing;
    this.stop();
    if (was) this.play();
  }

  seek(i) {
    const was = this.playing;
    this.stop();
    this.index = Math.max(0, Math.min(i, this.flat.length - 1));
    this.emit('position', { start: this.index, end: this.index + 1 });
    this.emit('save');
    if (was) this.play();
  }

  // Durante um trecho da nuvem, "voltar" parte da frase que está sendo dita
  currentIndex() {
    return this.estimated ?? this.index;
  }

  prev() { this.seek(this.currentIndex() - 1); }
  next() { this.seek(this.currentIndex() + 1); }

  prevChapter() {
    const s = this.flat[this.currentIndex()];
    if (!s) return;
    const start = this.chStart[s.ch];
    // Se já passou do início do capítulo, volta ao início dele; senão, ao anterior
    const target = this.currentIndex() - start > 2 || s.ch === 0 ? start : this.chStart[s.ch - 1];
    this.seek(target);
  }

  nextChapter() {
    const s = this.flat[this.currentIndex()];
    if (!s) return;
    for (let c = s.ch + 1; c < this.chapters.length; c++) {
      if (this.chapters[c].segs.length) return this.seek(this.chStart[c]);
    }
  }

  goToChapter(c) {
    this.seek(this.chStart[c] ?? 0);
  }

  // Volta/avança ~N segundos estimando pela quantidade de caracteres (≈15 caracteres/s em 1x)
  skipSeconds(sec) {
    let i = this.currentIndex();
    let chars = Math.abs(sec) * 15;
    const dir = Math.sign(sec);
    while (chars > 0 && i + dir >= 0 && i + dir < this.flat.length) {
      i += dir;
      chars -= this.flat[i].text.length;
    }
    this.seek(i);
  }

  setRate(r) {
    if (this.engineName !== 'device') this.currentCloud().setRate(r);
    else if (this.playing) this.restart(); // a voz do aparelho só aplica na próxima fala
  }

  // ---------- Loop de leitura ----------

  currentCloud() {
    return this.cloud[this.engineName] || this.cloud.openai;
  }

  stopCloud() {
    for (const c of Object.values(this.cloud)) c.stop();
    this.estimated = null;
  }

  async run(token) {
    let first = true;
    while (this.playing && token === this.token && this.index < this.flat.length) {
      const s = this.settings();
      const ok = s.engine === 'device' ? await this.stepDevice(token, s) : await this.stepCloud(token, s, first);
      if (!ok || token !== this.token) return;
      first = false;
    }
    if (token === this.token && this.index >= this.flat.length) {
      this.index = this.flat.length - 1;
      this.stop();
      this.emit('finished');
    }
  }

  async stepDevice(token, s) {
    const seg = this.flat[this.index];
    this.emit('position', { start: this.index, end: this.index + 1 });
    try {
      await this.device.speak(seg.text, { lang: this.book.lang, rate: s.rate, voiceName: s.deviceVoice });
    } catch (e) {
      if (e.message === 'cancel' || token !== this.token) return false;
      // Alguns navegadores emitem erros espúrios ("synthesis-failed") em frases isoladas: pula a frase
      if (this.errorsInRow++ > 3) return this.fail(new Error(`A voz do aparelho falhou (${e.message}).`));
    }
    if (token !== this.token) return false;
    this.errorsInRow = 0;
    this.advance(this.index + 1);
    return true;
  }

  chunkAt(start, max = CLOUD_CHUNK) {
    const ch = this.flat[start].ch;
    let end = start;
    let len = 0;
    const parts = [];
    let lastPara = null;
    while (end < this.flat.length && this.flat[end].ch === ch) {
      const seg = this.flat[end];
      if (len > 0 && len + seg.text.length > max) break;
      parts.push((lastPara !== null && seg.para !== lastPara ? '\n\n' : parts.length ? ' ' : '') + seg.text);
      lastPara = seg.para;
      len += seg.text.length;
      end++;
    }
    return { start, end, text: parts.join('') };
  }

  cacheKey(chunk, s) {
    const voice = s.engine === 'openai'
      ? `${s.openaiModel}|${s.openaiVoice}|${s.openaiInstructions}`
      : `${s.elevenModel}|${s.elevenVoice}`;
    return `${this.book.id}|${s.engine}|${voice}|${chunk.start}|${chunk.end}`;
  }

  fetchChunk(chunk, s) {
    const prev = this.flat[chunk.start - 1];
    const nxt = this.flat[chunk.end];
    return this.currentCloud().get(this.cacheKey(chunk, s), chunk.text, {
      previous: prev && prev.ch === this.flat[chunk.start].ch ? prev.text : '',
      next: nxt && nxt.ch === this.flat[chunk.start].ch ? nxt.text : '',
    });
  }

  prefetch(from, s) {
    let start = from;
    for (let k = 0; k < PREFETCH && start < this.flat.length; k++) {
      const c = this.chunkAt(start);
      this.fetchChunk(c, s).catch(() => {});
      start = c.end;
    }
  }

  async stepCloud(token, s, first) {
    const chunk = this.chunkAt(this.index, first ? CLOUD_FIRST_CHUNK : CLOUD_CHUNK);
    this.chunk = chunk;
    this.emit('position', { start: chunk.start, end: chunk.start + 1 });
    this.emit('loading', true);
    let url;
    try {
      url = await this.fetchChunk(chunk, s);
    } catch (e) {
      this.emit('loading', false);
      if (token !== this.token) return false;
      if (!e.fatal && s.fallbackToDevice) {
        // Sem internet (ex.: dirigindo num túnel): continua com a voz do aparelho
        this.emit('notice', 'Sem conexão — usando a voz do aparelho por enquanto.');
        const end = chunk.end;
        while (this.index < end && token === this.token && this.playing) {
          if (!(await this.stepDevice(token, s))) return false;
        }
        return true;
      }
      return this.fail(e);
    }
    this.emit('loading', false);
    if (token !== this.token) return false;
    this.prefetch(chunk.end, s);
    try {
      await this.currentCloud().play(url, s.rate);
    } catch (e) {
      if (e.message === 'cancel' || token !== this.token) return false;
      if (e.name === 'NotAllowedError') return this.fail(new Error('Toque em ▶ para liberar o áudio.'));
      return this.fail(e);
    }
    if (token !== this.token) return false;
    this.estimated = null;
    this.advance(chunk.end);
    return true;
  }

  // Estima a frase atual dentro de um trecho da nuvem pela proporção de caracteres
  onTimeUpdate() {
    const c = this.chunk;
    const a = this.audio;
    if (!c || !a.duration || !isFinite(a.duration)) return;
    const target = (a.currentTime / a.duration) * c.text.length;
    let acc = 0;
    let i = c.start;
    for (; i < c.end - 1; i++) {
      acc += this.flat[i].text.length + 1;
      if (acc > target) break;
    }
    if (i !== this.estimated) {
      this.estimated = i;
      this.emit('position', { start: i, end: i + 1 });
    }
  }

  advance(i) {
    const prevCh = this.flat[this.index]?.ch;
    this.index = i;
    const s = this.flat[i];
    if (s && s.ch !== prevCh) this.emit('chapter', { from: prevCh, to: s.ch });
    this.emit('save');
  }

  fail(err) {
    this.stop();
    this.emit('error', err);
    return false;
  }
}

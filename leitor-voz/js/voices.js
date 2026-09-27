// Motores de voz.
//  - DeviceVoice: vozes do próprio aparelho (Web Speech API). Grátis e offline,
//    mas o navegador costuma interromper a fala com a tela bloqueada.
//  - OpenAIVoice / ElevenLabsVoice: vozes neurais na nuvem. Geram MP3 que toca num
//    <audio>, o que continua em segundo plano e aparece nos controles da tela bloqueada.

export const OPENAI_VOICES = ['marin', 'cedar', 'coral', 'sage', 'nova', 'shimmer', 'alloy', 'ash', 'ballad', 'echo', 'fable', 'onyx', 'verse'];

export const DEFAULT_INSTRUCTIONS =
  'Leia como um narrador de audiolivro experiente: voz calma, calorosa e natural, ritmo fluido, ' +
  'pausas curtas entre frases e entonação expressiva. Leia no idioma do texto (português do Brasil ' +
  'quando for português). Pronuncie termos técnicos, siglas e unidades com precisão.';

// ---------------- Voz do aparelho ----------------

const LOW_QUALITY = /\b(eddy|flo|grandma|grandpa|rocko|reed|sandy|shelley|albert|bad news|bahh|bells|boing|bubbles|cellos|good news|jester|organ|superstar|trinoids|whisper|wobble|zarvox|junior|ralph|fred|kathy)\b/i;

export function listDeviceVoices() {
  return 'speechSynthesis' in window ? speechSynthesis.getVoices() : [];
}

export function voicesReady() {
  return new Promise((resolve) => {
    if (!('speechSynthesis' in window)) return resolve([]);
    const v = speechSynthesis.getVoices();
    if (v.length) return resolve(v);
    const done = () => resolve(speechSynthesis.getVoices());
    speechSynthesis.addEventListener('voiceschanged', done, { once: true });
    setTimeout(done, 1500);
  });
}

export function scoreVoice(v, lang) {
  const want = lang.toLowerCase();
  const vl = v.lang.toLowerCase().replace('_', '-');
  let s = 0;
  if (vl === want) s += 20;
  else if (vl.split('-')[0] === want.split('-')[0]) s += 12;
  else return -100;
  if (/natural|neural|premium|enhanced|aprimorad|online/i.test(v.name)) s += 8;
  if (/google/i.test(v.name)) s += 5;
  if (/microsoft/i.test(v.name) && !/online/i.test(v.name)) s -= 2;
  if (LOW_QUALITY.test(v.name)) s -= 15;
  if (v.default) s += 1;
  return s;
}

export function bestDeviceVoice(lang, preferredName) {
  const voices = listDeviceVoices();
  const base = lang.split('-')[0];
  if (preferredName) {
    const p = voices.find((v) => v.name === preferredName);
    if (p && p.lang.toLowerCase().startsWith(base)) return p;
  }
  return voices
    .map((v) => ({ v, s: scoreVoice(v, lang) }))
    .filter((x) => x.s > -100)
    .sort((a, b) => b.s - a.s)[0]?.v || null;
}

export class DeviceVoice {
  constructor() {
    this.current = null;
  }

  // Um trecho por vez; resolve quando termina de falar, rejeita com 'cancel' se interrompido.
  speak(text, { lang, rate, voiceName }) {
    return new Promise((resolve, reject) => {
      const u = new SpeechSynthesisUtterance(text);
      const voice = bestDeviceVoice(lang, voiceName);
      if (voice) u.voice = voice;
      u.lang = voice?.lang || lang;
      u.rate = rate;
      u.onend = () => { if (this.current === u) this.current = null; resolve(); };
      u.onerror = (e) => {
        if (this.current === u) this.current = null;
        e.error === 'interrupted' || e.error === 'canceled' ? reject(new Error('cancel')) : reject(new Error(e.error || 'speech-error'));
      };
      this.current = u; // mantém referência (bug do Chrome: onend some se a fala for coletada)
      speechSynthesis.speak(u);
    });
  }

  stop() {
    this.current = null;
    speechSynthesis.cancel();
  }
}

// ---------------- Vozes na nuvem ----------------

class CloudVoiceBase {
  constructor(audio) {
    this.audio = audio;
    this.cache = new Map(); // chave → Promise<blobURL>
  }

  fetchAudio() {
    throw new Error('not implemented');
  }

  get(key, text, ctx) {
    if (!this.cache.has(key)) {
      const p = this.fetchAudio(text, ctx).then((blob) => URL.createObjectURL(blob));
      p.catch(() => this.cache.delete(key));
      this.cache.set(key, p);
      this.trim();
    }
    return this.cache.get(key);
  }

  trim() {
    while (this.cache.size > 40) {
      const [k, p] = this.cache.entries().next().value;
      this.cache.delete(k);
      p.then((url) => URL.revokeObjectURL(url)).catch(() => {});
    }
  }

  clear() {
    for (const p of this.cache.values()) p.then((u) => URL.revokeObjectURL(u)).catch(() => {});
    this.cache.clear();
  }

  // Toca o áudio já baixado; resolve ao terminar.
  async play(url, rate) {
    const a = this.audio;
    this.stopPending?.(new Error('cancel'));
    a.src = url;
    a.playbackRate = rate;
    a.preservesPitch = true;
    return new Promise((resolve, reject) => {
      const cleanup = () => {
        a.onended = a.onerror = null;
        this.stopPending = null;
      };
      a.onended = () => { cleanup(); resolve(); };
      a.onerror = () => { cleanup(); reject(new Error('Falha ao tocar o áudio.')); };
      this.stopPending = (err) => { cleanup(); reject(err); };
      a.play().catch((e) => { cleanup(); reject(e); });
    });
  }

  pause() { this.audio.pause(); }
  resume() { return this.audio.play(); }
  setRate(r) { this.audio.playbackRate = r; }

  stop() {
    this.audio.pause();
    this.stopPending?.(new Error('cancel'));
  }
}

async function httpError(res, provider) {
  let detail = '';
  try {
    const j = await res.json();
    detail = j.error?.message || j.detail?.message || j.detail || '';
  } catch {}
  const msg = {
    401: `Chave de API ${provider} inválida ou ausente.`,
    402: `Sem créditos na conta ${provider}.`,
    429: `Limite de uso/créditos da ${provider} atingido.`,
  }[res.status] || `Erro ${res.status} na ${provider}.`;
  const e = new Error(detail ? `${msg} (${typeof detail === 'string' ? detail : JSON.stringify(detail)})` : msg);
  e.fatal = [400, 401, 402, 403, 404, 422, 429].includes(res.status);
  return e;
}

export class OpenAIVoice extends CloudVoiceBase {
  constructor(audio, settings) {
    super(audio);
    this.settings = settings;
  }

  async fetchAudio(text) {
    const s = this.settings();
    if (!s.openaiKey) throw Object.assign(new Error('Informe sua chave da OpenAI em Ajustes.'), { fatal: true });
    const res = await fetch('https://api.openai.com/v1/audio/speech', {
      method: 'POST',
      headers: { Authorization: `Bearer ${s.openaiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: s.openaiModel || 'gpt-4o-mini-tts',
        voice: s.openaiVoice || 'marin',
        input: text,
        response_format: 'mp3',
        ...(s.openaiModel === 'tts-1' || s.openaiModel === 'tts-1-hd' ? {} : { instructions: s.openaiInstructions || DEFAULT_INSTRUCTIONS }),
      }),
    });
    if (!res.ok) throw await httpError(res, 'OpenAI');
    return res.blob();
  }
}

export class ElevenLabsVoice extends CloudVoiceBase {
  constructor(audio, settings) {
    super(audio);
    this.settings = settings;
  }

  async fetchAudio(text, ctx = {}) {
    const s = this.settings();
    if (!s.elevenKey) throw Object.assign(new Error('Informe sua chave da ElevenLabs em Ajustes.'), { fatal: true });
    const voiceId = (s.elevenVoice || '').trim() || 'EXAVITQu4vr4xnSDxMaL';
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${encodeURIComponent(voiceId)}?output_format=mp3_44100_128`, {
      method: 'POST',
      headers: { 'xi-api-key': s.elevenKey, 'Content-Type': 'application/json', Accept: 'audio/mpeg' },
      body: JSON.stringify({
        text,
        model_id: s.elevenModel || 'eleven_multilingual_v2',
        // Contexto vizinho melhora a continuidade da entonação entre trechos
        previous_text: ctx.previous || undefined,
        next_text: ctx.next || undefined,
        voice_settings: { stability: 0.5, similarity_boost: 0.75, style: 0.15, use_speaker_boost: true },
      }),
    });
    if (!res.ok) throw await httpError(res, 'ElevenLabs');
    return res.blob();
  }
}

// 1 s de silêncio em WAV: mantém a sessão de mídia ativa para a voz do aparelho
export function silentWavUrl() {
  const rate = 8000;
  const n = rate;
  const buf = new ArrayBuffer(44 + n);
  const v = new DataView(buf);
  const w = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  w(0, 'RIFF'); v.setUint32(4, 36 + n, true); w(8, 'WAVE'); w(12, 'fmt ');
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate, true); v.setUint16(32, 1, true); v.setUint16(34, 8, true);
  w(36, 'data'); v.setUint32(40, n, true);
  new Uint8Array(buf, 44).fill(128);
  return URL.createObjectURL(new Blob([buf], { type: 'audio/wav' }));
}

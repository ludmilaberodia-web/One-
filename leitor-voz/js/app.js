import { parseFile } from './parsers.js';
import { buildSegments, detectLang } from './segment.js';
import { saveBook, getBook, deleteBook, listBooks, updateProgress } from './db.js';
import { Player } from './player.js';
import { OPENAI_VOICES, DEFAULT_INSTRUCTIONS, voicesReady, listDeviceVoices, bestDeviceVoice, scoreVoice, DeviceVoice, silentWavUrl } from './voices.js';

const $ = (s) => document.querySelector(s);

// ---------------- Ajustes ----------------
const DEFAULTS = {
  engine: 'device',
  deviceVoice: '',
  openaiKey: '',
  openaiVoice: 'marin',
  openaiModel: 'gpt-4o-mini-tts',
  openaiInstructions: DEFAULT_INSTRUCTIONS,
  elevenKey: '',
  elevenVoice: '',
  elevenModel: 'eleven_multilingual_v2',
  rate: 1,
  skipCitations: true,
  stopAtReferences: false,
  fallbackToDevice: true,
  wakeLock: true,
};
let settings = { ...DEFAULTS };
try { settings = { ...DEFAULTS, ...JSON.parse(localStorage.getItem('leitor-settings') || '{}') }; } catch {}
const saveSettings = () => { try { localStorage.setItem('leitor-settings', JSON.stringify(settings)); } catch {} };

// ---------------- Estado ----------------
const audio = $('#audio');
const keepalive = $('#keepalive');
const player = new Player({ settings: () => settings, audio });
let book = null;           // livro aberto (com capítulos)
let renderedChapter = -1;
let lastUserScroll = 0;
let sleep = { mode: 'off', until: 0, timer: null };

// ---------------- Biblioteca ----------------
async function renderLibrary() {
  const books = await listBooks();
  const ul = $('#book-list');
  ul.replaceChildren();
  $('#empty-library').hidden = books.length > 0;
  for (const b of books) {
    const li = document.createElement('li');
    li.className = 'book';
    const pct = Math.round((b.progress?.percent || 0) * 100);
    const hours = b.chars / 15 / 3600;
    li.innerHTML = `
      <div class="meta" role="button" tabindex="0">
        <h3></h3>
        <small>${b.format.toUpperCase()} · ${pct}% · ≈ ${hours < 1 ? Math.max(1, Math.round(hours * 60)) + ' min' : hours.toFixed(1).replace('.', ',') + ' h'} de áudio</small>
        <div class="bar"><i style="width:${pct}%"></i></div>
      </div>
      <button class="icon-btn del" aria-label="Remover"><svg viewBox="0 0 24 24"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg></button>`;
    li.querySelector('h3').textContent = b.title;
    const open = () => openBook(b.id);
    li.querySelector('.meta').addEventListener('click', open);
    li.querySelector('.meta').addEventListener('keydown', (e) => e.key === 'Enter' && open());
    li.querySelector('.del').addEventListener('click', async () => {
      if (!confirm(`Remover “${b.title}”?`)) return;
      await deleteBook(b.id);
      renderLibrary();
    });
    ul.append(li);
  }
}

async function importFile(file) {
  if (!file) return;
  busy(`Lendo ${file.name}…`);
  try {
    const parsed = await parseFile(file, (p) => busy(`Extraindo texto… ${Math.round(p * 100)}%`));
    const total = parsed.chapters.reduce((n, c) => n + c.text.length, 0);
    if (total < 20) {
      throw new Error('Não encontrei texto. Se for um PDF escaneado (imagem), é preciso OCR antes — ex.: abra no Google Drive/Adobe e exporte com texto.');
    }
    const id = `${file.name}|${file.size}`;
    const b = {
      id,
      title: parsed.title,
      format: file.name.split('.').pop().toLowerCase(),
      addedAt: Date.now(),
      chapters: parsed.chapters,
    };
    b.lang = detectLang(b);
    const existing = await getBook(id);
    if (existing?.progress) b.progress = existing.progress;
    await saveBook(b);
    unbusy();
    await openBook(id);
  } catch (e) {
    unbusy();
    toast(e.message || String(e), true);
    console.error(e);
  }
}

// ---------------- Leitor ----------------
let segments = null;

async function openBook(id) {
  const b = await getBook(id);
  if (!b) return;
  if (book) {
    player.stop();
    await updateProgress(book.id, player.position);
  }
  book = b;
  segments = buildSegments(book, settings);
  player.load(book, segments, book.progress);
  renderedChapter = -1;

  $('#book-title').textContent = book.title;
  const sel = $('#chapter-select');
  sel.replaceChildren(...segments.map((c, i) => new Option(c.title || `Capítulo ${i + 1}`, i)));
  sel.hidden = segments.length < 2;

  show('reader');
  history.pushState({ reader: id }, '');
  updateVoiceChip();
  renderPosition(player.index, player.index + 1, true);
  updateMediaMetadata();
}

function resegment() {
  if (!book) return;
  const pos = player.position;
  segments = buildSegments(book, settings);
  player.load(book, segments, pos);
  renderedChapter = -1;
  renderPosition(player.index, player.index + 1, true);
}

function renderChapter(ci) {
  const el = $('#text');
  el.replaceChildren();
  const ch = segments[ci];
  const h = document.createElement('h3');
  h.textContent = ch.title;
  el.append(h);
  if (!ch.segs.length) {
    const p = document.createElement('p');
    p.className = 'empty-ch';
    p.textContent = settings.stopAtReferences ? 'Seção ignorada (após “Referências”).' : 'Sem texto nesta seção.';
    el.append(p);
  }
  const base = player.chStart[ci];
  let p = null;
  let lastPara = null;
  ch.segs.forEach((s, i) => {
    if (s.para !== lastPara) {
      p = document.createElement('p');
      el.append(p);
      lastPara = s.para;
    } else {
      p.append(' ');
    }
    const span = document.createElement('span');
    span.className = 's';
    span.dataset.i = base + i;
    span.textContent = s.text;
    p.append(span);
  });
  renderedChapter = ci;
  $('#chapter-select').value = ci;
}

let curSpan = null;
function renderPosition(start, _end, forceScroll = false) {
  const seg = player.flat[start];
  if (!seg) {
    $('#text').textContent = 'Nada para ler neste arquivo com os filtros atuais.';
    return;
  }
  if (seg.ch !== renderedChapter) renderChapter(seg.ch);
  curSpan?.classList.remove('cur');
  curSpan = $(`#text .s[data-i="${start}"]`);
  curSpan?.classList.add('cur');
  if (curSpan && (forceScroll || Date.now() - lastUserScroll > 4000)) {
    curSpan.scrollIntoView({ block: 'center', behavior: forceScroll ? 'auto' : 'smooth' });
  }
  const pct = player.flat.length ? start / player.flat.length : 0;
  $('#progress').value = Math.round(pct * 1000);
  $('#progress-label').textContent = `${Math.round(pct * 100)}%`;
  $('#status-label').textContent = remainingLabel(start);
  $('#drive-chapter').textContent = segments[seg.ch].title;
  $('#drive-sentence').textContent = seg.text;
}

function remainingLabel(start) {
  let chars = 0;
  for (let i = start; i < player.flat.length; i++) chars += player.flat[i].text.length;
  const min = chars / 15 / 60 / settings.rate;
  return min < 60 ? `${Math.ceil(min)} min` : `${Math.floor(min / 60)} h ${Math.round(min % 60)}`;
}

// ---------------- Eventos do player ----------------
player.addEventListener('position', (e) => renderPosition(e.detail.start, e.detail.end));
player.addEventListener('state', (e) => {
  document.body.classList.toggle('playing', e.detail.playing);
  if (!e.detail.playing) document.body.classList.remove('loading');
  if ('mediaSession' in navigator) navigator.mediaSession.playbackState = e.detail.playing ? 'playing' : 'paused';
  e.detail.playing ? onPlayStart() : onPlayStop();
});
player.addEventListener('loading', (e) => document.body.classList.toggle('loading', e.detail));
player.addEventListener('error', (e) => toast(e.detail.message, true));
player.addEventListener('notice', (e) => toast(e.detail));
player.addEventListener('finished', () => { toast('Fim do livro.'); saveProgress(true); });
player.addEventListener('chapter', () => {
  updateMediaMetadata();
  if (sleep.mode === 'chapter') { player.pause(); setSleep('off'); toast('Timer: fim do capítulo.'); }
});
let saveTimer = null;
player.addEventListener('save', () => saveProgress());

function saveProgress(now = false) {
  if (!book) return;
  clearTimeout(saveTimer);
  const doSave = () => updateProgress(book.id, player.position);
  now ? doSave() : (saveTimer = setTimeout(doSave, 1500));
}

// ---------------- Segundo plano / tela bloqueada ----------------
let wakeLock = null;
let keepaliveUrl = null;

async function onPlayStart() {
  if (settings.wakeLock && 'wakeLock' in navigator) {
    try { wakeLock = await navigator.wakeLock.request('screen'); } catch {}
  }
  // Com a voz do aparelho, um áudio silencioso registra a sessão de mídia
  // (botões do fone/carro e tela de bloqueio)
  if (settings.engine === 'device') {
    keepaliveUrl ??= silentWavUrl();
    keepalive.src = keepaliveUrl;
    keepalive.volume = 0.01;
    keepalive.play().catch(() => {});
  }
}

function onPlayStop() {
  wakeLock?.release().catch(() => {});
  wakeLock = null;
  keepalive.pause();
  saveProgress(true);
}

document.addEventListener('visibilitychange', async () => {
  if (document.visibilityState === 'hidden') saveProgress(true);
  else if (player.playing && settings.wakeLock && 'wakeLock' in navigator && !wakeLock) {
    try { wakeLock = await navigator.wakeLock.request('screen'); } catch {}
  }
});

function updateMediaMetadata() {
  if (!('mediaSession' in navigator) || !book) return;
  const seg = player.flat[player.index];
  navigator.mediaSession.metadata = new MediaMetadata({
    title: seg ? segments[seg.ch].title : book.title,
    artist: book.title,
    album: 'Leitor de Voz',
    artwork: [{ src: new URL('icons/icon-512.png', location.href).href, sizes: '512x512', type: 'image/png' }],
  });
}

if ('mediaSession' in navigator) {
  const ms = navigator.mediaSession;
  const h = (a, fn) => { try { ms.setActionHandler(a, fn); } catch {} };
  h('play', () => player.play());
  h('pause', () => player.pause());
  h('stop', () => player.pause());
  h('seekbackward', () => player.skipSeconds(-15));
  h('seekforward', () => player.skipSeconds(15));
  // Botões ⏮/⏭ do volante/fone: voltar/avançar ~30 s é mais útil que pular capítulo
  h('previoustrack', () => player.skipSeconds(-30));
  h('nexttrack', () => player.skipSeconds(30));
}

// Pausa ao ser interrompido (ligação etc.) é tratada pelo SO; se o áudio for pausado externamente, sincroniza
audio.addEventListener('pause', () => {
  if (player.playing && !audio.ended && audio.src && settings.engine !== 'device' && player.chunk && !player.cloudPaused) {
    player.playing = false;
    player.cloudPaused = true;
    player.emit('state', { playing: false });
  }
});
audio.addEventListener('play', () => {
  if (!player.playing && player.cloudPaused) {
    player.playing = true;
    player.cloudPaused = false;
    player.emit('state', { playing: true });
  }
});

// ---------------- Controles ----------------
$('#play').addEventListener('click', () => {
  // iOS exige que a primeira fala/áudio parta de um toque
  if (settings.engine === 'device' && 'speechSynthesis' in window && !player.playing) speechSynthesis.resume();
  player.toggle();
});
$('#back15').addEventListener('click', () => player.skipSeconds(-15));
$('#fwd15').addEventListener('click', () => player.skipSeconds(15));
$('#prev-chapter').addEventListener('click', () => player.prevChapter());
$('#next-chapter').addEventListener('click', () => player.nextChapter());
$('#chapter-select').addEventListener('change', (e) => player.goToChapter(+e.target.value));
$('#progress').addEventListener('change', (e) => player.seek(Math.round((e.target.value / 1000) * player.flat.length)));
$('#text').addEventListener('click', (e) => {
  const s = e.target.closest('.s');
  if (s) player.seek(+s.dataset.i);
});
['wheel', 'touchmove'].forEach((ev) => window.addEventListener(ev, () => (lastUserScroll = Date.now()), { passive: true }));

$('#back').addEventListener('click', () => history.back());
window.addEventListener('popstate', () => {
  if ($('#reader').classList.contains('active')) {
    player.stop();
    saveProgress(true);
    book = null;
    document.body.classList.remove('drive');
    show('library');
    renderLibrary();
  }
});

$('#drive-toggle').addEventListener('click', () => {
  const on = document.body.classList.toggle('drive');
  $('#drive-toggle').classList.toggle('on', on);
  try { localStorage.setItem('leitor-drive', on ? '1' : ''); } catch {}
});

const RATES = [0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.5, 1.75, 2];
$('#rate-chip').addEventListener('click', () => {
  const i = RATES.findIndex((r) => r > settings.rate + 0.001);
  setRate(i === -1 ? RATES[0] : RATES[i]);
});
function setRate(r) {
  settings.rate = Math.round(r * 100) / 100;
  saveSettings();
  $('#rate-chip').textContent = `${settings.rate.toFixed(settings.rate * 10 % 1 ? 2 : 1).replace('.', ',')}×`;
  $('#rate').value = settings.rate;
  $('#rate-out').textContent = $('#rate-chip').textContent;
  player.setRate(settings.rate);
}

const SLEEP = ['off', 15, 30, 45, 60, 'chapter'];
$('#sleep-chip').addEventListener('click', () => setSleep(SLEEP[(SLEEP.indexOf(sleep.mode) + 1) % SLEEP.length]));
function setSleep(mode) {
  clearInterval(sleep.timer);
  sleep = { mode, until: typeof mode === 'number' ? Date.now() + mode * 60000 : 0, timer: null };
  const chip = $('#sleep-chip');
  chip.classList.toggle('on', mode !== 'off');
  const label = () => {
    if (mode === 'off') return '⏾ Desligado';
    if (mode === 'chapter') return '⏾ Fim do capítulo';
    const left = Math.max(0, Math.ceil((sleep.until - Date.now()) / 60000));
    return `⏾ ${left} min`;
  };
  chip.textContent = label();
  if (typeof mode === 'number') {
    sleep.timer = setInterval(() => {
      chip.textContent = label();
      if (Date.now() >= sleep.until) { player.pause(); setSleep('off'); toast('Timer encerrado.'); }
    }, 5000);
  }
}

$('#voice-chip').addEventListener('click', () => openSettings());

function updateVoiceChip() {
  const s = settings;
  let label;
  if (s.engine === 'openai') label = `OpenAI · ${s.openaiVoice}`;
  else if (s.engine === 'elevenlabs') label = 'ElevenLabs';
  else label = bestDeviceVoice(book?.lang || 'pt-BR', s.deviceVoice)?.name.replace(/\s*\(.*\)/, '') || 'Voz do aparelho';
  $('#voice-chip').textContent = `🗣 ${label}`;
}

// ---------------- Tela de ajustes ----------------
const dlg = $('#settings');
$('#open-settings').addEventListener('click', () => openSettings());

function openSettings() {
  const s = settings;
  dlg.querySelector(`input[name="engine"][value="${s.engine}"]`).checked = true;
  $('#openai-key').value = s.openaiKey;
  $('#openai-voice').value = s.openaiVoice;
  $('#openai-model').value = s.openaiModel;
  $('#openai-instructions').value = s.openaiInstructions;
  $('#eleven-key').value = s.elevenKey;
  $('#eleven-voice').value = s.elevenVoice;
  $('#eleven-model').value = s.elevenModel;
  $('#rate').value = s.rate;
  $('#rate-out').textContent = $('#rate-chip').textContent;
  $('#skip-citations').checked = s.skipCitations;
  $('#stop-at-references').checked = s.stopAtReferences;
  $('#fallback').checked = s.fallbackToDevice;
  $('#wake-lock').checked = s.wakeLock;
  fillDeviceVoices();
  showEngine();
  dlg.showModal();
}

function showEngine() {
  const engine = dlg.querySelector('input[name="engine"]:checked').value;
  dlg.querySelectorAll('[data-engine]').forEach((el) => el.classList.toggle('show', el.dataset.engine === engine));
  $('#engine-hint').textContent = {
    device: 'Qualidade depende do aparelho. Em muitos celulares a leitura para com a tela bloqueada — deixe “Manter tela ligada” ativo.',
    openai: 'Voz neural muito natural; continua com a tela bloqueada e responde aos botões do fone/carro. Custo aproximado: US$ 0,015 por minuto de áudio (gpt-4o-mini-tts).',
    elevenlabs: 'A voz mais humana disponível hoje, com contexto entre frases. Mais cara: consome créditos do plano por caractere.',
  }[engine];
}

function fillDeviceVoices() {
  const lang = book?.lang || 'pt-BR';
  const base = lang.split('-')[0];
  const sel = $('#device-voice');
  const voices = listDeviceVoices()
    .filter((v) => v.lang.toLowerCase().startsWith(base))
    .sort((a, b) => scoreVoice(b, lang) - scoreVoice(a, lang));
  sel.replaceChildren(new Option('Automática (melhor disponível)', ''), ...voices.map((v) => new Option(`${v.name} — ${v.lang}`, v.name)));
  sel.value = voices.some((v) => v.name === settings.deviceVoice) ? settings.deviceVoice : '';
}

$('#openai-voice').replaceChildren(...OPENAI_VOICES.map((v) => new Option(v[0].toUpperCase() + v.slice(1), v)));

dlg.addEventListener('change', (e) => {
  const before = JSON.stringify(settings);
  const prevEngine = settings.engine;
  const s = settings;
  s.engine = dlg.querySelector('input[name="engine"]:checked').value;
  s.deviceVoice = $('#device-voice').value;
  s.openaiKey = $('#openai-key').value.trim();
  s.openaiVoice = $('#openai-voice').value;
  s.openaiModel = $('#openai-model').value;
  s.openaiInstructions = $('#openai-instructions').value.trim() || DEFAULT_INSTRUCTIONS;
  s.elevenKey = $('#eleven-key').value.trim();
  s.elevenVoice = $('#eleven-voice').value.trim();
  s.elevenModel = $('#eleven-model').value;
  const filtersChanged = s.skipCitations !== $('#skip-citations').checked || s.stopAtReferences !== $('#stop-at-references').checked;
  s.skipCitations = $('#skip-citations').checked;
  s.stopAtReferences = $('#stop-at-references').checked;
  s.fallbackToDevice = $('#fallback').checked;
  s.wakeLock = $('#wake-lock').checked;
  saveSettings();
  if (e.target.name === 'engine') showEngine();
  if (e.target.id === 'rate') setRate(+e.target.value);
  updateVoiceChip();
  if (filtersChanged) resegment();
  else if (before !== JSON.stringify(settings) && e.target.id !== 'rate' && (player.playing || prevEngine !== s.engine)) player.restart();
});
$('#rate').addEventListener('input', (e) => ($('#rate-out').textContent = `${(+e.target.value).toFixed(2).replace('.', ',')}×`));

$('#test-voice').addEventListener('click', async () => {
  const lang = book?.lang || 'pt-BR';
  const sample = lang.startsWith('en')
    ? 'Hello. This is how your books and articles will sound while you run, drive or take care of the house.'
    : 'Olá. É assim que seus livros e artigos vão soar enquanto você corre, dirige ou cuida da casa. A facoemulsificação com lente trifocal foi realizada sem intercorrências.';
  player.pause();
  const btn = $('#test-voice');
  btn.disabled = true;
  try {
    if (settings.engine === 'device') {
      await new DeviceVoice().speak(sample, { lang, rate: settings.rate, voiceName: settings.deviceVoice });
    } else {
      const eng = player.cloud[settings.engine];
      btn.textContent = 'Gerando…';
      const url = await eng.get(`test|${JSON.stringify(settings)}`, sample, {});
      btn.textContent = 'Tocando…';
      await eng.play(url, settings.rate);
    }
  } catch (e) {
    if (e.message !== 'cancel') toast(e.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Testar voz';
  }
});

// ---------------- Arquivos ----------------
$('#file-input').addEventListener('change', (e) => {
  importFile(e.target.files[0]);
  e.target.value = '';
});
const dz = $('#dropzone');
['dragenter', 'dragover'].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add('drag'); }));
['dragleave', 'drop'].forEach((ev) => dz.addEventListener(ev, () => dz.classList.remove('drag')));
dz.addEventListener('drop', (e) => { e.preventDefault(); importFile(e.dataTransfer.files[0]); });

// Arquivos recebidos pelo "Compartilhar" do Android (share target do PWA)
async function checkSharedFile() {
  if (!new URLSearchParams(location.search).has('shared') || !('caches' in window)) return;
  history.replaceState(null, '', location.pathname);
  const cache = await caches.open('shared-files');
  const res = await cache.match('shared-file');
  if (!res) return;
  const name = decodeURIComponent(res.headers.get('X-File-Name') || 'arquivo.pdf');
  const blob = await res.blob();
  await cache.delete('shared-file');
  importFile(new File([blob], name, { type: blob.type }));
}

// ---------------- Utilidades ----------------
function show(id) {
  document.querySelectorAll('.screen').forEach((s) => s.classList.toggle('active', s.id === id));
  window.scrollTo(0, 0);
}

let toastTimer;
function toast(msg, isError = false) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.toggle('error', isError);
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), isError ? 7000 : 3500);
}
$('#toast').addEventListener('click', () => ($('#toast').hidden = true));

function busy(text) {
  $('#busy-text').textContent = text;
  $('#busy').hidden = false;
}
function unbusy() {
  $('#busy').hidden = true;
}

// ---------------- Início ----------------
(async function init() {
  setRate(settings.rate);
  setSleep('off');
  try {
    if (localStorage.getItem('leitor-drive')) {
      document.body.classList.add('drive');
      $('#drive-toggle').classList.add('on');
    }
  } catch {}
  await voicesReady();
  if ('speechSynthesis' in window) speechSynthesis.addEventListener('voiceschanged', updateVoiceChip);
  renderLibrary();
  checkSharedFile();
  if ('serviceWorker' in navigator && location.protocol !== 'file:') {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
})();

// Exposto para testes automatizados
window.__leitor = { player, importFile, settings: () => settings };

'use strict';

// Grava a consulta, envia o áudio em pedaços para o servidor local e pede a
// transcrição ao encerrar. O áudio nunca sai desta máquina.

const $ = (id) => document.getElementById(id);

const telas = {
  consentimento: $('tela-consentimento'),
  gravando: $('tela-gravando'),
  processando: $('tela-processando'),
  pronto: $('tela-pronto'),
};

let sessaoId = null;
let gravador = null;
let fluxo = null;
let contexto = null;
let cronometro = null;
let segundos = 0;

// Uploads precisam chegar em ordem: um pedaço fora de sequência corrompe o
// arquivo. A fila encadeia os envios em vez de disparar em paralelo.
let fila = Promise.resolve();
let falhaEnvio = false;

const PEDACO_MS = 10000;

// --------------------------------------------------------------------- telas

function mostrar(nome) {
  for (const [chave, el] of Object.entries(telas)) el.hidden = chave !== nome;
}

function erro(mensagem) {
  const el = $('erro');
  el.textContent = mensagem;
  el.hidden = !mensagem;
}

// ----------------------------------------------------------------- servidor

async function api(caminho, opcoes = {}) {
  const resposta = await fetch(caminho, opcoes);
  const tipo = resposta.headers.get('content-type') || '';
  const corpo = tipo.includes('json') ? await resposta.json() : {};
  if (!resposta.ok) throw new Error(corpo.erro || `Falha na requisição (${resposta.status})`);
  return corpo;
}

// -------------------------------------------------------------------- áudio

function melhorFormato() {
  const candidatos = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
  ];
  return candidatos.find((t) => MediaRecorder.isTypeSupported?.(t)) || '';
}

function enfileirar(blob) {
  fila = fila.then(async () => {
    if (falhaEnvio) return;
    try {
      await api(`/api/sessao/${sessaoId}/audio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/octet-stream' },
        body: blob,
      });
    } catch (e) {
      falhaEnvio = true;
      erro(`Falha ao salvar o áudio: ${e.message}\nA gravação continua, mas encerre logo.`);
    }
  });
  return fila;
}

function medirNivel(stream) {
  try {
    contexto = new (window.AudioContext || window.webkitAudioContext)();
    const fonte = contexto.createMediaStreamSource(stream);
    const analisador = contexto.createAnalyser();
    analisador.fftSize = 512;
    fonte.connect(analisador);

    const dados = new Uint8Array(analisador.frequencyBinCount);
    const barra = $('nivel');

    (function medir() {
      if (!contexto || contexto.state === 'closed') return;
      analisador.getByteFrequencyData(dados);
      const media = dados.reduce((a, b) => a + b, 0) / dados.length;
      barra.style.width = `${Math.min(media * 1.8, 100)}%`;
      requestAnimationFrame(medir);
    })();
  } catch {
    // Medidor é enfeite: se o AudioContext falhar, a gravação segue.
  }
}

function pararAudio() {
  if (gravador && gravador.state !== 'inactive') gravador.stop();
  if (fluxo) fluxo.getTracks().forEach((t) => t.stop());
  if (contexto && contexto.state !== 'closed') contexto.close();
  gravador = fluxo = contexto = null;
  clearInterval(cronometro);
}

// ------------------------------------------------------------------ ciclo

async function iniciar() {
  erro('');
  $('btn-iniciar').disabled = true;

  if (!navigator.mediaDevices?.getUserMedia) {
    erro('Este navegador não permite gravar áudio. Use o Chrome ou o Safari, e abra por http://localhost.');
    $('btn-iniciar').disabled = false;
    return;
  }

  try {
    fluxo = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
  } catch (e) {
    const motivo = e.name === 'NotAllowedError'
      ? 'Permissão de microfone negada. Libere o microfone para este site e tente de novo.'
      : `Não consegui acessar o microfone: ${e.message}`;
    erro(motivo);
    $('btn-iniciar').disabled = false;
    return;
  }

  try {
    const sessao = await api('/api/sessao', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ consentimento: true }),
    });
    sessaoId = sessao.id;
  } catch (e) {
    erro(e.message);
    pararAudio();
    $('btn-iniciar').disabled = false;
    return;
  }

  const mimeType = melhorFormato();
  gravador = new MediaRecorder(fluxo, mimeType ? { mimeType, audioBitsPerSecond: 32000 } : {});
  gravador.ondataavailable = (e) => { if (e.data && e.data.size) enfileirar(e.data); };
  gravador.start(PEDACO_MS);

  segundos = 0;
  falhaEnvio = false;
  fila = Promise.resolve();
  $('cronometro').textContent = '00:00';
  cronometro = setInterval(() => {
    segundos += 1;
    const m = String(Math.floor(segundos / 60)).padStart(2, '0');
    const s = String(segundos % 60).padStart(2, '0');
    $('cronometro').textContent = `${m}:${s}`;
  }, 1000);

  medirNivel(fluxo);
  mostrar('gravando');
}

function pausar() {
  if (!gravador) return;
  const status = document.querySelector('.status');

  if (gravador.state === 'recording') {
    gravador.pause();
    clearInterval(cronometro);
    status.classList.add('pausado');
    $('rotulo-status').textContent = 'Pausado';
    $('btn-pausar').textContent = 'Continuar';
  } else if (gravador.state === 'paused') {
    gravador.resume();
    cronometro = setInterval(() => {
      segundos += 1;
      const m = String(Math.floor(segundos / 60)).padStart(2, '0');
      const s = String(segundos % 60).padStart(2, '0');
      $('cronometro').textContent = `${m}:${s}`;
    }, 1000);
    status.classList.remove('pausado');
    $('rotulo-status').textContent = 'Gravando';
    $('btn-pausar').textContent = 'Pausar';
  }
}

async function encerrar() {
  erro('');
  $('btn-encerrar').disabled = true;

  // requestData() força a saída do trecho ainda em buffer; stop() emite o resto.
  if (gravador && gravador.state !== 'inactive') {
    await new Promise((resolve) => {
      gravador.onstop = resolve;
      gravador.stop();
    });
  }
  if (fluxo) fluxo.getTracks().forEach((t) => t.stop());
  if (contexto && contexto.state !== 'closed') contexto.close();
  clearInterval(cronometro);

  await fila; // garante que todo pedaço chegou antes de transcrever

  mostrar('processando');

  try {
    const r = await api(`/api/sessao/${sessaoId}/encerrar`, { method: 'POST' });
    $('resumo-pronto').textContent =
      `${r.duracao} de consulta · ${r.palavras} palavras · salvo em ${r.arquivo}`;
    $('previa').textContent = r.previa || '(sem fala reconhecida)';
    $('comando').textContent = r.comando;
    mostrar('pronto');
  } catch (e) {
    mostrar('gravando');
    erro(e.message);
  } finally {
    gravador = fluxo = contexto = null;
    $('btn-encerrar').disabled = false;
  }
}

async function descartar() {
  if (!confirm('Descartar a gravação? O áudio será apagado e não há como recuperar.')) return;
  pararAudio();
  try {
    await api(`/api/sessao/${sessaoId}`, { method: 'DELETE' });
  } catch (e) {
    erro(e.message);
  }
  reiniciar();
}

function reiniciar() {
  sessaoId = null;
  segundos = 0;
  falhaEnvio = false;
  fila = Promise.resolve();
  $('consentimento').checked = false;
  $('btn-iniciar').disabled = true;
  $('btn-pausar').textContent = 'Pausar';
  $('rotulo-status').textContent = 'Gravando';
  document.querySelector('.status').classList.remove('pausado');
  $('nivel').style.width = '0%';
  erro('');
  mostrar('consentimento');
}

// ------------------------------------------------------------------ eventos

$('consentimento').addEventListener('change', (e) => {
  $('btn-iniciar').disabled = !e.target.checked;
});

$('btn-iniciar').addEventListener('click', iniciar);
$('btn-pausar').addEventListener('click', pausar);
$('btn-encerrar').addEventListener('click', encerrar);
$('btn-descartar').addEventListener('click', descartar);
$('btn-nova').addEventListener('click', reiniciar);

$('btn-copiar').addEventListener('click', async () => {
  await navigator.clipboard.writeText($('comando').textContent);
  $('btn-copiar').textContent = 'Copiado';
  setTimeout(() => { $('btn-copiar').textContent = 'Copiar'; }, 1600);
});

// Fechar a aba no meio da gravação perde o que estiver em buffer.
window.addEventListener('beforeunload', (e) => {
  if (gravador && gravador.state !== 'inactive') {
    e.preventDefault();
    e.returnValue = '';
  }
});

// Estado inicial: avisa se o Whisper não estiver instalado.
api('/api/estado').then((estado) => {
  if (!estado.transcricaoDisponivel) {
    const aviso = $('aviso-whisper');
    aviso.textContent =
      'Atenção: faster-whisper não está instalado. Você consegue gravar, mas não transcrever. '
      + 'Rode: pip install -r app/requirements.txt';
    aviso.hidden = false;
  }
}).catch(() => {});

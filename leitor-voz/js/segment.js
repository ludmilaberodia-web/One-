// Prepara o texto para leitura em voz alta e divide em frases.

const REF_HEADING = /^(\d+\.?\s*)?(references?|refer[êe]ncias( bibliogr[áa]ficas)?|bibliografia|bibliography|literature cited|works cited)\s*:?$/i;

export function detectLang(book) {
  const sample = book.chapters.map((c) => c.text.slice(0, 4000)).join(' ').slice(0, 20000).toLowerCase();
  const count = (words) => words.reduce((n, w) => n + (sample.match(new RegExp(`\\b${w}\\b`, 'g')) || []).length, 0);
  const pt = count(['de', 'que', 'não', 'uma', 'para', 'com', 'dos', 'das', 'ao', 'são', 'também', 'pela']);
  const en = count(['the', 'and', 'of', 'to', 'with', 'that', 'is', 'for', 'was', 'were', 'which', 'this']);
  const es = count(['el', 'los', 'las', 'del', 'por', 'una', 'con', 'que', 'es', 'para', 'también', 'pero']);
  if (en > pt && en > es) return 'en-US';
  if (es > pt * 1.2) return 'es-ES';
  return 'pt-BR';
}

export function cleanForSpeech(text, opts) {
  let t = text;
  // URLs e DOIs não fazem sentido em áudio
  t = t.replace(/\bhttps?:\/\/\S+/g, '').replace(/\bdoi:\s*\S+/gi, '').replace(/\b10\.\d{4,9}\/\S+/g, '');
  if (opts.skipCitations) {
    // [1], [2,3], [4–7]
    t = t.replace(/\s?\[\d+(?:\s*[,;–-]\s*\d+)*\]/g, '');
    // (Smith et al., 2019; Lee 2020a)
    t = t.replace(/\s?\((?:[^()]*?\b(?:19|20)\d{2}[a-z]?)(?:\s*;\s*[^()]*?\b(?:19|20)\d{2}[a-z]?)*\)/g, (m) =>
      /[A-Z][a-zà-ú]+|et al/.test(m) ? '' : m,
    );
    // Sobrescritos numéricos colados a palavras: "catarata.12 " / "ref¹²"
    t = t.replace(/[¹²³⁴⁵⁶⁷⁸⁹⁰]+/g, '');
  }
  return t.replace(/ {2,}/g, ' ').replace(/ +([.,;:])/g, '$1');
}

function splitSentences(paragraph, lang) {
  let parts;
  if (typeof Intl !== 'undefined' && Intl.Segmenter) {
    const seg = new Intl.Segmenter(lang, { granularity: 'sentence' });
    parts = [...seg.segment(paragraph)].map((s) => s.segment.trim()).filter(Boolean);
  } else {
    parts = paragraph.match(/[^.!?…]+[.!?…]+["”’)]*\s*|[^.!?…]+$/g)?.map((s) => s.trim()).filter(Boolean) || [paragraph];
  }
  // Junta fragmentos curtos gerados por abreviações (Dr., et al., Fig.)
  const merged = [];
  for (const p of parts) {
    const prev = merged[merged.length - 1];
    if (prev && (prev.length < 30 || /\b(et al|Dr|Dra|Sr|Sra|Fig|Figs|Tab|vs|ex|p|pp|n|No|Vol|cap|approx|aprox|e\.g|i\.e)\.$/i.test(prev))) {
      merged[merged.length - 1] = prev + ' ' + p;
    } else {
      merged.push(p);
    }
  }
  // Quebra frases muito longas em vírgulas/ponto e vírgula (limite do Web Speech ~15 s por fala)
  const out = [];
  for (const s of merged) out.push(...splitLong(s, 260));
  return out;
}

function splitLong(s, max) {
  if (s.length <= max) return [s];
  const out = [];
  let rest = s;
  while (rest.length > max) {
    const window = rest.slice(0, max);
    let cut = Math.max(window.lastIndexOf('; '), window.lastIndexOf(', '), window.lastIndexOf(': '), window.lastIndexOf(' — '));
    if (cut < max * 0.4) cut = window.lastIndexOf(' ');
    if (cut <= 0) cut = max;
    out.push(rest.slice(0, cut + 1).trim());
    rest = rest.slice(cut + 1).trim();
  }
  if (rest) out.push(rest);
  return out;
}

// Retorna [{ chapter, segs: [{ text, para }] }]
export function buildSegments(book, opts) {
  const lang = book.lang || 'pt-BR';
  const result = [];
  let stopped = false;
  for (const ch of book.chapters) {
    const segs = [];
    if (!stopped) {
      const paras = ch.text.split(/\n{2,}/);
      for (let pi = 0; pi < paras.length; pi++) {
        const raw = paras[pi].replace(/\n/g, ' ').trim();
        if (!raw) continue;
        if (opts.stopAtReferences && REF_HEADING.test(raw) && isLateEnough(book, ch, pi, paras.length)) {
          stopped = true;
          break;
        }
        const clean = cleanForSpeech(raw, opts).trim();
        if (!clean || !/[\p{L}\p{N}]/u.test(clean)) continue;
        for (const s of splitSentences(clean, lang)) segs.push({ text: s, para: pi });
      }
    }
    result.push({ title: ch.title, segs });
  }
  return result;
}

// Evita cortar em um "Referências" que aparece no sumário no início do documento
function isLateEnough(book, ch, pi, nParas) {
  const idx = book.chapters.indexOf(ch);
  return (idx + pi / nParas) / book.chapters.length > 0.3;
}

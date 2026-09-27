// Extração de texto: PDF, EPUB, MOBI/AZW3 (sem DRM), TXT, HTML, DOCX.
// Saída comum: { title, chapters: [{ title, text }] }

import * as pdfjs from '../vendor/pdf.min.mjs';

pdfjs.GlobalWorkerOptions.workerSrc = new URL('../vendor/pdf.worker.min.mjs', import.meta.url).href;

const JSZip = () => window.JSZip;

export async function parseFile(file, onProgress = () => {}) {
  const name = file.name;
  const ext = name.split('.').pop().toLowerCase();
  const baseTitle = name.replace(/\.[^.]+$/, '');
  const buf = await file.arrayBuffer();

  switch (ext) {
    case 'pdf': return parsePdf(buf, baseTitle, onProgress);
    case 'epub': return parseEpub(buf, baseTitle);
    case 'mobi':
    case 'azw':
    case 'azw3':
    case 'prc': return parseMobi(buf, baseTitle);
    case 'kfx':
      throw new Error('Arquivos .kfx são o formato proprietário (com DRM) do Kindle e não podem ser lidos. Veja o README para alternativas.');
    case 'docx': return parseDocx(buf, baseTitle);
    case 'html':
    case 'htm':
    case 'xhtml': return single(baseTitle, htmlToText(decode(buf)));
    case 'txt':
    case 'md':
    default: return parseTxt(decode(buf), baseTitle);
  }
}

function decode(buf) {
  const utf8 = new TextDecoder('utf-8', { fatal: false }).decode(buf);
  // Se houver muitos caracteres de substituição, tenta latin1 (comum em .txt antigos)
  const bad = (utf8.match(/�/g) || []).length;
  if (bad > 20 && bad / utf8.length > 0.001) return new TextDecoder('windows-1252').decode(buf);
  return utf8.replace(/^﻿/, '');
}

function single(title, text) {
  return { title, chapters: [{ title, text: normalize(text) }] };
}

// ---------- TXT (inclui "My Clippings.txt" do Kindle) ----------
function parseTxt(text, title) {
  if (/==========\r?\n/.test(text) && /\n- .*\|/.test(text)) return parseClippings(text);
  return single(title, text);
}

function parseClippings(text) {
  const byBook = new Map();
  for (const entry of text.split(/==========\r?\n?/)) {
    const lines = entry.trim().split(/\r?\n/);
    if (lines.length < 3) continue;
    const book = lines[0].trim();
    const body = lines.slice(2).join('\n').trim();
    if (!body) continue;
    if (!byBook.has(book)) byBook.set(book, []);
    byBook.get(book).push(body);
  }
  return {
    title: 'Destaques do Kindle',
    chapters: [...byBook].map(([t, notes]) => ({ title: t, text: normalize(notes.join('\n\n')) })),
  };
}

// ---------- PDF ----------
async function parsePdf(buf, fallbackTitle, onProgress) {
  const doc = await pdfjs.getDocument({ data: new Uint8Array(buf), isEvalSupported: false }).promise;
  let title = fallbackTitle;
  try {
    const meta = await doc.getMetadata();
    const t = meta?.info?.Title?.trim();
    if (t && t.length > 3 && !/^(untitled|microsoft word|about:|https?:|file:)|\.(docx?|pdf|tex|indd)$/i.test(t)) title = t;
  } catch {}

  const pages = [];
  for (let p = 1; p <= doc.numPages; p++) {
    const page = await doc.getPage(p);
    const content = await page.getTextContent();
    pages.push(pdfPageLines(content.items));
    onProgress(p / doc.numPages);
  }

  const cleaned = stripRepeatedHeaders(pages);
  // Um "capítulo" por bloco de ~10 páginas mantém a navegação útil em PDFs sem sumário
  const outline = await pdfOutline(doc);
  if (outline.length >= 2) {
    const chapters = [];
    for (let i = 0; i < outline.length; i++) {
      const from = outline[i].page;
      const to = i + 1 < outline.length ? outline[i + 1].page : cleaned.length;
      const text = cleaned.slice(from, Math.max(from + 1, to)).join('\n\n');
      if (text.trim()) chapters.push({ title: outline[i].title, text: normalize(joinPdfLines(text)) });
    }
    if (outline[0].page > 0) {
      const pre = cleaned.slice(0, outline[0].page).join('\n\n');
      if (pre.trim()) chapters.unshift({ title: 'Início', text: normalize(joinPdfLines(pre)) });
    }
    if (chapters.length) return { title, chapters };
  }

  const chapters = [];
  const step = 10;
  for (let i = 0; i < cleaned.length; i += step) {
    const text = normalize(joinPdfLines(cleaned.slice(i, i + step).join('\n\n')));
    if (text) chapters.push({ title: `Páginas ${i + 1}–${Math.min(i + step, cleaned.length)}`, text });
  }
  return { title, chapters };
}

async function pdfOutline(doc) {
  try {
    const outline = await doc.getOutline();
    if (!outline) return [];
    const out = [];
    for (const item of outline) {
      let dest = item.dest;
      if (typeof dest === 'string') dest = await doc.getDestination(dest);
      if (!Array.isArray(dest)) continue;
      const idx = await doc.getPageIndex(dest[0]);
      out.push({ title: item.title, page: idx });
    }
    return out.sort((a, b) => a.page - b.page);
  } catch {
    return [];
  }
}

// Reconstrói linhas a partir das posições dos fragmentos de texto
function pdfPageLines(items) {
  const lines = [];
  let cur = null;
  for (const it of items) {
    if (!('str' in it)) continue;
    const y = Math.round(it.transform[5]);
    if (!cur || Math.abs(cur.y - y) > 2) {
      if (cur) lines.push(cur);
      cur = { y, text: it.str, h: it.height };
    } else {
      cur.text += (needsSpace(cur.text, it.str) ? ' ' : '') + it.str;
    }
    if (it.hasEOL) { lines.push(cur); cur = null; }
  }
  if (cur) lines.push(cur);

  // Linha em branco quando o salto vertical é grande (parágrafo)
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (i > 0 && l.h && Math.abs(lines[i - 1].y - l.y) > l.h * 1.8) out.push('');
    out.push(l.text.trim());
  }
  return out.join('\n');
}

function needsSpace(a, b) {
  return a && b && !/\s$/.test(a) && !/^\s/.test(b);
}

// Remove cabeçalhos/rodapés que se repetem em muitas páginas e números de página isolados
function stripRepeatedHeaders(pages) {
  if (pages.length < 4) return pages;
  const key = (l) => l.replace(/\d+/g, '#').trim();
  const count = new Map();
  for (const p of pages) {
    const lines = p.split('\n').filter(Boolean);
    const edge = new Set([...lines.slice(0, 2), ...lines.slice(-2)].map(key));
    for (const k of edge) count.set(k, (count.get(k) || 0) + 1);
  }
  const threshold = Math.max(3, pages.length * 0.4);
  return pages.map((p) => {
    const lines = p.split('\n');
    const n = lines.length;
    return lines
      .filter((l, i) => {
        const edge = i < 3 || i >= n - 3;
        if (!edge) return true;
        if (/^\s*(página|page|p\.)?\s*\d{1,4}(\s*(de|of|\/)\s*\d+)?\s*$/i.test(l)) return false;
        return !(l.trim() && count.get(key(l)) >= threshold);
      })
      .join('\n');
  });
}

// Junta linhas quebradas pelo layout do PDF, preservando parágrafos
function joinPdfLines(text) {
  return text
    .replace(/(\p{L})-\n(\p{Ll})/gu, '$1$2')        // hifenização de fim de linha
    .replace(/([^\n])\n(?!\n)/g, (m, c) => c + ' ') // quebra simples → espaço
    .replace(/ {2,}/g, ' ');
}

// ---------- EPUB ----------
async function parseEpub(buf, fallbackTitle) {
  const zip = await JSZip().loadAsync(buf);
  const container = await zip.file('META-INF/container.xml')?.async('string');
  if (!container) throw new Error('EPUB inválido (container.xml ausente).');
  const opfPath = xml(container).querySelector('rootfile')?.getAttribute('full-path');
  const opfText = await zip.file(opfPath)?.async('string');
  if (!opfText) throw new Error('EPUB inválido (OPF ausente).');
  if (zip.file('META-INF/encryption.xml')) {
    const enc = await zip.file('META-INF/encryption.xml').async('string');
    if (/EncryptedData/.test(enc) && !/font/i.test(enc)) throw new Error('Este EPUB tem DRM e não pode ser lido.');
  }
  const opf = xml(opfText);
  const base = opfPath.includes('/') ? opfPath.slice(0, opfPath.lastIndexOf('/') + 1) : '';
  const title = opf.querySelector('metadata > title, title')?.textContent?.trim() || fallbackTitle;

  const manifest = new Map();
  for (const item of opf.querySelectorAll('manifest > item')) {
    manifest.set(item.getAttribute('id'), { href: item.getAttribute('href'), type: item.getAttribute('media-type') });
  }
  const tocTitles = await epubTocTitles(zip, opf, manifest, base);

  const chapters = [];
  for (const ref of opf.querySelectorAll('spine > itemref')) {
    const item = manifest.get(ref.getAttribute('idref'));
    if (!item || !/html/.test(item.type || 'html')) continue;
    const path = resolvePath(base, item.href);
    const html = await zip.file(path)?.async('string');
    if (!html) continue;
    const { text, heading } = htmlToTextWithHeading(html);
    if (text.trim().length < 2) continue;
    const t = tocTitles.get(path) || heading || `Seção ${chapters.length + 1}`;
    chapters.push({ title: t, text: normalize(text) });
  }
  if (!chapters.length) throw new Error('Nenhum texto encontrado no EPUB.');
  return { title, chapters };
}

async function epubTocTitles(zip, opf, manifest, base) {
  const map = new Map();
  try {
    // EPUB3 nav
    const navItem = [...opf.querySelectorAll('manifest > item')].find((i) => /\bnav\b/.test(i.getAttribute('properties') || ''));
    if (navItem) {
      const navPath = resolvePath(base, navItem.getAttribute('href'));
      const navBase = navPath.slice(0, navPath.lastIndexOf('/') + 1);
      const doc = new DOMParser().parseFromString(await zip.file(navPath).async('string'), 'text/html');
      for (const a of doc.querySelectorAll('nav a[href]')) {
        const p = resolvePath(navBase, a.getAttribute('href').split('#')[0]);
        if (!map.has(p)) map.set(p, a.textContent.trim());
      }
      if (map.size) return map;
    }
    // EPUB2 NCX
    const ncxId = opf.querySelector('spine')?.getAttribute('toc');
    const ncx = ncxId && manifest.get(ncxId);
    if (ncx) {
      const ncxPath = resolvePath(base, ncx.href);
      const ncxBase = ncxPath.slice(0, ncxPath.lastIndexOf('/') + 1);
      const doc = xml(await zip.file(ncxPath).async('string'));
      for (const np of doc.querySelectorAll('navPoint')) {
        const src = np.querySelector('content')?.getAttribute('src');
        const label = np.querySelector('navLabel text')?.textContent?.trim();
        if (!src || !label) continue;
        const p = resolvePath(ncxBase, src.split('#')[0]);
        if (!map.has(p)) map.set(p, label);
      }
    }
  } catch {}
  return map;
}

function resolvePath(base, href) {
  const parts = (base + decodeURIComponent(href)).split('/');
  const out = [];
  for (const p of parts) {
    if (p === '..') out.pop();
    else if (p !== '.' && p !== '') out.push(p);
  }
  return out.join('/');
}

function xml(s) {
  return new DOMParser().parseFromString(s, 'application/xml');
}

// ---------- DOCX ----------
async function parseDocx(buf, title) {
  const zip = await JSZip().loadAsync(buf);
  const docXml = await zip.file('word/document.xml')?.async('string');
  if (!docXml) throw new Error('DOCX inválido.');
  const doc = xml(docXml);
  const W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main';
  const paras = [...doc.getElementsByTagNameNS(W, 'p')].map((p) =>
    [...p.getElementsByTagNameNS(W, 't')].map((t) => t.textContent).join(''),
  );
  return single(title, paras.join('\n\n'));
}

// ---------- MOBI / AZW3 (somente sem DRM, compressão PalmDOC ou nenhuma) ----------
function parseMobi(buf, fallbackTitle) {
  const dv = new DataView(buf);
  const bytes = new Uint8Array(buf);
  const numRecords = dv.getUint16(76);
  const offsets = [];
  for (let i = 0; i < numRecords; i++) offsets.push(dv.getUint32(78 + i * 8));
  offsets.push(buf.byteLength);
  const rec = (i) => bytes.subarray(offsets[i], offsets[i + 1]);

  const r0 = rec(0);
  const r0v = new DataView(r0.buffer, r0.byteOffset, r0.byteLength);
  const compression = r0v.getUint16(0);
  const textRecordCount = r0v.getUint16(8);
  const encryption = r0v.getUint16(12);
  if (encryption !== 0) {
    throw new Error('Este arquivo Kindle tem DRM. Livros comprados na Amazon são protegidos — veja no README como usar EPUB/PDF.');
  }
  if (compression === 17480) {
    throw new Error('Compressão HUFF/CDIC não suportada. Converta para EPUB (ex.: Calibre) e tente de novo.');
  }

  let title = fallbackTitle;
  let encoding = 1252;
  let extraFlags = 0;
  const hasMobiHeader = String.fromCharCode(...r0.subarray(16, 20)) === 'MOBI';
  if (hasMobiHeader) {
    encoding = r0v.getUint32(28);
    const headerLen = r0v.getUint32(20);
    const nameOff = r0v.getUint32(84);
    const nameLen = r0v.getUint32(88);
    if (headerLen >= 0xe4) extraFlags = r0v.getUint16(0xf2);
    try {
      const dec = new TextDecoder(encoding === 65001 ? 'utf-8' : 'windows-1252');
      const t = dec.decode(r0.subarray(nameOff, nameOff + nameLen)).trim();
      if (t) title = t;
    } catch {}
  }

  const chunks = [];
  for (let i = 1; i <= textRecordCount && i < numRecords; i++) {
    let data = rec(i);
    data = data.subarray(0, data.length - trailingSize(data, extraFlags));
    chunks.push(compression === 2 ? palmDocDecompress(data) : data);
  }
  const total = chunks.reduce((n, c) => n + c.length, 0);
  const all = new Uint8Array(total);
  let pos = 0;
  for (const c of chunks) { all.set(c, pos); pos += c.length; }
  const html = new TextDecoder(encoding === 65001 ? 'utf-8' : 'windows-1252').decode(all);

  // Quebras de página do MOBI (<mbp:pagebreak>) servem como divisão de capítulos
  const parts = html.split(/<mbp:pagebreak\s*\/?>/i);
  const chapters = [];
  for (const part of parts) {
    const { text, heading } = htmlToTextWithHeading(part);
    if (text.trim().length < 2) continue;
    chapters.push({ title: heading || `Seção ${chapters.length + 1}`, text: normalize(text) });
  }
  if (!chapters.length) throw new Error('Nenhum texto encontrado. Se for AZW3/KF8, converta para EPUB com o Calibre.');
  return { title, chapters };
}

// Bytes extras no fim de cada registro de texto (multibyte + TBS), conforme flags do cabeçalho MOBI
function trailingSize(data, flags) {
  let size = 0;
  for (let bit = 15; bit > 0; bit--) {
    if (!(flags & (1 << bit))) continue;
    // Varint lido de trás para frente
    let v = 0;
    let shift = 0;
    for (let i = data.length - size - 1; i >= Math.max(0, data.length - size - 4); i--) {
      const b = data[i];
      v |= (b & 0x7f) << shift;
      shift += 7;
      if (b & 0x80) break;
    }
    size += v;
  }
  if (flags & 1) size += (data[data.length - size - 1] & 0x3) + 1;
  return size;
}

function palmDocDecompress(src) {
  const out = [];
  let i = 0;
  while (i < src.length) {
    const c = src[i++];
    if (c === 0 || (c >= 0x09 && c <= 0x7f)) {
      out.push(c);
    } else if (c >= 0x01 && c <= 0x08) {
      for (let k = 0; k < c && i < src.length; k++) out.push(src[i++]);
    } else if (c >= 0xc0) {
      out.push(0x20, c ^ 0x80);
    } else {
      const pair = (c << 8) | src[i++];
      const dist = (pair >> 3) & 0x7ff;
      const len = (pair & 7) + 3;
      const start = out.length - dist;
      for (let k = 0; k < len; k++) out.push(out[start + k]);
    }
  }
  return Uint8Array.from(out);
}

// ---------- HTML → texto ----------
const BLOCK = 'p,div,h1,h2,h3,h4,h5,h6,li,blockquote,tr,section,article,br,dd,dt,figcaption,pre';

function htmlToTextWithHeading(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  doc.querySelectorAll('script,style,head,nav[epub\\:type="toc"],sup a[href^="#"],a.noteref').forEach((n) => n.remove());
  const heading = doc.querySelector('h1,h2,h3')?.textContent?.replace(/\s+/g, ' ').trim().slice(0, 120) || '';
  doc.querySelectorAll(BLOCK).forEach((el) => {
    if (el.tagName === 'BR') el.replaceWith('\n');
    else { el.prepend('\n\n'); el.append('\n\n'); }
  });
  return { text: doc.body?.textContent || '', heading };
}

function htmlToText(html) {
  return htmlToTextWithHeading(html).text;
}

// ---------- Normalização ----------
export function normalize(text) {
  return text
    .replace(/\r\n?/g, '\n')
    .replace(/[­​﻿]/g, '')
    .replace(/ /g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/ *\n */g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

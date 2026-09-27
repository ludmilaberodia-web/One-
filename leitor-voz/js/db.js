// Biblioteca local (IndexedDB). Os livros nunca saem do aparelho.

const DB_NAME = 'leitor-voz';

let dbPromise;
function open() {
  dbPromise ??= new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore('books', { keyPath: 'id' });
      req.result.createObjectStore('meta', { keyPath: 'id' });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbPromise;
}

async function tx(stores, mode, fn) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const t = db.transaction(stores, mode);
    const req = fn(t);
    t.oncomplete = () => resolve(req?.result);
    t.onerror = () => reject(t.error);
  });
}

// "meta" guarda título, tamanho e progresso; "books" guarda o texto completo.
export async function saveBook(book) {
  const { chapters, ...meta } = book;
  meta.chapterCount = chapters.length;
  meta.chars = chapters.reduce((n, c) => n + c.text.length, 0);
  await tx(['books', 'meta'], 'readwrite', (t) => {
    t.objectStore('books').put({ id: book.id, chapters });
    return t.objectStore('meta').put(meta);
  });
  return meta;
}

export async function getBook(id) {
  const [meta, body] = await Promise.all([
    tx('meta', 'readonly', (t) => t.objectStore('meta').get(id)),
    tx('books', 'readonly', (t) => t.objectStore('books').get(id)),
  ]);
  return meta && body ? { ...meta, chapters: body.chapters } : null;
}

export const deleteBook = (id) =>
  tx(['books', 'meta'], 'readwrite', (t) => {
    t.objectStore('books').delete(id);
    return t.objectStore('meta').delete(id);
  });

export async function listBooks() {
  const all = await tx('meta', 'readonly', (t) => t.objectStore('meta').getAll());
  return all.sort((a, b) => (b.progress?.updatedAt || b.addedAt) - (a.progress?.updatedAt || a.addedAt));
}

export async function updateProgress(id, progress) {
  const meta = await tx('meta', 'readonly', (t) => t.objectStore('meta').get(id));
  if (!meta) return;
  meta.progress = { ...progress, updatedAt: Date.now() };
  await tx('meta', 'readwrite', (t) => t.objectStore('meta').put(meta));
}

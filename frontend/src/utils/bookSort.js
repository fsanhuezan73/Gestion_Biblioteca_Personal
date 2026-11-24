// Orden de la tabla de la colección, en el navegador (la colección se carga completa).

// Texto en español: sin distinguir mayúsculas ni tildes, y «Libro 2» antes que «Libro 10».
const collator = new Intl.Collator('es', { sensitivity: 'base', numeric: true })

// Estado en orden de lectura. Sin estado se muestra (y ordena) como «Quiero leer».
const STATUS_RANK = { 'Quiero leer': 0, Leyendo: 1, Leído: 2 }

function text(value) {
  const trimmed = typeof value === 'string' ? value.trim() : value
  return trimmed ? String(trimmed) : null
}

function number(value) {
  return value === null || value === undefined || value === '' || Number.isNaN(Number(value)) ? null : Number(value)
}

// La fecha que muestra la columna «Lectura»: término si está leído, inicio si se está leyendo.
function readingDate(book) {
  if (book.reading_status === 'Leído') return text(book.finished_at)
  if (book.reading_status === 'Leyendo') return text(book.started_at)
  return null
}

// Cada columna ordenable: cómo obtener su valor y si se compara como texto o número.
export const SORT_COLUMNS = {
  title: { label: 'Título', type: 'text', value: (b) => text(b.title) },
  author: { label: 'Autor', type: 'text', value: (b) => text(b.authors?.[0]) },
  genre: { label: 'Género', type: 'text', value: (b) => text(b.genre) },
  year: { label: 'Año', type: 'number', value: (b) => number(b.year) },
  isbn: { label: 'ISBN', type: 'text', value: (b) => text(b.isbn) },
  status: { label: 'Estado', type: 'number', value: (b) => STATUS_RANK[b.reading_status] ?? 0 },
  // Fechas ISO (AAAA-MM-DD): el orden de texto coincide con el cronológico.
  reading: { label: 'Lectura', type: 'iso', value: readingDate },
  rating: { label: 'Valoración', type: 'number', value: (b) => number(b.rating) },
}

function compareValues(a, b, type) {
  if (type === 'text') return collator.compare(a, b)
  if (type === 'iso') return a < b ? -1 : a > b ? 1 : 0
  return a - b
}

function compareTitles(a, b) {
  return collator.compare(text(a.title) ?? '', text(b.title) ?? '')
}

/**
 * Devuelve una copia ordenada de `books`. Sin columna, mantiene el orden recibido.
 * Los valores vacíos van siempre al final (en ambas direcciones) y los empates se
 * resuelven por título ascendente; si persisten, se conserva el orden recibido.
 */
export function sortBooks(books, key, direction = 'asc') {
  const column = SORT_COLUMNS[key]
  if (!column) return books
  const factor = direction === 'desc' ? -1 : 1
  return books
    .map((book, index) => ({ book, index, value: column.value(book) }))
    .sort((x, y) => {
      const xEmpty = x.value === null
      const yEmpty = y.value === null
      if (xEmpty !== yEmpty) return xEmpty ? 1 : -1
      if (!xEmpty) {
        const result = compareValues(x.value, y.value, column.type) * factor
        if (result !== 0) return result
      }
      return compareTitles(x.book, y.book) || x.index - y.index
    })
    .map(({ book }) => book)
}

/** Siguiente estado al hacer clic en una columna: otra columna empieza ascendente. */
export function nextSort(current, key) {
  if (current?.key === key) return { key, direction: current.direction === 'asc' ? 'desc' : 'asc' }
  return { key, direction: 'asc' }
}

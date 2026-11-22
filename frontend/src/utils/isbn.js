// Utilidades de ISBN. El código de barras de un libro es un EAN-13 que
// empieza con 978 o 979: ese número es el ISBN-13.

/** Deja solo dígitos y la X final de un ISBN-10 ("978-84 450" → "97884450"). */
export function normalizeIsbn(raw) {
  return String(raw ?? '').toUpperCase().replace(/[^0-9X]/g, '')
}

/** Dígito verificador correcto de un ISBN-13 / EAN-13. */
export function isValidIsbn13(value) {
  if (!/^\d{13}$/.test(value)) return false
  const sum = [...value].reduce((acc, d, i) => acc + Number(d) * (i % 2 === 0 ? 1 : 3), 0)
  return sum % 10 === 0
}

/** Dígito verificador correcto de un ISBN-10 (la X vale 10). */
export function isValidIsbn10(value) {
  if (!/^\d{9}[\dX]$/.test(value)) return false
  const sum = [...value].reduce((acc, c, i) => acc + (c === 'X' ? 10 : Number(c)) * (10 - i), 0)
  return sum % 11 === 0
}

/** Convierte un ISBN-10 válido en su ISBN-13 (prefijo 978). */
export function isbn10to13(isbn10) {
  const core = `978${isbn10.slice(0, 9)}`
  const sum = [...core].reduce((acc, d, i) => acc + Number(d) * (i % 2 === 0 ? 1 : 3), 0)
  return `${core}${(10 - (sum % 10)) % 10}`
}

/**
 * ISBN-13 a partir de lo que entregue el lector de códigos de barras, o null si
 * el código no es de un libro (p. ej. revistas 977) o tiene un dígito erróneo.
 * Ignora el suplemento de 5 dígitos (precio) que algunos libros traen al lado.
 */
export function isbnFromBarcode(rawValue) {
  const digits = String(rawValue ?? '').replace(/\D/g, '')
  const match = digits.match(/^97[89]\d{10}/)
  if (!match || !isValidIsbn13(match[0])) return null
  return match[0]
}

/** ISBN-13 a partir de un ISBN-10 o ISBN-13 escrito a mano; null si no es válido. */
export function toIsbn13(raw) {
  const value = normalizeIsbn(raw)
  if (value.length === 13) return isValidIsbn13(value) && /^97[89]/.test(value) ? value : null
  if (value.length === 10) return isValidIsbn10(value) ? isbn10to13(value) : null
  return null
}

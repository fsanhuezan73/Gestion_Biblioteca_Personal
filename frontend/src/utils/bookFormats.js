export const BOOK_FORMATS = [
  { code: 'physical', label: 'Físico' },
  { code: 'kindle', label: 'Kindle' },
  { code: 'apple_books', label: 'Apple Books' },
]

export const WITHOUT_FORMAT_LABEL = 'Sin formato registrado'

export function formatLabels(formats) {
  return BOOK_FORMATS.filter(({ code }) => formats?.includes(code)).map(({ label }) => label)
}

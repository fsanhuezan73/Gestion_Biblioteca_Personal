import { describe, expect, it } from 'vitest'
import { isbn10to13, isbnFromBarcode, isValidIsbn10, isValidIsbn13, normalizeIsbn, toIsbn13 } from './isbn'

describe('ISBN', () => {
  it('normaliza guiones, espacios y la X', () => {
    expect(normalizeIsbn('978-84-450-7747-2')).toBe('9788445077472')
    expect(normalizeIsbn(' 0-306-40615-x ')).toBe('030640615X')
    expect(normalizeIsbn(null)).toBe('')
  })

  it('valida dígitos verificadores', () => {
    expect(isValidIsbn13('9780451524935')).toBe(true)  // 1984
    expect(isValidIsbn13('9780451524936')).toBe(false)
    expect(isValidIsbn13('978045152493')).toBe(false)
    expect(isValidIsbn10('0306406152')).toBe(true)
    expect(isValidIsbn10('080442957X')).toBe(true)
    expect(isValidIsbn10('0306406153')).toBe(false)
  })

  it('convierte ISBN-10 a ISBN-13', () => {
    expect(isbn10to13('0306406152')).toBe('9780306406157')
    expect(isbn10to13('080442957X')).toBe('9780804429573')
  })

  it.each([
    ['9780451524935', '9780451524935'],
    ['9791032305690', '9791032305690'],           // prefijo 979
    ['978045152493551995', '9780451524935'],      // con suplemento de precio
    ['9771234567003', null],                      // revista (ISSN, 977)
    ['7501234567893', null],                      // producto, no libro
    ['9780451524936', null],                      // dígito verificador erróneo
    ['', null],
  ])('código de barras %s → %s', (raw, expected) => {
    expect(isbnFromBarcode(raw)).toBe(expected)
  })

  it('acepta ISBN escritos a mano en 10 o 13 dígitos', () => {
    expect(toIsbn13('978-0-451-52493-5')).toBe('9780451524935')
    expect(toIsbn13('0-306-40615-2')).toBe('9780306406157')
    expect(toIsbn13('12345')).toBeNull()
    expect(toIsbn13('9771234567003')).toBeNull()
  })
})

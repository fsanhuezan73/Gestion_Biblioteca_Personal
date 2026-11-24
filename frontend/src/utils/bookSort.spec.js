import { describe, expect, it } from 'vitest'
import { nextSort, sortBooks } from './bookSort'

const titles = (books) => books.map((b) => b.title)

describe('sortBooks', () => {
  it('sin columna mantiene el orden recibido y no muta el arreglo', () => {
    const books = [{ title: 'B' }, { title: 'A' }]
    expect(sortBooks(books, null)).toBe(books)
    const sorted = sortBooks(books, 'title')
    expect(titles(sorted)).toEqual(['A', 'B'])
    expect(titles(books)).toEqual(['B', 'A'])
  })

  it('ordena texto en español: sin mayúsculas ni tildes y con números naturales', () => {
    const books = [{ title: 'Libro 10' }, { title: 'él' }, { title: 'Libro 2' }, { title: 'Ana' }, { title: 'Éxodo' }]
    expect(titles(sortBooks(books, 'title'))).toEqual(['Ana', 'él', 'Éxodo', 'Libro 2', 'Libro 10'])
    expect(titles(sortBooks(books, 'title', 'desc'))).toEqual(['Libro 10', 'Libro 2', 'Éxodo', 'él', 'Ana'])
  })

  it('ordena por el primer autor', () => {
    const books = [
      { title: 'X', authors: ['Zambra', 'Aira'] },
      { title: 'Y', authors: ['Borges'] },
    ]
    expect(titles(sortBooks(books, 'author'))).toEqual(['Y', 'X'])
  })

  it('ordena números y deja los vacíos al final en ambas direcciones', () => {
    const books = [
      { title: 'Sin año', year: null },
      { title: '1999', year: 1999 },
      { title: '2020', year: 2020 },
      { title: '1850', year: 1850 },
    ]
    expect(titles(sortBooks(books, 'year'))).toEqual(['1850', '1999', '2020', 'Sin año'])
    expect(titles(sortBooks(books, 'year', 'desc'))).toEqual(['2020', '1999', '1850', 'Sin año'])
  })

  it('ordena el estado en orden de lectura; sin estado cuenta como «Quiero leer»', () => {
    const books = [
      { title: 'C', reading_status: 'Leído' },
      { title: 'B', reading_status: 'Leyendo' },
      { title: 'A', reading_status: null },
      { title: 'D', reading_status: 'Quiero leer' },
    ]
    expect(titles(sortBooks(books, 'status'))).toEqual(['A', 'D', 'B', 'C'])
    expect(titles(sortBooks(books, 'status', 'desc'))).toEqual(['C', 'B', 'A', 'D'])
  })

  it('ordena «Lectura» por la fecha que muestra la columna', () => {
    const books = [
      { title: 'Leído marzo', reading_status: 'Leído', started_at: '2026-01-01', finished_at: '2026-03-10' },
      { title: 'Leyendo enero', reading_status: 'Leyendo', started_at: '2026-01-20', finished_at: null },
      { title: 'Leído sin fecha', reading_status: 'Leído', started_at: '2025-01-01', finished_at: null },
      { title: 'Quiero leer', reading_status: 'Quiero leer', started_at: null, finished_at: null },
      { title: 'Leído 2025', reading_status: 'Leído', started_at: null, finished_at: '2025-12-31' },
    ]
    expect(titles(sortBooks(books, 'reading'))).toEqual([
      'Leído 2025', 'Leyendo enero', 'Leído marzo', 'Leído sin fecha', 'Quiero leer',
    ])
    expect(titles(sortBooks(books, 'reading', 'desc')).slice(0, 3)).toEqual(['Leído marzo', 'Leyendo enero', 'Leído 2025'])
  })

  it('desempata por título y deja sin valoración al final', () => {
    const books = [
      { title: 'Zeta', rating: 5 },
      { title: 'Sin estrellas', rating: null },
      { title: 'Alfa', rating: 5 },
      { title: 'Beta', rating: 3 },
    ]
    expect(titles(sortBooks(books, 'rating', 'desc'))).toEqual(['Alfa', 'Zeta', 'Beta', 'Sin estrellas'])
    expect(titles(sortBooks(books, 'rating'))).toEqual(['Beta', 'Alfa', 'Zeta', 'Sin estrellas'])
  })

  it('trata textos vacíos o con espacios como vacíos', () => {
    const books = [{ title: 'Sin género', genre: '  ' }, { title: 'Con género', genre: 'Novela' }]
    expect(titles(sortBooks(books, 'genre', 'desc'))).toEqual(['Con género', 'Sin género'])
  })
})

describe('nextSort', () => {
  it('alterna la dirección en la misma columna y reinicia en otra', () => {
    expect(nextSort(null, 'title')).toEqual({ key: 'title', direction: 'asc' })
    expect(nextSort({ key: 'title', direction: 'asc' }, 'title')).toEqual({ key: 'title', direction: 'desc' })
    expect(nextSort({ key: 'title', direction: 'desc' }, 'title')).toEqual({ key: 'title', direction: 'asc' })
    expect(nextSort({ key: 'title', direction: 'desc' }, 'year')).toEqual({ key: 'year', direction: 'asc' })
  })
})

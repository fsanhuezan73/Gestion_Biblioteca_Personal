import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import BookTable from './BookTable.vue'

const books = [
  { id: 1, title: 'Rayuela', authors: ['Julio Cortázar'], year: 1963, reading_status: 'Leído' },
  { id: 2, title: 'Aura', authors: ['Carlos Fuentes'], year: 1962, reading_status: 'Leyendo' },
  { id: 3, title: 'Ficciones', authors: ['Jorge Luis Borges'], year: null, reading_status: null },
]

function rowTitles(wrapper) {
  return wrapper.findAll('tbody tr td:nth-child(2)').map((td) => td.text())
}

describe('BookTable · orden', () => {
  it('sin orden muestra los libros como llegan y todas las columnas como no ordenadas', () => {
    const wrapper = mount(BookTable, { props: { books } })
    expect(rowTitles(wrapper)).toEqual(['Rayuela', 'Aura', 'Ficciones'])
    const headers = wrapper.findAll('thead th[aria-sort]')
    expect(headers).toHaveLength(8)
    expect(headers.every((th) => th.attributes('aria-sort') === 'none')).toBe(true)
  })

  it('al hacer clic emite el siguiente orden', async () => {
    const wrapper = mount(BookTable, { props: { books, sort: { key: 'title', direction: 'asc' } } })
    await wrapper.get('[data-test="sort-title"]').trigger('click')
    await wrapper.get('[data-test="sort-year"]').trigger('click')
    expect(wrapper.emitted('update:sort')).toEqual([
      [{ key: 'title', direction: 'desc' }],
      [{ key: 'year', direction: 'asc' }],
    ])
  })

  it('ordena las filas y marca la columna activa', async () => {
    const wrapper = mount(BookTable, { props: { books, sort: { key: 'title', direction: 'asc' } } })
    expect(rowTitles(wrapper)).toEqual(['Aura', 'Ficciones', 'Rayuela'])
    const title = wrapper.get('[data-test="sort-title"]')
    expect(title.element.closest('th').getAttribute('aria-sort')).toBe('ascending')
    expect(title.text()).toContain('▲')

    await wrapper.setProps({ sort: { key: 'year', direction: 'desc' } })
    expect(rowTitles(wrapper)).toEqual(['Rayuela', 'Aura', 'Ficciones'])
    expect(wrapper.get('[data-test="sort-year"]').text()).toContain('▼')
    expect(title.element.closest('th').getAttribute('aria-sort')).toBe('none')
  })
})

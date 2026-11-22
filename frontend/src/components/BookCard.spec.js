import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import BookCard from './BookCard.vue'
import BookTable from './BookTable.vue'

const stubs = { RouterLink: { template: '<a><slot /></a>' } }
const read = { id: 1, title: 'Dune', authors: ['Frank Herbert'], reading_status: 'Leído', started_at: '2026-01-05', finished_at: '2026-02-10' }
const reading = { id: 2, title: 'Emma', authors: ['Jane Austen'], reading_status: 'Leyendo', started_at: '2026-03-05' }
const want = { id: 3, title: 'Ulises', authors: ['James Joyce'], reading_status: 'Quiero leer' }

describe('fechas de lectura en la biblioteca', () => {
  it('tarjeta: Leído muestra término y días, Leyendo el inicio', () => {
    const r = mount(BookCard, { props: { book: read }, global: { stubs } })
    expect(r.find('[data-test="reading-summary"]').text()).toMatch(/Término:.*2026.*36 días/)
    const l = mount(BookCard, { props: { book: reading }, global: { stubs } })
    expect(l.find('[data-test="reading-summary"]').text()).toMatch(/Inicio:.*2026/)
    expect(mount(BookCard, { props: { book: want }, global: { stubs } }).find('[data-test="reading-summary"]').exists()).toBe(false)
  })

  it('tabla: columna Lectura con fechas y días', () => {
    const wrapper = mount(BookTable, { props: { books: [read, reading, want] } })
    expect(wrapper.find('thead').text()).toContain('Lectura')
    const cells = wrapper.findAll('[data-test="reading-summary"]').map((c) => c.text())
    expect(cells[0]).toMatch(/Término:.*36 días de lectura/)
    expect(cells[1]).toMatch(/Inicio:/)
    expect(cells[2]).toBe('')
  })
})

import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import BookForm from './BookForm.vue'

describe('BookForm', () => {
  it('validates and emits the payload when the form is valid', async () => {
    const wrapper = mount(BookForm)

    await wrapper.find('#title').setValue('Dune')
    const authorInputs = wrapper.findAll('input[type="text"]')
    await authorInputs[1].setValue('Frank Herbert')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('submit')).toHaveLength(1)
    expect(wrapper.emitted('submit')[0][0]).toMatchObject({
      title: 'Dune',
      authors: ['Frank Herbert'],
      reading_status: 'Quiero leer',
    })
  })
})

describe('BookForm · fechas y páginas', () => {
  async function fillRequired(wrapper) {
    await wrapper.find('#title').setValue('Dune')
    await wrapper.findAll('input[type="text"]')[1].setValue('Frank Herbert')
  }

  it('al marcar Leído propone la fecha de término de hoy y la envía', async () => {
    const wrapper = mount(BookForm)
    await fillRequired(wrapper)
    expect(wrapper.find('#finished_at').exists()).toBe(false)
    await wrapper.find('#reading_status').setValue('Leído')
    const finished = wrapper.find('#finished_at')
    expect(finished.element.value).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    await wrapper.find('#page_count').setValue('412')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')[0][0]).toMatchObject({
      reading_status: 'Leído',
      page_count: 412,
      started_at: null,
      finished_at: finished.element.value,
    })
  })

  it('rechaza un término anterior al inicio', async () => {
    const wrapper = mount(BookForm)
    await fillRequired(wrapper)
    await wrapper.find('#reading_status').setValue('Leído')
    await wrapper.find('#started_at').setValue('2026-03-10')
    await wrapper.find('#finished_at').setValue('2026-03-01')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.text()).toContain('anterior a la de inicio')
  })

  it('no envía fechas ocultas cuando el estado es Quiero leer', async () => {
    const wrapper = mount(BookForm, {
      props: { initialData: { title: 'Dune', authors: ['Frank Herbert'], reading_status: 'Quiero leer', started_at: '2026-01-01' } },
    })
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')[0][0]).toMatchObject({ started_at: null, finished_at: null })
  })
})

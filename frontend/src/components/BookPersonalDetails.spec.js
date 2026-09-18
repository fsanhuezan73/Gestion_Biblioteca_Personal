import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import BookPersonalDetails from './BookPersonalDetails.vue'

const { update } = vi.hoisted(() => ({ update: vi.fn() }))
vi.mock('@/stores/books', () => ({ useBooksStore: () => ({ updatePersonalDetails: update }) }))
const original = { id: 101, rating: 4, personal_notes: 'Nota guardada', reading_status: 'Leyendo' }

beforeEach(() => { update.mockReset() })

function render(book = original) {
  return mount(BookPersonalDetails, { props: { book: { ...book } } })
}

describe('valoración y notas personales', () => {
  it('carga los datos y guarda solo los campos cambiados', async () => {
    const wrapper = render()
    expect(wrapper.find('#personal-rating').element.value).toBe('4')
    expect(wrapper.find('#personal-notes').element.value).toBe('Nota guardada')
    const saved = { ...original, rating: 5 }
    update.mockResolvedValue(saved)
    await wrapper.find('#personal-rating').setValue('5')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(update).toHaveBeenCalledWith(101, { rating: 5 })
    expect(wrapper.emitted('saved')[0]).toEqual([saved])
    await wrapper.setProps({ book: saved })
    expect(wrapper.find('[role="status"]').text()).toContain('guardadas')
    expect(wrapper.find('button[type="submit"]').element.disabled).toBe(true)
  })

  it('permite borrar valoración y notas explícitamente', async () => {
    const wrapper = render()
    update.mockResolvedValue({ ...original, rating: null, personal_notes: null })
    await wrapper.find('#personal-rating').setValue('')
    // Vue conserva null como valor del primer option.
    wrapper.find('#personal-rating').element.selectedIndex = 0
    await wrapper.find('#personal-rating').trigger('change')
    await wrapper.find('#personal-notes').setValue('')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(update).toHaveBeenCalledWith(101, { rating: null, personal_notes: null })
  })

  it('mantiene los borradores ante errores y permite reintentar', async () => {
    const wrapper = render()
    update.mockRejectedValueOnce(new Error('offline'))
    await wrapper.find('#personal-notes').setValue('Mi borrador')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('vuelve a intentarlo')
    expect(wrapper.find('#personal-notes').element.value).toBe('Mi borrador')
    expect(wrapper.emitted('saved')).toBeUndefined()
    update.mockResolvedValue({ ...original, personal_notes: 'Mi borrador' })
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(update).toHaveBeenCalledTimes(2)
    expect(wrapper.emitted('saved')).toHaveLength(1)
  })

  it('rechaza notas demasiado largas y cuenta caracteres Unicode', async () => {
    const wrapper = render()
    await wrapper.find('#personal-notes').setValue('📚'.repeat(5001))
    expect(wrapper.find('#personal-notes-help').text()).toContain('5001 / 5000')
    await wrapper.find('form').trigger('submit')
    expect(update).not.toHaveBeenCalled()
    expect(wrapper.find('[role="alert"]').text()).toContain('5000')
    await wrapper.find('#personal-notes').setValue('📚'.repeat(5000))
    expect(wrapper.find('button[type="submit"]').element.disabled).toBe(false)
  })

  it('descarta cambios y recupera los valores guardados', async () => {
    const wrapper = render()
    await wrapper.find('#personal-notes').setValue('Borrador')
    await wrapper.find('#personal-rating').setValue('1')
    await wrapper.find('button[type="button"]').trigger('click')
    expect(wrapper.find('#personal-notes').element.value).toBe(original.personal_notes)
    expect(wrapper.find('#personal-rating').element.value).toBe('4')
    expect(update).not.toHaveBeenCalled()
  })

  it('cambiar el estado de lectura no borra notas sin guardar', async () => {
    const wrapper = render()
    await wrapper.find('#personal-notes').setValue('Borrador')
    await wrapper.setProps({ book: { ...original, reading_status: 'Leído' } })
    expect(wrapper.find('#personal-notes').element.value).toBe('Borrador')
  })

  it('muestra HTML como texto y conserva saltos de línea', async () => {
    const notes = '<script>alert(1)</script>\nUna cita'
    const wrapper = render({ ...original, personal_notes: notes })
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('#personal-notes').element.value).toBe(notes)
  })

  it('impide envíos duplicados durante un guardado', async () => {
    let complete
    update.mockImplementation(() => new Promise((resolve) => { complete = resolve }))
    const wrapper = render()
    await wrapper.find('#personal-rating').setValue('5')
    await wrapper.find('form').trigger('submit')
    await wrapper.find('form').trigger('submit')
    expect(update).toHaveBeenCalledTimes(1)
    expect(wrapper.find('fieldset').element.disabled).toBe(true)
    complete({ ...original, rating: 5 })
    await flushPromises()
  })
})

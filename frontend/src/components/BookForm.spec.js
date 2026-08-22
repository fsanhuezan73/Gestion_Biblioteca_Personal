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

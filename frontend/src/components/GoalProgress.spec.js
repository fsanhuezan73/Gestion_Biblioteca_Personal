import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import GoalProgress from './GoalProgress.vue'

const goal = (overrides = {}) => ({
  target_books: 24, books_read: 14, percent: 58, expected_to_date: 12, difference: 2,
  remaining: 10, status: 'ahead', ...overrides,
})

describe('GoalProgress', () => {
  it('muestra avance y ritmo', () => {
    const wrapper = mount(GoalProgress, { props: { year: 2026, goal: goal() } })
    expect(wrapper.text()).toContain('14 de 24 libros')
    expect(wrapper.text()).toContain('58% completado')
    expect(wrapper.text()).toContain('Vas 2 libros adelantado')
    expect(wrapper.find('[role="progressbar"]').attributes('aria-valuenow')).toBe('58')
  })

  it.each([
    ['behind', -3, 'Te faltan 3 libros para ir al día'],
    ['completed', 0, 'Meta cumplida'],
    ['on_track', 0.4, 'Vas al día'],
  ])('estado %s', (status, difference, text) => {
    const wrapper = mount(GoalProgress, { props: { year: 2026, goal: goal({ status, difference }) } })
    expect(wrapper.text()).toContain(text)
  })

  it('permite definir una meta y valida el rango', async () => {
    const wrapper = mount(GoalProgress, { props: { year: 2026, goal: null } })
    expect(wrapper.text()).toContain('Sin meta definida')
    await wrapper.find('[data-test="edit-goal"]').trigger('click')
    await wrapper.find('#goal-target').setValue('0')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('save')).toBeUndefined()
    expect(wrapper.text()).toContain('entre 1 y 365')
    await wrapper.find('#goal-target').setValue('30')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('save')[0]).toEqual([30])
  })
})

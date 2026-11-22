import { describe, expect, it } from 'vitest'
import { daysBetween, datesForStatus, formatDate, readingDatesError, todayISO } from './dates'

const TODAY = '2026-07-02'

describe('fechas de lectura', () => {
  it('genera la fecha local de hoy en ISO', () => {
    expect(todayISO(new Date(2026, 0, 5, 23, 59))).toBe('2026-01-05')
  })

  it.each([
    ['Quiero leer', '2026-05-01', '2026-06-01', { started_at: '', finished_at: '' }],
    ['Leyendo', '', '', { started_at: TODAY, finished_at: '' }],
    ['Leyendo', '2026-05-01', '2026-06-01', { started_at: '2026-05-01', finished_at: '' }],
    ['Leído', '', '', { started_at: '', finished_at: TODAY }],
    ['Leído', '2026-05-01', '2026-06-01', { started_at: '2026-05-01', finished_at: '2026-06-01' }],
  ])('%s con %s/%s', (status, started, finished, expected) => {
    expect(datesForStatus(status, started, finished, TODAY)).toEqual(expected)
  })

  it('valida coherencia y fechas futuras', () => {
    expect(readingDatesError('2026-05-01', '2026-06-01', TODAY)).toBe('')
    expect(readingDatesError('2026-06-10', '2026-06-01', TODAY)).toMatch('anterior')
    expect(readingDatesError('2026-08-01', '', TODAY)).toMatch('inicio no puede ser futura')
    expect(readingDatesError('', '2026-08-01', TODAY)).toMatch('término no puede ser futura')
  })

  it('calcula días y formatea sin desfase de zona horaria', () => {
    expect(daysBetween('2026-03-01', '2026-03-31')).toBe(30)
    expect(daysBetween('', '2026-03-31')).toBeNull()
    expect(formatDate('2026-03-05')).toMatch(/5/)
    expect(formatDate('2026-03-05')).toMatch(/2026/)
  })
})

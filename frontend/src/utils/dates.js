// Utilidades de fechas de lectura. La API usa fechas ISO "YYYY-MM-DD".

/** Fecha local de hoy en formato ISO (sin desfase UTC). */
export function todayISO(now = new Date()) {
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** "2026-03-05" → "5 mar 2026" (sin conversión de zona horaria). */
export function formatDate(iso) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('es-CL', { day: 'numeric', month: 'short', year: 'numeric' })
}

/** Días entre dos fechas ISO (fin - inicio). */
export function daysBetween(startIso, endIso) {
  if (!startIso || !endIso) return null
  const toUtc = (iso) => {
    const [y, m, d] = iso.split('-').map(Number)
    return Date.UTC(y, m - 1, d)
  }
  return Math.round((toUtc(endIso) - toUtc(startIso)) / 86400000)
}

/**
 * Fechas automáticas al cambiar el estado (mismas reglas que el backend):
 * Quiero leer → sin fechas · Leyendo → inicio hoy si falta, sin término ·
 * Leído → término hoy si falta, inicio sin cambios.
 */
export function datesForStatus(status, startedAt, finishedAt, today = todayISO()) {
  if (status === 'Quiero leer') return { started_at: '', finished_at: '' }
  if (status === 'Leyendo') return { started_at: startedAt || today, finished_at: '' }
  if (status === 'Leído') return { started_at: startedAt || '', finished_at: finishedAt || today }
  return { started_at: startedAt || '', finished_at: finishedAt || '' }
}

/** Mensaje de error de fechas o '' si son coherentes. */
export function readingDatesError(startedAt, finishedAt, today = todayISO()) {
  if (startedAt && startedAt > today) return 'La fecha de inicio no puede ser futura'
  if (finishedAt && finishedAt > today) return 'La fecha de término no puede ser futura'
  if (startedAt && finishedAt && finishedAt < startedAt) {
    return 'La fecha de término no puede ser anterior a la de inicio'
  }
  return ''
}

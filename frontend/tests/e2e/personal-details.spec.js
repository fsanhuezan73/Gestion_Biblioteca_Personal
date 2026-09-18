import { test, expect } from '@playwright/test'
import { URL } from 'node:url'

test('guardar, recargar y borrar valoraciones y notas privadas', async ({ page }, testInfo) => {
  let book = {
    id: 101, title: '1984', authors: ['George Orwell'], reading_status: 'Leyendo',
    year: 1949, rating: null, personal_notes: null,
  }
  await page.addInitScript(() => localStorage.setItem('auth_token', 'test-token'))
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    let data
    if (path.endsWith('/books/101/personal')) {
      book = { ...book, ...route.request().postDataJSON() }
      data = book
    } else if (path.endsWith('/books/101')) {
      if (route.request().method() === 'DELETE') {
        book = null
        return route.fulfill({ status: 204 })
      }
      data = book
    } else if (path.endsWith('/books/genres')) {
      data = []
    } else if (path.endsWith('/books/')) {
      const summary = { ...book }
      delete summary.personal_notes
      data = book ? [summary] : []
    } else {
      return route.abort()
    }
    await route.fulfill({ json: data })
  })

  await page.goto('/books/101')
  await page.getByLabel('Mi valoración', { exact: true }).selectOption('5')
  await page.getByLabel('Mis notas personales').fill('Mi reseña: inolvidable.\nUna cita para recordar 📚')
  await page.getByRole('button', { name: 'Guardar valoración y notas' }).click()
  await expect(page.getByRole('status')).toHaveText('Valoración y notas guardadas.')
  await page.reload()
  await expect(page.getByLabel('Mi valoración', { exact: true })).toHaveValue('5')
  await expect(page.getByLabel('Mis notas personales')).toHaveValue('Mi reseña: inolvidable.\nUna cita para recordar 📚')

  await page.screenshot({ path: testInfo.outputPath('valoracion-notas-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: testInfo.outputPath('valoracion-notas-mobile.png'), fullPage: true })

  // La protección de navegación permite conservar el borrador al cancelar.
  await page.getByLabel('Mis notas personales').fill('Borrador sin guardar')
  page.once('dialog', (dialog) => dialog.dismiss())
  await page.getByRole('link', { name: '← Volver', exact: true }).click()
  await expect(page).toHaveURL(/books\/101$/)
  await expect(page.getByLabel('Mis notas personales')).toHaveValue('Borrador sin guardar')
  await page.getByRole('button', { name: 'Descartar cambios' }).click()

  await page.getByRole('link', { name: '← Volver', exact: true }).click()
  await expect(page.getByLabel('5 de 5 estrellas')).toBeVisible()
  await page.getByRole('button', { name: '☰ Tabla' }).click()
  await expect(page.getByRole('columnheader', { name: 'Valoración' })).toBeVisible()
  await expect(page.getByLabel('5 de 5 estrellas')).toBeVisible()

  await page.goto('/books/101')
  await page.getByLabel('Mi valoración', { exact: true }).selectOption({ label: 'Sin valorar' })
  await page.getByLabel('Mis notas personales').fill('')
  await page.getByRole('button', { name: 'Guardar valoración y notas' }).click()
  await expect(page.getByRole('status')).toHaveText('Valoración y notas guardadas.')
  await page.reload()
  await expect(page.getByLabel('Mi valoración', { exact: true }).locator('option:checked')).toHaveText('Sin valorar')
  await expect(page.getByLabel('Mis notas personales')).toHaveValue('')

  // Tras confirmar la eliminación no debe aparecer otro aviso por el borrador.
  await page.getByLabel('Mis notas personales').fill('Borrador antes de borrar')
  const unexpectedDialogs = []
  page.on('dialog', async (dialog) => {
    unexpectedDialogs.push(dialog.message())
    await dialog.dismiss()
  })
  await page.getByRole('button', { name: '🗑️ Eliminar', exact: true }).click()
  await page.getByRole('button', { name: 'Sí, eliminar', exact: true }).click()
  await expect(page).toHaveURL(/library/)
  expect(unexpectedDialogs).toEqual([])
})

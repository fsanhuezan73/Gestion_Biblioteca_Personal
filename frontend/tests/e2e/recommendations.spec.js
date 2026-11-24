import { test, expect } from '@playwright/test'
import { URL } from 'node:url'

// API simulada: la IA nunca se llama de verdad.
test('recomendaciones: generar, ver motivo y sinopsis, y agregar a Quiero leer', async ({ page }) => {
  let state = {
    recommendations: [], provider: null, model: null, generated_at: null,
    remaining_today: 5, daily_limit: 5, rated_books: 3, min_rated_books: 3,
  }
  let saved = null
  const books = [{ id: 1, title: 'Rayuela', authors: ['Julio Cortázar'], reading_status: 'Leído', rating: 5 }]

  await page.addInitScript(() => localStorage.setItem('auth_token', 'test-token'))
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path.endsWith('/ai/recommendations') && request.method() === 'POST') {
      state = {
        ...state,
        recommendations: [
          {
            title: 'Cien años de soledad', authors: ['Gabriel García Márquez'], year: 1967,
            reason: 'Como Rayuela, juega con el tiempo y la memoria.',
            synopsis: 'La historia de siete generaciones de la familia Buendía en Macondo.',
            cover_url: null, isbn: '9788497592208', publisher: 'Sudamericana', page_count: 471, in_library: false,
          },
          {
            title: 'Aura', authors: ['Carlos Fuentes'], reason: 'Una novela breve y extraña.',
            synopsis: null, cover_url: null, isbn: null, in_library: false,
          },
        ],
        provider: 'gemini', model: 'gemini-3.5-flash-lite', generated_at: '2026-11-23T15:00:00Z', remaining_today: 4,
      }
      return route.fulfill({ json: state })
    }
    if (path.endsWith('/ai/recommendations')) return route.fulfill({ json: state })
    if (path.endsWith('/books/') && request.method() === 'POST') {
      saved = request.postDataJSON()
      return route.fulfill({ status: 201, json: { id: 99, ...saved } })
    }
    if (path.endsWith('/books/')) return route.fulfill({ json: books })
    if (path.endsWith('/books/genres')) return route.fulfill({ json: [] })
    if (path.endsWith('/stats/')) return route.abort()
    return route.fulfill({ status: 404, json: {} })
  })

  // «Para ti» ya no aparece en la colección: se abre desde el menú.
  await page.goto('/library')
  await expect(page.getByText('Rayuela')).toBeVisible()
  await expect(page.getByTestId('recommendations')).toHaveCount(0)
  await page.getByRole('button', { name: 'Abrir menú' }).click()
  await page.getByRole('link', { name: 'Para ti' }).click()
  await expect(page).toHaveURL(/\/for-you$/)
  const section = page.getByTestId('recommendations')
  await expect(section.getByTestId('ai-label')).toHaveText('Generado por IA')
  await expect(section.getByTestId('remaining')).toHaveText('Te quedan 5 de 5 hoy')

  await section.getByTestId('generate-recommendations').click()
  const cards = section.getByTestId('recommendation')
  await expect(cards).toHaveCount(2)
  await expect(cards.first().getByTestId('reason')).toContainText('juega con el tiempo')
  await expect(cards.first().getByTestId('synopsis')).toContainText('familia Buendía')
  await expect(cards.nth(1).getByTestId('synopsis')).toHaveCount(0)
  await expect(section.getByTestId('remaining')).toHaveText('Te quedan 4 de 5 hoy')

  await cards.first().getByTestId('add-want-to-read').click()
  await expect(cards.first().getByTestId('in-library')).toBeVisible()
  await expect(page.getByRole('alert').filter({ hasText: 'se agregó a Quiero leer' })).toBeVisible()
  expect(saved).toEqual({
    title: 'Cien años de soledad', authors: ['Gabriel García Márquez'], isbn: '9788497592208', year: 1967,
    publisher: 'Sudamericana', cover_url: null, page_count: 471, reading_status: 'Quiero leer',
  })
})

test('recomendaciones: sin libros valorados suficientes no se puede generar', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('auth_token', 'test-token'))
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/ai/recommendations')) {
      return route.fulfill({ json: {
        recommendations: [], remaining_today: 5, daily_limit: 5, rated_books: 1, min_rated_books: 3,
      } })
    }
    if (path.endsWith('/books/')) return route.fulfill({ json: [] })
    if (path.endsWith('/books/genres')) return route.fulfill({ json: [] })
    return route.abort()
  })
  await page.goto('/for-you')
  await expect(page.getByTestId('not-enough')).toContainText('llevas 1')
  await expect(page.getByTestId('generate-recommendations')).toBeDisabled()
})

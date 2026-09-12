import { test, expect } from '@playwright/test'

test('login flow redirects to the library view', async ({ page }) => {
  await page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: 'demo-token', token_type: 'bearer' }),
    })
  })

  await page.route('**/api/v1/books/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  await page.route('**/api/v1/books/genres', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  await page.goto('/login')

  await page.getByLabel('Correo electrónico').fill('user@example.com')
  await page.getByLabel('Contraseña').fill('secret123')
  await page.getByRole('button', { name: 'Ingresar' }).click()

  await expect(page).toHaveURL(/\/library/)
  await expect(page.getByText('Biblioteca Personal')).toBeVisible()
})

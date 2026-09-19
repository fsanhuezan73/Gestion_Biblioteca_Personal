import { test, expect } from '@playwright/test'

test('request and reset use generic copy and remove the link token from the URL', async ({ page }) => {
  await page.route('**/api/v1/auth/password-reset/request', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Si el correo está registrado, recibirás un enlace de recuperación.' }),
    })
  })
  await page.route('**/api/v1/auth/password-reset/confirm', async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      token: 'reset-secret', new_password: 'NewPassword123',
    })
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Contraseña actualizada.' }),
    })
  })

  await page.goto('/forgot-password')
  await page.getByLabel('Correo electrónico').fill('user@example.com')
  await page.getByRole('button', { name: 'Enviar enlace' }).click()
  await expect(page.getByRole('status')).toContainText('Si el correo está registrado')

  await page.goto('/reset-password?token=reset-secret')
  await expect(page).toHaveURL(/\/reset-password$/)
  await page.getByLabel('Nueva contraseña', { exact: true }).fill('NewPassword123')
  await page.getByLabel('Confirma la contraseña').fill('NewPassword123')
  await page.getByRole('button', { name: 'Restablecer contraseña' }).click()
  await expect(page.getByRole('status')).toContainText('sesiones anteriores')
  await expect(page.getByRole('link', { name: 'Iniciar sesión' })).toBeVisible()
})

test('account password change clears local session and returns to login', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('auth_token', 'old-token'))
  await page.route('**/api/v1/auth/password/change', async (route) => {
    expect(route.request().headers().authorization).toBe('Bearer old-token')
    expect(route.request().postDataJSON()).toEqual({
      current_password: 'CurrentPassword123', new_password: 'NewPassword123',
    })
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Contraseña actualizada.' }),
    })
  })

  await page.goto('/account')
  await page.getByLabel('Contraseña actual').fill('CurrentPassword123')
  await page.getByLabel('Nueva contraseña', { exact: true }).fill('NewPassword123')
  await page.getByLabel('Confirma la nueva contraseña').fill('NewPassword123')
  await page.getByRole('button', { name: 'Guardar nueva contraseña' }).click()
  await expect(page).toHaveURL(/\/login\?passwordChanged=1/)
  expect(await page.evaluate(() => localStorage.getItem('auth_token'))).toBeNull()
})

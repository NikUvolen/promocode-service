import { expect, test } from '@playwright/test'

test('verified user logs in through the live API', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill('ci-user@example.com')
  await page.locator('#password').fill('StrongPassword123!')
  await page.getByRole('button', { name: 'Войти' }).click()

  await expect(page).toHaveURL(/\/account$/)
  await expect(page.getByLabel('Email')).toHaveValue('ci-user@example.com')
})

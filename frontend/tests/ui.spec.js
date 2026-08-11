import { expect, test } from '@playwright/test'

test('landing is visible without horizontal overflow', async ({ page }, testInfo) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { level: 1, name: 'GEAR DROP' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Участвовать' }).first()).toBeVisible()
  await expect(page.locator('.hero')).toHaveCSS('background-image', /gaming-hero\.png/)

  const hasOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasOverflow).toBe(false)

  await page.screenshot({
    path: testInfo.outputPath('landing.png'),
    fullPage: true,
  })
})

test('auth routes render their forms', async ({ page }, testInfo) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { level: 1, name: 'Войти' })).toBeVisible()
  await expect(page.getByLabel('Email')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('login.png'), fullPage: true })

  await page.goto('/register')
  await expect(page.getByRole('heading', { level: 1, name: 'Регистрация' })).toBeVisible()
  await expect(page.getByText('Согласен на обработку персональных данных')).toBeVisible()

  await page.goto('/forgot-password')
  await expect(page.getByRole('heading', { level: 1, name: 'Забыли пароль?' })).toBeVisible()
})

import { expect, test } from '@playwright/test'

const emptyProfile = {
  email: 'user@example.com',
  first_name: '',
  last_name: '',
  middle_name: '',
  no_middle_name: false,
  phone: '',
  is_complete: false,
}

async function mockProfileApi(page) {
  await page.route('**/api/v1/auth/profile/', async (route) => {
    if (route.request().method() === 'PATCH') {
      const requestProfile = route.request().postDataJSON()
      await route.fulfill({
        json: {
          ...emptyProfile,
          ...requestProfile,
          is_complete: true,
        },
      })
      return
    }
    await route.fulfill({ json: emptyProfile })
  })
}

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

test('page shells use the same container boundary', async ({ page }) => {
  await page.goto('/')
  const landingBrand = await page.locator('.site-header .brand').boundingBox()
  const hero = await page.locator('.hero').boundingBox()
  expect(Math.abs(landingBrand.x - hero.x)).toBeLessThanOrEqual(1)

  await page.goto('/login')
  const authBrand = await page.locator('.auth-header .brand').boundingBox()
  const authMain = await page.locator('.auth-main').boundingBox()
  expect(Math.abs(authBrand.x - authMain.x)).toBeLessThanOrEqual(1)
})

test('account header and content share a container', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      'gear-drop.tokens',
      JSON.stringify({ access: 'preview', refresh: 'preview' }),
    )
  })
  await mockProfileApi(page)
  await page.goto('/account')

  const accountBrand = await page.locator('.account-header .brand').boundingBox()
  const accountMain = await page.locator('.account-main').boundingBox()
  expect(Math.abs(accountBrand.x - accountMain.x)).toBeLessThanOrEqual(1)
})

test('profile can be viewed and updated', async ({ page }, testInfo) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      'gear-drop.tokens',
      JSON.stringify({ access: 'preview', refresh: 'preview' }),
    )
  })
  await mockProfileApi(page)
  await page.goto('/account')

  await expect(page.getByLabel('Email')).toHaveValue('user@example.com')
  await page.getByLabel('Фамилия').fill('Иванов')
  await page.getByLabel('Имя').fill('Михаил')
  await page.getByText('Нет отчества').click()
  await page.getByLabel('Телефон').fill('80055')
  await page.getByRole('button', { name: 'Сохранить профиль' }).click()
  await expect(page.getByText('Введите 10 цифр номера телефона.')).toBeVisible()

  await page.getByLabel('Телефон').fill('+78005553535')
  await expect(page.getByLabel('Телефон')).toHaveValue('(800) 555-35-35')
  await page.getByRole('button', { name: 'Сохранить профиль' }).click()

  await expect(page.getByText('Данные профиля сохранены.')).toBeVisible()
  await expect(page.getByLabel('Профиль заполнен')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('profile.png'), fullPage: true })
})

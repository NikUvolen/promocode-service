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

async function mockProfileApi(page, currentProfile = emptyProfile) {
  let promoCodeEmailNotifications = true
  await page.route('**/api/v1/auth/profile/', async (route) => {
    if (route.request().method() === 'PATCH') {
      const requestProfile = route.request().postDataJSON()
      await route.fulfill({
        json: {
          ...currentProfile,
          ...requestProfile,
          is_complete: true,
        },
      })
      return
    }
    await route.fulfill({ json: currentProfile })
  })
  await page.route('**/api/v1/auth/notification-settings/', async (route) => {
    if (route.request().method() === 'PATCH') {
      promoCodeEmailNotifications = route.request().postDataJSON().promo_code_email_notifications
    }
    await route.fulfill({
      json: {
        promo_code_email_notifications: promoCodeEmailNotifications,
      },
    })
  })
}

async function mockPromoApi(page, options = {}) {
  const initialCodes = options.initialCodes || []
  let blocked = Boolean(options.initiallyBlocked)
  await page.route('**/api/v1/promo-codes/**', async (route) => {
    if (route.request().url().endsWith('/registration-status/')) {
      await route.fulfill({
        json: blocked
          ? {
              is_blocked: true,
              retry_after: 300,
              blocked_until: '2026-08-12T12:05:00Z',
            }
          : {
              is_blocked: false,
              retry_after: 0,
              blocked_until: null,
            },
      })
      return
    }
    if (route.request().method() === 'POST') {
      if (options.rateLimited) {
        blocked = true
        await route.fulfill({
          status: 429,
          json: {
            detail: 'Слишком много неудачных попыток. Попробуйте позже.',
            reason: 'rate_limited',
            retry_after: 300,
            blocked_until: '2026-08-12T12:05:00Z',
          },
        })
        return
      }
      const { code } = route.request().postDataJSON()
      await route.fulfill({
        status: 201,
        json: {
          code,
          registered_at: '2026-08-12T09:30:00Z',
          status: 'participating',
          prize: null,
        },
      })
      return
    }
    const pageNumber = Number(new URL(route.request().url()).searchParams.get('page') || 1)
    const pageSize = 10
    const start = (pageNumber - 1) * pageSize
    const pageCodes = initialCodes.slice(start, start + pageSize)
    await route.fulfill({
      json: {
        count: initialCodes.length,
        next: start + pageSize < initialCodes.length ? `http://api.test/promo-codes/?page=${pageNumber + 1}` : null,
        previous: pageNumber > 1 ? `http://api.test/promo-codes/?page=${pageNumber - 1}` : null,
        results: pageCodes,
      },
    })
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
  await mockPromoApi(page)
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
  await mockPromoApi(page)
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
  const notificationSwitch = page.getByRole('switch', { name: 'Письма о регистрации промокода' })
  await expect(notificationSwitch).toBeChecked()
  await notificationSwitch.click()
  await expect(notificationSwitch).not.toBeChecked()
  await expect(page.getByText('Настройка сохранена.')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('profile.png'), fullPage: true })
})

test('promo code can be registered', async ({ page }, testInfo) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      'gear-drop.tokens',
      JSON.stringify({ access: 'preview', refresh: 'preview' }),
    )
  })
  await mockProfileApi(page, {
    ...emptyProfile,
    first_name: 'Михаил',
    last_name: 'Иванов',
    no_middle_name: true,
    phone: '+7 (999) 123-45-67',
    is_complete: true,
  })
  await mockPromoApi(page)
  await page.goto('/account')

  const promoCodeInput = page.getByRole('textbox', { name: 'Промокод' })
  await promoCodeInput.fill('ab12cd34')
  await expect(promoCodeInput).toHaveValue('AB12CD34')
  await page.getByRole('button', { name: 'Зарегистрировать' }).click()

  await expect(page.getByText('Промокод AB12CD34 зарегистрирован.')).toBeVisible()
  await expect(page.locator('.promo-history')).toContainText('AB12CD34')
  await expect(page.locator('.promo-panel__count')).toHaveText('Кодов: 1')
  await page.screenshot({ path: testInfo.outputPath('promo-code.png'), fullPage: true })
})

test('promo code statuses and pagination are displayed', async ({ page }, testInfo) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      'gear-drop.tokens',
      JSON.stringify({ access: 'preview', refresh: 'preview' }),
    )
  })
  await mockProfileApi(page, { ...emptyProfile, is_complete: true })
  const codes = Array.from({ length: 12 }, (_, index) => ({
    code: `CD${String(index).padStart(6, '0')}`,
    registered_at: '2026-08-12T09:30:00Z',
    status: index === 0 ? 'won' : index === 1 ? 'not_won' : 'participating',
    prize: index === 0 ? { code: 'airpods', name: 'AirPods' } : null,
  }))
  await mockPromoApi(page, { initialCodes: codes })

  await page.goto('/account')

  await expect(page.locator('.promo-history__item')).toHaveCount(10)
  await expect(page.getByText('Выиграл', { exact: true })).toBeVisible()
  await expect(page.getByText('Не выиграл', { exact: true })).toBeVisible()
  await expect(page.getByText('Подробности отправлены на вашу почту.', { exact: false })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('promo-statuses.png'), fullPage: true })
  await page.getByRole('button', { name: 'Показать еще (2)' }).click()
  await expect(page.locator('.promo-history__item')).toHaveCount(12)
  await expect(page.getByRole('button', { name: /Показать еще/ })).toHaveCount(0)
})

test('promo rate limit shows countdown', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      'gear-drop.tokens',
      JSON.stringify({ access: 'preview', refresh: 'preview' }),
    )
  })
  await mockProfileApi(page, { ...emptyProfile, is_complete: true })
  await mockPromoApi(page, { rateLimited: true })
  await page.goto('/account')

  const promoCodeInput = page.getByRole('textbox', { name: 'Промокод' })
  await promoCodeInput.fill('AB12CD34')
  await page.getByRole('button', { name: 'Зарегистрировать' }).click()

  await expect(page.getByText('Ввод временно заблокирован')).toBeVisible()
  await expect(page.locator('.promo-ban strong')).toHaveText('05:00')
  await expect(promoCodeInput).toBeDisabled()

  await page.reload()
  await expect(page.getByText('Ввод временно заблокирован')).toBeVisible()
  await expect(page.locator('.promo-ban strong')).toHaveText('05:00')
  await expect(page.getByRole('textbox', { name: 'Промокод' })).toBeDisabled()
})

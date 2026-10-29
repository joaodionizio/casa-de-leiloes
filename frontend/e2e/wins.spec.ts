import { expect, test, type Page } from '@playwright/test'
import { mockApi } from './support/mockApi'
const WIN = { lot_id: '00000000-0000-0000-0000-000000000001', title: 'Obra arrematada', artist_display: 'Artista', image_url: '/api/catalog/images/abc-123', phase: 'ended', settlement_status: 'settled', result: 'won', winner_alias: 'Licitante-0123456789ABCDEF', final_amount_cents: 123456, settled_at: '2026-10-28T12:00:00Z', bid_count: 3 }
async function winsApi(page: Page, items: unknown[] = [WIN], status = 200) {
  let requests = 0
  await page.route('**/api/me/wins', route => {
    requests++
    return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify({ as_of: '2026-10-28T12:01:00Z', items }) })
  })
  return () => requests
}
test('anonymous returns after login; auctioneer never calls wins', async ({ page }) => {
  await mockApi(page)
  await winsApi(page)
  await page.goto('/bidder/wins')
  await expect(page).toHaveURL(/\/login$/)
  await page.getByLabel('E-mail').fill('bidder1@example.com')
  await page.getByLabel('Senha').fill('Demo123!')
  await page.getByRole('button', { name: 'Entrar', exact: true }).click()
  await expect(page).toHaveURL(/\/bidder\/wins$/)
  await expect(page.getByRole('heading', { name: 'Meus arremates' })).toBeVisible()
  const other = await page.context().newPage()
  await mockApi(other, { session: 'AUCTIONEER' })
  const count = await winsApi(other)
  await other.goto('/bidder/wins')
  await expect(other.getByRole('heading', { name: 'Área do licitante' })).toBeVisible()
  expect(count()).toBe(0)
})
test('list shows BRL/date and public actions; only winners have receipt and copy', async ({ page }) => {
  await mockApi(page, { session: 'BIDDER', images: 'broken' })
  await winsApi(page, [WIN, { ...WIN, lot_id: '00000000-0000-0000-0000-000000000002', title: 'Participação pendente', result: null, settlement_status: 'pending', winner_alias: null, final_amount_cents: null, settled_at: null }])
  await page.goto('/bidder/wins')
  await expect(page.getByText('Encerrado, apurando resultado', { exact: true })).toBeVisible()
  await expect(page.getByText(/1\.234,56/)).toContainText('2026')
  await expect(page.getByText(/1\.234,56/)).toContainText(WIN.winner_alias)
  await expect(page.getByRole('link', { name: 'Comprovante', exact: true })).toHaveCount(1)
  await expect(page.getByRole('link', { name: 'Comprovante', exact: true })).toHaveAttribute('href', `/lots/${WIN.lot_id}/receipt`)
  await expect(page.getByRole('link', { name: 'Auditoria', exact: true })).toHaveCount(2)
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.getByRole('button', { name: 'Copiar link' }).click()
  await expect(page.getByText('Link copiado.')).toBeVisible()
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(`http://127.0.0.1:4173/lots/${WIN.lot_id}/receipt`)
})
test('clipboard failure exposes selectable absolute URL', async ({ page }) => {
  await mockApi(page, { session: 'BIDDER' })
  await winsApi(page)
  await page.addInitScript(() => Object.defineProperty(navigator, 'clipboard', { value: { writeText: () => Promise.reject(new Error('denied')) } }))
  await page.goto('/bidder/wins')
  await page.getByRole('button', { name: 'Copiar link' }).click()
  await expect(page.getByRole('alert')).toContainText('Não foi possível copiar')
  const input = page.getByLabel('Link do comprovante')
  await expect(input).toHaveValue(`http://127.0.0.1:4173/lots/${WIN.lot_id}/receipt`)
  await input.focus()
  expect(await input.evaluate((node: HTMLInputElement) => node.selectionEnd! - node.selectionStart!)).toBe((await input.inputValue()).length)
})
test('loading, error/retry and empty state', async ({ page }) => {
  await mockApi(page, { session: 'BIDDER' })
  let release: () => void = () => undefined
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/me/wins', async route => { await held; await route.fulfill({ status: 500, body: '{}' }) })
  await page.goto('/bidder/wins')
  await expect(page.getByText('Carregando arremates…')).toBeVisible()
  release()
  await expect(page.getByRole('alert')).toContainText('Não foi possível carregar')
  await winsApi(page, [])
  await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByText(/Você ainda não participou/)).toBeVisible()
})
test('expired session returns to login', async ({ page }) => {
  await mockApi(page, { session: 'BIDDER' })
  await winsApi(page, [], 401)
  await page.goto('/bidder/wins')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByText(/sessão expirou/i)).toBeVisible()
})
test('50 long titles and large amounts fit at 320/375/1440px', async ({ page }) => {
  await mockApi(page, { session: 'BIDDER' })
  await winsApi(page, Array.from({ length: 50 }, (_, i) => ({ ...WIN, lot_id: `00000000-0000-0000-0000-${String(i + 1).padStart(12, '0')}`, title: 'Uma obra de título longo '.repeat(8), final_amount_cents: Number.MAX_SAFE_INTEGER })))
  for (const width of [320, 375, 1440]) {
    await page.setViewportSize({ width, height: width === 1440 ? 900 : 812 })
    await page.goto('/bidder/wins')
    await expect(page.locator('.my-win')).toHaveCount(50)
    await expect(page.locator('.my-win h2').first()).toHaveAccessibleName('Uma obra de título longo '.repeat(8).trim())
    for (const action of await page.locator('.my-win').first().locator('a, button').all()) {
      await action.scrollIntoViewIfNeeded()
      expect((await action.boundingBox())!.height).toBeGreaterThanOrEqual(43)
      await action.focus()
      expect(await action.evaluate(node => getComputedStyle(node).outlineStyle)).toBe('solid')
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  }
})

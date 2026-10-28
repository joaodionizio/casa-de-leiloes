import { expect, test } from '@playwright/test'
import { lotId, mockApi } from './support/mockApi'

const ID = lotId(1)
const receipt = {
  lot_id: ID, title: 'Obra de teste', artist_display: 'Artista', image_url: '/api/catalog/images/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  winner_alias: 'Licitante-ABCDEF1234567890', winning_bid_sequence: 2, final_amount_cents: 123456,
  settled_at: '2026-10-28T12:30:00Z', bid_count: 2, final_hash: 'a'.repeat(64),
}
for (const width of [320, 1280]) {
  test(`comprovante público e auditoria em ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await mockApi(page)
    await page.route(`**/api/lots/${ID}/receipt`, route => route.fulfill({ json: receipt }))
    await page.goto(`/lots/${ID}/receipt`)
    await expect(page.getByRole('heading', { name: 'Comprovante de arremate' })).toBeVisible()
    await expect(page.getByText('Obra de teste')).toBeVisible()
    await expect(page.getByText('Licitante-ABCDEF1234567890')).toBeVisible()
    await expect(page.getByText('R$ 1.234,56')).toBeVisible()
    await expect(page.locator('time')).toHaveAttribute('datetime', receipt.settled_at)
    await expect(page.getByText('a'.repeat(64))).toBeVisible()
    await expect(page.getByRole('link', { name: 'Consultar auditoria pública' })).toHaveAttribute('href', `/lots/${ID}/audit`)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  })
}
for (const status of [404, 409, 500]) {
  test(`falha ${status} não apresenta comprovante`, async ({ page }) => {
    await mockApi(page)
    await page.route(`**/api/lots/${ID}/receipt`, route => route.fulfill({ status, json: {} }))
    await page.goto(`/lots/${ID}/receipt`)
    await expect(page.getByText(status === 404 ? 'Comprovante não encontrado.' : status === 409 ? 'Não foi possível confirmar a integridade deste comprovante.' : 'Não foi possível carregar o comprovante.')).toBeVisible()
    await expect(page.getByText('Arrematado', { exact: true })).toHaveCount(0)
  })
}

import { expect, test } from '@playwright/test'
import { lotId, makeBids, mockApi } from './support/mockApi'

const ID = lotId(1)
const receipt = {
  lot_id: ID, title: 'Obra de teste', artist_display: 'Artista', image_url: '/api/catalog/images/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  winner_alias: 'Licitante-ABCDEF1234567890', winning_bid_sequence: 2, final_amount_cents: 123456,
  settled_at: '2026-10-28T12:30:00Z', bid_count: 2, final_hash: 'a'.repeat(64),
}
for (const width of [320, 1280]) {
  test(`comprovante público e auditoria em ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    const api = await mockApi(page, { images: 'broken' })
    await page.route(`**/api/lots/${ID}/receipt`, route => route.fulfill({ json: receipt }))
    await page.route(`**/api/lots/${ID}/audit`, route => route.fulfill({ json: {
      lot_id: ID, as_of: receipt.settled_at, integrity: 'verified', phase: 'ended',
      settlement_status: 'settled',
      settlement: { outcome: 'sold', winner_alias: receipt.winner_alias,
        final_amount_cents: receipt.final_amount_cents, bid_count: receipt.bid_count,
        final_hash: receipt.final_hash, settled_at: receipt.settled_at },
      bid_count: receipt.bid_count, final_hash: receipt.final_hash,
      bids: makeBids(2, receipt.final_amount_cents - 1000, [receipt.winner_alias]).map((bid, index) => ({
        ...bid, canonical_version: 1,
        previous_hash: index === 0 ? '0'.repeat(64) : 'b'.repeat(64),
        current_hash: index === 0 ? 'b'.repeat(64) : receipt.final_hash,
      })),
    } }))
    await page.goto(`/lots/${ID}/receipt`)
    await expect(page.getByRole('heading', { name: 'Comprovante de arremate' })).toBeVisible()
    await expect(page.getByText('Obra de teste')).toBeVisible()
    await expect(page.getByText('Artista', { exact: true })).toBeVisible()
    await expect(page.locator('.receipt-art img')).toHaveAttribute('src', '/artwork-placeholder.svg')
    await expect(page.getByText('Imagem indisponível')).toBeVisible()
    expect(api.count(`GET ${receipt.image_url}`)).toBe(1)
    await expect(page.getByText('Licitante-ABCDEF1234567890')).toBeVisible()
    await expect(page.getByText('R$ 1.234,56')).toBeVisible()
    await expect(page.locator('time')).toHaveAttribute('datetime', receipt.settled_at)
    await expect(page.getByText('a'.repeat(64))).toBeVisible()
    await expect(page.locator('.receipt-details dd').filter({ hasText: /^2$/ })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Consultar auditoria pública' })).toHaveAttribute('href', `/lots/${ID}/audit`)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.getByRole('link', { name: 'Consultar auditoria pública' }).click()
    await expect(page).toHaveURL(`/lots/${ID}/audit`)
    await expect(page.getByRole('heading', { name: 'Integridade verificada' })).toBeVisible()
    await expect(page.locator('.audit-events > li')).toHaveCount(2)
    await expect(page.locator('.audit-page img')).toHaveCount(0)
    expect(api.count(`GET ${receipt.image_url}`)).toBe(1)
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

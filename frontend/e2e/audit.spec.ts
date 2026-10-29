import { expect, test, type Page } from '@playwright/test'
import { mockApi, makeLot, makeBids, lotId, AS_OF } from './support/mockApi'
import type { Audit } from '../src/api/audit'
const ID = lotId(1)
function audit(count = 0): Audit {
  const bids = makeBids(count, 10000).map((bid, index) => ({ ...bid, canonical_version: 1 as const,
    previous_hash: index === 0 ? '0'.repeat(64) : index.toString(16).padStart(64, '0'),
    current_hash: (index + 1).toString(16).padStart(64, '0') }))
  return { lot_id: ID, as_of: AS_OF, integrity: 'verified', phase: 'live', settlement_status: 'pending', settlement: null,
    bid_count: count, final_hash: bids.at(-1)?.current_hash ?? '0'.repeat(64), bids }
}
async function respond(page: Page, data: Audit, status = 200) {
  await page.route(`**/api/lots/${ID}/audit`, route => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) }))
}
test('anonymous follows room link and returns; session does not block audit', async ({ page }) => {
  await mockApi(page, { lots: [makeLot(1, 'live')] }); await respond(page, audit(3))
  await page.goto(`/lots/${ID}`)
  await page.getByRole('link', { name: 'Consultar auditoria pública' }).click()
  await expect(page).toHaveURL(`/lots/${ID}/audit`)
  await expect(page.getByRole('heading', { name: 'Integridade verificada' })).toBeVisible()
  await expect(page.locator('.audit-events > li')).toHaveCount(3)
  await page.getByRole('link', { name: 'Sala do lote' }).click()
  await expect(page).toHaveURL(`/lots/${ID}`)
  await page.route('**/api/me', async route => {
    await new Promise(resolve => setTimeout(resolve, 1500)); await route.fulfill({ status: 401, body: '{}' })
  })
  await page.goto(`/lots/${ID}/audit`)
  await expect(page.getByRole('heading', { name: 'Integridade verificada' })).toBeVisible()
})
for (const phase of ['scheduled', 'live', 'ended', 'cancelled'] as const) {
  test(`trusted ${phase} empty state`, async ({ page }) => {
    await mockApi(page); const data = audit(); data.phase = phase
    if (phase === 'cancelled') data.settlement_status = 'not_applicable'
    await respond(page, data); await page.goto(`/lots/${ID}/audit`)
    await expect(page.getByText('Nenhum lance registrado.')).toBeVisible()
    await expect(page.locator('.audit-state')).toHaveText({ scheduled: 'Agendado', live: 'Ao vivo', ended: 'Encerrado, apurando resultado', cancelled: 'Cancelado' }[phase])
  })
}
for (const outcome of ['sold', 'unsold'] as const) {
  test(`persisted ${outcome} result`, async ({ page }) => {
    await mockApi(page); const data = audit(outcome === 'sold' ? 1 : 0)
    data.phase = 'ended'; data.settlement_status = 'settled'
    data.settlement = { outcome, winner_alias: data.bids[0]?.bidder_alias ?? null, final_amount_cents: data.bids[0]?.amount_cents ?? null, bid_count: data.bid_count!, final_hash: data.final_hash!, settled_at: AS_OF }
    await respond(page, data); await page.goto(`/lots/${ID}/audit`)
    await expect(page.getByText(outcome === 'sold' ? /Arrematado por/ : 'Encerrado sem vencedor.')).toBeVisible()
  })
}
test('adulterated withholds data; operational failure retries; 404 is explicit', async ({ page }) => {
  await mockApi(page)
  await respond(page, { ...audit(), integrity: 'adulterated', phase: null, settlement_status: null, settlement: null, bid_count: null, final_hash: null })
  await page.goto(`/lots/${ID}/audit`)
  await expect(page.getByRole('heading', { name: 'Integridade adulterada' })).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('foram retidos')
  await expect(page.getByText('Histórico completo')).toHaveCount(0)
  await respond(page, audit(), 500); await page.reload()
  await expect(page.getByRole('alert')).toContainText('Não foi possível')
  await respond(page, audit()); await page.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(page.getByText('Nenhum lance registrado.')).toBeVisible()
  await respond(page, audit(), 404); await page.reload()
  await expect(page.getByText('Lote não encontrado.')).toBeVisible()
})
for (const width of [320, 375, 1440]) {
  test(`100 events readable at ${width}px with expanded hashes`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 1440 ? 900 : 812 }); await mockApi(page); await respond(page, audit(100))
    await page.goto(`/lots/${ID}/audit`)
    await expect(page.locator('.audit-events > li')).toHaveCount(100)
    const summary = page.getByText('Detalhes técnicos do lance 100', { exact: true })
    await summary.focus()
    await page.keyboard.press('Enter')
    await expect(summary).toBeFocused()
    expect(await summary.evaluate(node => getComputedStyle(node).outlineStyle)).toBe('solid')
    expect((await summary.boundingBox())!.height).toBeGreaterThanOrEqual(43)
    await expect(page.locator('.audit-events > li').last().getByText('Hash atual', { exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  })
}
test('loading and late unmounted responses are ignored', async ({ page }) => {
  const api = await mockApi(page); const held = api.hold(`GET /api/lots/${ID}/audit`)
  await page.goto(`/lots/${ID}/audit`)
  await expect(page.getByRole('status').filter({ hasText: 'Carregando auditoria' })).toBeVisible()
  await page.getByRole('link', { name: 'Sala do lote' }).click(); held.release()
  await expect(page.getByRole('heading', { name: 'Auditoria pública do lote' })).toHaveCount(0)
})

test('changing lot invalidates the previous pending audit', async ({ page }) => {
  await mockApi(page)
  let release: () => void = () => undefined
  const pending = new Promise<void>(resolve => { release = resolve })
  await page.route(`**/api/lots/${ID}/audit`, async route => {
    await pending
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(audit(3)) }).catch(() => undefined)
  })
  const otherId = lotId(2)
  await page.route(`**/api/lots/${otherId}/audit`, route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ...audit(), lot_id: otherId, phase: 'cancelled', settlement_status: 'not_applicable' }) }))
  await page.goto(`/lots/${ID}/audit`)
  await expect(page.getByText('Carregando auditoria…', { exact: true })).toBeVisible()
  await page.evaluate((target) => {
    history.pushState({}, '', `/lots/${target}/audit`)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }, otherId)
  await expect(page.locator('.audit-state')).toHaveText('Cancelado')
  release()
  await expect(page.locator('.audit-lot-id')).toContainText(otherId)
  await expect(page.locator('.audit-events > li')).toHaveCount(0)
})

test('unavailable or cancelled room retains a functional public audit link', async ({ page }) => {
  await mockApi(page)
  await respond(page, { ...audit(), phase: 'cancelled', settlement_status: 'not_applicable' })
  await page.goto(`/lots/${ID}`)
  await page.getByRole('link', { name: 'Consultar auditoria pública' }).click()
  await expect(page.locator('.audit-state')).toHaveText('Cancelado')
})

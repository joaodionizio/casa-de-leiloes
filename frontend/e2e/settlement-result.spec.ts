import { expect, test, type Page, type WebSocketRoute } from '@playwright/test'
import {
  makeBids, makeLot, mockApi, OTHER_ALIAS, OWN_ALIAS, lotId, type MockBid,
} from './support/mockApi'

const ID = lotId(201)
const settledAt = '2026-10-25T17:00:00.123456Z'

async function openSettledRoom(
  page: Page,
  bids: MockBid[],
  winnerAlias: string | null,
  failPrivate = false,
) {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'onLine', { get: () => false })
  })
  const lot = makeLot(201, 'ended', { settlement_status: 'settled' })
  await mockApi(page, {
    session: 'BIDDER',
    lots: [lot],
    rooms: { [ID]: { bids } },
    wallet: { total: 100_000, committed: 0 },
  })
  await page.route(`**/api/lots/${ID}/bids`, route => {
    const latest = bids.at(-1)
    return route.fulfill({ status: 200, json: {
      as_of: '2026-10-25T17:00:01.123456Z',
      phase: 'ended',
      ends_at: lot.ends_at,
      current_bid_cents: latest?.amount_cents ?? null,
      minimum_next_bid_cents: null,
      bid_count: bids.length,
      bids: [...bids].reverse(),
      settlement_status: 'settled',
      settlement: {
        outcome: winnerAlias === null ? 'unsold' : 'sold',
        winner_alias: winnerAlias,
        final_amount_cents: latest?.amount_cents ?? null,
        bid_count: bids.length,
        final_hash: (winnerAlias === null ? '0' : 'a').repeat(64),
        settled_at: settledAt,
      },
    } })
  })
  if (failPrivate) {
    await page.route(`**/api/lots/${ID}/bids/mine`, route =>
      route.fulfill({ status: 503, json: { code: 'internal_error' } }))
  }
  await page.goto(`/lots/${ID}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
}

test('winner sees confirmed result, final price and receipt', async ({ page }) => {
  await openSettledRoom(page, makeBids(2, 11_000, [OTHER_ALIAS, OWN_ALIAS]), OWN_ALIAS)
  await expect(page.getByRole('heading', { name: 'Você arrematou esta obra!' })).toBeVisible()
  await expect(page.locator('.bid-settlement-notice')).toContainText('R$ 120,00')
  await expect(page.getByRole('link', { name: 'Acessar seu comprovante' }))
    .toHaveAttribute('href', `/lots/${ID}/receipt`)
  await expect(page.getByText('Não foi possível carregar sua participação.')).toHaveCount(0)
})

test('participant outbid at settlement sees loss, not victory', async ({ page }) => {
  await openSettledRoom(page, makeBids(2, 11_000, [OWN_ALIAS, OTHER_ALIAS]), OTHER_ALIAS)
  await expect(page.getByRole('heading', { name: 'Você não arrematou esta obra.' })).toBeVisible()
})

test('nonparticipant is not labeled as a losing bidder', async ({ page }) => {
  await openSettledRoom(page, makeBids(1, 11_000, [OTHER_ALIAS]), OTHER_ALIAS)
  await expect(page.getByRole('heading', { name: 'Este lote foi arrematado.' })).toBeVisible()
  await expect(page.getByText('Você não deu lances neste lote.')).toBeVisible()
})

test('pending settlement does not announce a winner', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'onLine', { get: () => false })
  })
  await mockApi(page, {
    session: 'BIDDER', lots: [makeLot(201, 'ended')],
    rooms: { [ID]: { bids: makeBids(1, 11_000, [OWN_ALIAS]) } },
  })
  await page.goto(`/lots/${ID}`)
  await expect(page.locator('.room-phase-note')).toHaveText('Encerrado, apurando resultado')
  await expect(page.locator('.bid-settlement-notice')).toHaveCount(0)
})

test('private read failure does not report false victory', async ({ page }) => {
  await openSettledRoom(page, makeBids(2, 11_000, [OTHER_ALIAS, OWN_ALIAS]), OWN_ALIAS, true)
  await expect(page.getByText('Não foi possível confirmar sua participação.', { exact: false })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Você arrematou esta obra!' })).toHaveCount(0)
})

test('unsold lot is marked as such', async ({ page }) => {
  await openSettledRoom(page, [], null)
  await expect(page.getByRole('heading', { name: 'O leilão terminou sem arremate.' })).toBeVisible()
})

test('lot_closed refreshes private bidder information before confirming victory', async ({ page }) => {
  const id = lotId(1)
  const bids = makeBids(1, 11_000, [OWN_ALIAS])
  const api = await mockApi(page, {
    session: 'BIDDER', lots: [makeLot(1, 'live')],
    rooms: { [id]: { bids } }, wallet: { total: 100_000, committed: 11_000 },
  })
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', socket => {
    sockets.push(socket)
    socket.onMessage(data => {
      const payload = JSON.parse(String(data)) as { type?: string; id?: number }
      if (payload.type === 'ping') socket.send(JSON.stringify({ type: 'pong', id: payload.id }))
    })
    socket.send(JSON.stringify({
      type: 'room_snapshot', lot_id: id,
      room: {
        as_of: '2026-10-25T14:30:00.123456Z',
        phase: 'live', ends_at: '2026-10-25T17:00:00Z',
        current_bid_cents: 11_000, minimum_next_bid_cents: 12_000,
        bid_count: 1, bids: [...bids].reverse(),
        settlement_status: 'pending', settlement: null,
      },
    }))
  })
  await page.goto(`/lots/${id}`)
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  const mine = `GET /api/lots/${id}/bids/mine`
  await expect.poll(() => api.count(mine)).toBeGreaterThan(0)
  const before = api.count(mine)
  const socket = sockets[0]
  if (socket === undefined) throw Error('WebSocket not opened')
  socket.send(JSON.stringify({
    type: 'lot_closed', lot_id: id, as_of: settledAt,
    outcome: 'sold', winner_alias: OWN_ALIAS, final_amount_cents: 11_000,
    bid_count: 1, final_hash: 'a'.repeat(64), settled_at: settledAt,
  }))
  await expect(page.getByRole('heading', { name: 'Você arrematou esta obra!' })).toBeVisible()
  await expect.poll(() => api.count(mine)).toBeGreaterThan(before)
})

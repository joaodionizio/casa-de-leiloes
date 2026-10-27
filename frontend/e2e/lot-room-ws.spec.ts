// Browser tests with simulated public WebSockets and REST. Persistence is tested
// separately with PostgreSQL and the real ASGI transport.
import { expect, test, type Page, type WebSocketRoute } from '@playwright/test'
import { mockApi, makeLots, lotId, makeBids, OTHER_ALIAS, OWN_ALIAS, type MockBid } from './support/mockApi'
interface BidRoom {
  as_of: string; phase: 'live' | 'scheduled' | 'ended'; ends_at: string
  current_bid_cents: number | null; minimum_next_bid_cents: number | null
  bid_count: number; bids: MockBid[]
}

const LOT = lotId(1)
const LOTS = makeLots({ live: 2 })
const ROOM = `GET /api/lots/${LOT}/bids`
const MINE = `GET /api/lots/${LOT}/bids/mine`
function state(count = 0, extra: Partial<BidRoom> = {}): BidRoom {
  return {
    as_of: '2026-10-25T14:31:00.123456Z', phase: 'live',
    ends_at: '2026-10-25T17:00:00Z', current_bid_cents: count ? 10000 + count * 1000 : null,
    minimum_next_bid_cents: count ? 11000 + count * 1000 : 11000,
    bid_count: count, bids: makeBids(count, 11000).reverse(), ...extra,
  }
}
function send(socket: WebSocketRoute, room: BidRoom, type = 'bid_accepted', id = LOT) {
  socket.send(JSON.stringify({ type, lot_id: id, room }))
}

test('snapshots replace state, preserve input/focus, coalesce duplicates and expose disconnect without retry', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  const api = await mockApi(page, { lots: LOTS, session: 'BIDDER', wallet: { total: 500000, committed: 0 } })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  await expect.poll(() => api.count(MINE)).toBeGreaterThan(0)
  const input = page.getByLabel('Valor do lance')
  await input.fill('333,00')
  const next = state(2, { bids: makeBids(2, 11000).reverse(), ends_at: '2026-10-25T18:00:00Z' })
  api.setBids(LOT, [...next.bids].reverse())
  send(sockets[0], next, 'room_snapshot')
  await expect(page.locator('.bid-current')).toHaveText('R$\u00a0120,00')
  await expect(page.locator('.bid-minimum')).toHaveText('R$\u00a0130,00')
  await expect(input).toHaveValue('333,00')
  await expect(input).toBeFocused()
  await expect.poll(() => api.count(MINE)).toBeGreaterThan(1)
  // Await private response before measuring: identical message has no new round.
  await expect(page.getByText('Seu pseudônimo neste lote:', { exact: false })).toBeVisible()
  const calls = api.count(MINE)
  const clockBefore = await page.locator('.as-of').textContent()
  // The server renews `as_of` on every reread: same public state, newer reading. The clock
  // is re-anchored but no private revalidation starts.
  send(sockets[0], { ...next, as_of: '2026-10-25T14:35:00.000000Z' })
  await expect(page.locator('.as-of')).not.toHaveText(clockBefore!)
  expect(api.count(MINE)).toBe(calls)
  send(sockets[0], next)
  send(sockets[0], state(1))
  send(sockets[0], state(3), 'bid_accepted', lotId(2))
  await expect(page.locator('.bid-current')).toHaveText('R$\u00a0120,00')
  expect(api.count(MINE)).toBe(calls)
  await sockets[0].close({ code: 1011 })
  await expect(page.getByText('Atualizações ao vivo indisponíveis.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect.poll(() => api.count(ROOM)).toBeGreaterThan(1)
  // Fresh by manual reading, live updates still out; the socket is not "connected" again.
  await expect(page.getByText('Dados atualizados por leitura manual', { exact: false })).toBeVisible()
  await expect(page.getByText('Estado desatualizado', { exact: false })).toHaveCount(0)
  await expect(page.getByText('Sala conectada', { exact: false })).toHaveCount(0)
  expect(sockets).toHaveLength(1)
  expect(api.bidPosts).toHaveLength(0)
})

test('old REST cannot replace WS and terminal cancellation at zero cannot be reversed', async ({ page }) => {
  let socket: WebSocketRoute
  await page.routeWebSocket('**/ws/lots/*', (value) => { socket = value })
  const api = await mockApi(page, { lots: LOTS })
  const held = api.hold(ROOM)
  await page.goto(`/lots/${LOT}`)
  await expect.poll(() => api.count(ROOM)).toBe(1)
  send(socket!, state(2), 'room_snapshot')
  held.release()
  await expect(page.locator('.bid-current')).toHaveText('R$\u00a0120,00')
  send(socket!, state(2, { as_of: '2026-10-25T14:31:00.123455Z', phase: 'ended' }))
  await expect(page.getByText('Encerrado, apurando resultado')).toHaveCount(0)
  send(socket!, state(2, { as_of: '2026-10-25T14:31:00.123457Z', phase: 'ended' }))
  await expect(page.getByText('Encerrado, apurando resultado').first()).toBeVisible()
  // Reopen a different mount whose initial room has no bids.
  await page.goto(`/lots/${lotId(2)}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  socket!.send(JSON.stringify({ type: 'lot_cancelled', lot_id: lotId(2), cancelled_at: state().as_of }))
  await expect(page.getByRole('heading', { name: 'Este lote foi cancelado' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Este lote foi cancelado' })).toBeFocused()
  await expect(page.getByRole('link', { name: 'Ir para a vitrine', exact: true })).toBeVisible()
  expect(api.count(MINE)).toBe(0)
  expect(api.count('GET /api/wallet')).toBe(0)
})

test('201 N after WS N+1 confirms attempt and wallet without replacing newer price, minimum, history or end', async ({ page }) => {
  let socket: WebSocketRoute
  await page.routeWebSocket('**/ws/lots/*', (value) => { socket = value })
  const api = await mockApi(page, { lots: LOTS, session: 'BIDDER', wallet: { total: 500000, committed: 0 } })
  let release: () => void = () => undefined
  const gate = new Promise<void>((resolve) => { release = resolve })
  let posted = false
  await page.route(`**/api/lots/${LOT}/bids`, async (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    posted = true
    await gate
    await route.fulfill({ status: 201, json: {
      bid: { sequence: 1, bidder_alias: OWN_ALIAS, amount_cents: 11000, placed_at: '2026-10-25T14:30:00Z' },
      lot: { current_bid_cents: 11000, ends_at: '2026-10-25T16:00:00Z', anti_sniping_applied: false },
      wallet: { total_balance_cents: 500000, committed_balance_cents: 11000, available_balance_cents: 489000 },
    } })
  })
  await page.goto(`/lots/${LOT}`)
  await page.getByLabel('Valor do lance').fill('110,00')
  await page.getByRole('button', { name: 'Dar lance' }).click()
  await expect.poll(() => posted).toBe(true)
  const latest = state(2, { bids: [
    { sequence: 2, bidder_alias: OTHER_ALIAS, amount_cents: 12000, placed_at: state().as_of },
    { sequence: 1, bidder_alias: OWN_ALIAS, amount_cents: 11000, placed_at: '2026-10-25T14:30:00Z' },
  ] })
  api.setBids(LOT, [...latest.bids].reverse())
  send(socket!, latest)
  await expect(page.locator('.bid-current')).toHaveText('R$\u00a0120,00')
  const end = await page.locator('.lot-page-when').textContent()
  release()
  await expect(page.getByText('Lance de R$', { exact: false }).first()).toBeVisible()
  await expect(page.getByLabel('Valor do lance')).toHaveValue('')
  await expect(page.locator('.bid-current')).toHaveText('R$\u00a0120,00')
  await expect(page.locator('.bid-minimum')).toHaveText('R$\u00a0130,00')
  await expect(page.locator('.lot-page-when')).toHaveText(end!)
  await expect(page.getByText('↑ Você foi superado')).toBeVisible()
})

test('WS invalidates private position while mine is delayed or fails; session changes reuse public socket', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  const initial = makeBids(1, 11000, [OWN_ALIAS])
  const api = await mockApi(page, { lots: LOTS, session: 'BIDDER', rooms: { [LOT]: { bids: initial } }, wallet: { total: 500000, committed: 0 } })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('✓ Você está ganhando')).toBeVisible()
  const held = api.hold(MINE)
  const incoming = state(2, { bids: [
    { sequence: 2, bidder_alias: OTHER_ALIAS, amount_cents: 12000, placed_at: state().as_of }, ...initial,
  ] })
  api.setBids(LOT, [...incoming.bids].reverse())
  const previous = api.count(MINE)
  send(sockets[0], incoming)
  await expect.poll(() => api.count(MINE)).toBeGreaterThan(previous)
  await expect(page.getByText('✓ Você está ganhando')).toHaveCount(0)
  await expect(page.getByText('↑ Você foi superado')).toHaveCount(0)
  // The read is still pending: hidden position is an update, not a failure.
  await expect(page.getByText('Não foi possível carregar sua participação.')).toHaveCount(0)
  held.fail()
  await expect(page.getByText('Não foi possível carregar sua participação.')).toBeVisible()
  await expect(page.getByText('✓ Você está ganhando')).toHaveCount(0)
  await page.getByRole('button', { name: 'Sair', exact: true }).click()
  await expect(page).toHaveURL(/\/$/)
  expect(sockets).toHaveLength(1)
  await expect(page.getByText('Seu pseudônimo neste lote:', { exact: false })).toHaveCount(0)
  await page.goto(`/lots/${lotId(2)}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  expect(sockets).toHaveLength(2)
})

test('WS during pending POST and remount keeps one submission and follows its result', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  const api = await mockApi(page, { lots: LOTS, session: 'BIDDER', wallet: { total: 500000, committed: 0 } })
  let release: () => void = () => undefined
  const gate = new Promise<void>((resolve) => { release = resolve })
  let posts = 0
  await page.route(`**/api/lots/${LOT}/bids`, async (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    posts += 1
    await gate
    await route.fulfill({ status: 201, json: {
      bid: { sequence: 1, bidder_alias: OWN_ALIAS, amount_cents: 11000, placed_at: state().as_of },
      lot: { current_bid_cents: 11000, ends_at: state().ends_at, anti_sniping_applied: false },
      wallet: { total_balance_cents: 500000, committed_balance_cents: 11000, available_balance_cents: 489000 },
    } })
  })
  await page.goto(`/lots/${LOT}`)
  await page.getByLabel('Valor do lance').fill('110,00')
  await page.getByRole('button', { name: 'Dar lance' }).click()
  await expect.poll(() => posts).toBe(1)
  send(sockets[0], state(1))
  await expect(page.getByRole('button', { name: 'Enviando lance…' })).toBeDisabled()
  await page.getByRole('link', { name: 'Vitrine', exact: true }).first().click()
  await page.goBack()
  await expect(page.getByLabel('Valor do lance')).toHaveValue('110,00')
  send(sockets[1], state(2), 'room_snapshot')
  await expect(page.locator('.bid-current')).toHaveText('R$\u00a0120,00')
  release()
  await expect(page.getByText('Lance de R$', { exact: false }).first()).toBeVisible()
  await expect(page.getByLabel('Valor do lance')).toHaveValue('')
  await expect(page.locator('.bid-current')).toHaveText('R$\u00a0120,00')
  expect(posts).toBe(1)
  expect(api.bidPosts).toHaveLength(0) // POST intercepted above, never through another path.
})

test('countdown zero and manual REST round cannot undo a concurrent WS extension', async ({ page }) => {
  await page.clock.install()
  let socket: WebSocketRoute
  await page.routeWebSocket('**/ws/lots/*', (value) => { socket = value })
  const api = await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  send(socket!, state(1, { ends_at: '2026-10-25T14:31:01.123456Z' }))
  await expect(page.getByRole('timer')).toHaveText('00:01')
  const held = api.hold(ROOM)
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect.poll(() => api.count(ROOM)).toBe(2)
  await page.clock.runFor(2000)
  expect(api.count(ROOM)).toBe(2)
  send(socket!, state(2, { ends_at: '2026-10-25T14:33:00.123456Z' }))
  held.release()
  await expect(page.locator('.bid-current')).toHaveText('R$\u00a0120,00')
  await expect(page.getByRole('timer')).toHaveText('02:00')
  await expect(page.getByText('Confirmando encerramento com o servidor…')).toHaveCount(0)
})

test('going offline closes the socket, marks the room stale, keeps the last state and never reconnects by itself', async ({ page, context }) => {
  const sockets: WebSocketRoute[] = []
  let closedByPage = 0
  await page.routeWebSocket('**/ws/lots/*', (socket) => {
    sockets.push(socket)
    socket.onClose(() => { closedByPage += 1 })
  })
  const api = await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  send(sockets[0], state(2), 'room_snapshot')
  await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
  await context.setOffline(true)
  await expect(page.getByText('Atualizações ao vivo indisponíveis.', { exact: false })).toBeVisible()
  await expect(page.getByText('Estado desatualizado', { exact: false })).toBeVisible()
  await expect.poll(() => closedByPage).toBe(1) // the current socket was closed, not just labelled
  await expect(page.getByText('Sala conectada', { exact: false })).toHaveCount(0)
  await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  await context.setOffline(false)
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect.poll(() => api.count(ROOM)).toBeGreaterThan(1)
  // A successful manual read says so; it does not claim the data is stale nor that the socket is back.
  await expect(page.getByText('Dados atualizados por leitura manual', { exact: false })).toBeVisible()
  await expect(page.getByText('Estado desatualizado', { exact: false })).toHaveCount(0)
  await expect(page.getByText('Sala conectada', { exact: false })).toHaveCount(0) // GET passing is not a socket
  expect(sockets).toHaveLength(1) // `online` and the refresh never reconnect
})

test('socket error or close, before or after connecting, never erases the room', async ({ page }) => {
  let attempts = 0
  await page.routeWebSocket('**/ws/lots/*', (socket) => { attempts += 1; void socket.close({ code: 1011 }) })
  await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('Atualizações ao vivo indisponíveis.', { exact: false })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  await expect(page.locator('.bid-current')).toBeVisible()
  expect(attempts).toBe(1)
})

test('failed manual refresh keeps the last valid state locally and a later one applies the newer room', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  const api = await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  send(sockets[0], state(2), 'room_snapshot')
  await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
  // Playwright routes answer before the network layer, so failures are injected as 503.
  const detail = api.hold(`GET /api/lots/${LOT}`)
  const held = api.hold(ROOM)
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect.poll(() => api.count(ROOM)).toBe(2)
  detail.fail()
  held.fail()
  await expect(page.getByText('Não foi possível atualizar a sala.', { exact: false })).toBeVisible()
  await expect(page.getByText('Não foi possível carregar o lote')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
  await expect(page.getByRole('button', { name: 'Atualizar sala' })).toBeEnabled()
  api.setBids(LOT, [...makeBids(3, 11000)])
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect(page.locator('.bid-current')).toHaveText('R$ 130,00')
  await expect(page.getByText('Não foi possível atualizar a sala.', { exact: false })).toHaveCount(0)
  expect(sockets).toHaveLength(1)
})

test('lot_cancelled is terminal and moves focus; a pending read and a later frame cannot bring the room back', async ({ page }) => {
  let socket: WebSocketRoute
  await page.routeWebSocket('**/ws/lots/*', (value) => { socket = value })
  const api = await mockApi(page, { lots: LOTS, session: 'BIDDER', wallet: { total: 500000, committed: 0 } })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  await page.getByLabel('Valor do lance').focus()
  const held = api.hold(ROOM)
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect.poll(() => api.count(ROOM)).toBe(2)
  socket!.send(JSON.stringify({ type: 'lot_cancelled', lot_id: LOT, cancelled_at: state().as_of }))
  send(socket!, state(5)) // a later frame with a higher count must not undo the terminal state
  const cancelled = page.getByRole('heading', { name: 'Este lote foi cancelado' })
  await expect(cancelled).toBeFocused()
  // The terminal event aborts the pending REST read (first line of defence); the pure
  // rule `shouldApplyRoom(..., cancelled)` is the second and is covered in node tests.
  held.release()
  await page.evaluate(() => new Promise<void>((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
  }))
  await expect(cancelled).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toHaveCount(0)
  await expect(page.locator('.bid-current')).toHaveCount(0)
})

test('an ambiguous POST superseded by a newer frame is resolved by the coalesced revalidation', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  const api = await mockApi(page, { lots: LOTS, session: 'BIDDER', wallet: { total: 500000, committed: 0 } })
  await page.route(`**/api/lots/${LOT}/bids`, async (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    await route.fulfill({ status: 503, json: { error: { code: 'internal_error' } } })
  })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  const held = api.hold(ROOM) // keeps the post-POST round in flight
  await page.getByLabel('Valor do lance').fill('110,00')
  await page.getByRole('button', { name: 'Dar lance' }).click()
  const pending = page.getByText('Não foi possível confirmar o lance nem atualizar todos os dados da sala.')
  await expect(pending).toBeVisible()
  const incoming = state(1)
  api.setBids(LOT, [...incoming.bids].reverse())
  send(sockets[0], incoming) // supersedes the round; the private read then completes
  const resolved = page.getByText('Não foi possível confirmar o lance. O estado abaixo é o atual do servidor')
  await expect(resolved).toBeVisible()
  await expect(pending).toHaveCount(0)
  held.release()
  expect(api.bidPosts).toHaveLength(0)
})

async function ambiguousPostThenFrame(page: Page, sockets: WebSocketRoute[]) {
  const api = await mockApi(page, { lots: LOTS, session: 'BIDDER', wallet: { total: 500000, committed: 0 } })
  await page.route(`**/api/lots/${LOT}/bids`, async (route) => {
    if (route.request().method() !== 'POST') return route.fallback()
    await route.fulfill({ status: 503, json: { error: { code: 'internal_error' } } })
  })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  const room = api.hold(ROOM) // keeps the post-POST round in flight
  await page.getByLabel('Valor do lance').fill('110,00')
  await page.getByRole('button', { name: 'Dar lance' }).click()
  const pending = page.getByText('Não foi possível confirmar o lance nem atualizar todos os dados da sala.')
  await expect(pending).toBeVisible()
  const mine = api.hold(MINE) // the revalidation started by the frame stays in flight
  const incoming = state(1)
  api.setBids(LOT, [...incoming.bids].reverse())
  const before = api.count(MINE)
  send(sockets[0], incoming) // supersedes the post-POST round
  await expect.poll(() => api.count(MINE)).toBeGreaterThan(before)
  return { api, room, mine, pending }
}
const RESOLVED = 'O estado abaixo é o atual do servidor'

test('a private read replaced by a manual refresh never resolves the ambiguous POST as complete', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  const { api, room, mine, pending } = await ambiguousPostThenFrame(page, sockets)
  const during = api.count(MINE)
  await page.getByRole('button', { name: 'Atualizar sala' }).click() // aborts the in-flight /mine
  await expect.poll(() => api.count(MINE)).toBeGreaterThan(during)
  room.release()
  mine.fail() // the replacing round's private read fails
  await expect(page.getByText('Não foi possível atualizar a sala.', { exact: false })).toBeVisible()
  await expect(page.getByText(RESOLVED, { exact: false })).toHaveCount(0)
  await expect(pending).toBeVisible()
})

test('a private revalidation that fails directly keeps the ambiguous POST partial', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  const { room, mine, pending } = await ambiguousPostThenFrame(page, sockets)
  mine.fail()
  await expect(page.getByText('Não foi possível carregar sua participação.')).toBeVisible()
  await expect(page.getByText(RESOLVED, { exact: false })).toHaveCount(0)
  await expect(pending).toBeVisible()
  room.release()
})

test('a replaced private read is decided by the round that replaced it', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  const { api, room, mine, pending } = await ambiguousPostThenFrame(page, sockets)
  const during = api.count(MINE)
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect.poll(() => api.count(MINE)).toBeGreaterThan(during)
  room.release()
  mine.release() // the replacing round succeeds
  await expect(page.getByText(RESOLVED, { exact: false })).toBeVisible()
  await expect(pending).toHaveCount(0)
})

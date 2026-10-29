// Browser tests with simulated public WebSockets and REST. Persistence is tested
// separately with PostgreSQL and the real ASGI transport.
import { expect, test, type Page, type WebSocketRoute } from '@playwright/test'
import { mockApi, makeLots, lotId, makeBids, OTHER_ALIAS, OWN_ALIAS, type MockBid } from './support/mockApi'
interface BidRoom {
  as_of: string; phase: 'live' | 'scheduled' | 'ended'; ends_at: string
  current_bid_cents: number | null; minimum_next_bid_cents: number | null
  bid_count: number; bids: MockBid[]
  settlement_status: 'pending' | 'settled'; settlement: { outcome: 'sold' | 'unsold'; winner_alias: string | null; final_amount_cents: number | null; bid_count: number; final_hash: string; settled_at: string } | null
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
    bid_count: count, bids: makeBids(count, 11000).reverse(),
    settlement_status: 'pending', settlement: null, ...extra,
  }
}
function send(socket: WebSocketRoute, room: BidRoom, type = 'bid_accepted', id = LOT) {
  socket.send(JSON.stringify({ type, lot_id: id, room }))
}

function initialize(socket: WebSocketRoute, id = LOT) {
  socket.onMessage((data) => {
    const payload = JSON.parse(String(data))
    if (payload.type === 'ping') socket.send(JSON.stringify({ type: 'pong', id: payload.id }))
  })
  send(socket, state(), 'room_snapshot', id)
}

for (const sold of [false, true]) {
  test(`T22/T23/T40 settled ${sold ? 'sold' : 'unsold'} snapshot stops heartbeat/reconnect before first ping`, async ({ page }) => {
    await page.clock.install()
    await page.clock.pauseAt(new Date())
    const sockets: WebSocketRoute[] = []
    const pings: unknown[] = []
    const terminal = state(sold ? 1 : 0, { phase: 'ended', settlement_status: 'settled', settlement: {
      outcome: sold ? 'sold' : 'unsold', winner_alias: sold ? OWN_ALIAS : null,
      final_amount_cents: sold ? 11000 : null, bid_count: sold ? 1 : 0,
      final_hash: (sold ? 'a' : '0').repeat(64), settled_at: '2026-10-25T17:00:00.123456Z',
    } })
    await page.routeWebSocket('**/ws/lots/*', (socket) => {
      sockets.push(socket)
      socket.onMessage((data) => pings.push(data))
      send(socket, terminal, 'room_snapshot')
    })
    const api = await mockApi(page, { lots: LOTS })
    // A delayed pending REST snapshot with a later clock cannot reopen terminal.
    const held = api.hold(ROOM)
    await page.goto(`/lots/${LOT}`)
    await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Dar lance', exact: true })).toHaveCount(0)
    held.release()
    await expect(page.getByRole('link', { name: 'Ver comprovante de arremate' })).toHaveCount(sold ? 1 : 0)
    await expect(page.locator('.bid-history li')).toHaveCount(sold ? 1 : 0)
    await expect(page.locator('.lot-page-status .lot-state')).toHaveText('Encerrado')
  await expect(page.locator('.room-phase-note')).toHaveText('Encerrado')
  await expect(page.getByText(/apurando resultado/)).toHaveCount(0)
  await expect(page.getByRole('timer')).toHaveCount(0)
    await page.evaluate(() => {
      window.dispatchEvent(new Event('offline'))
      window.dispatchEvent(new Event('online'))
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await page.clock.runFor(90_000)
    expect(pings).toHaveLength(0)
    expect(sockets).toHaveLength(1)
    expect(api.bidPosts).toHaveLength(0)
    await expect(page.getByText('Reconectando à sala…', { exact: true })).toHaveCount(0)
    await expect(page.getByText('Este lote foi cancelado', { exact: true })).toHaveCount(0)
  })
}

test('T21/T38 lot_closed keeps terminal despite later pending REST and failed final history read', async ({ page }) => {
  await page.clock.install()
  await page.clock.pauseAt(new Date())
  const sockets: WebSocketRoute[] = []
  const pings: unknown[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => {
    sockets.push(socket)
    socket.onMessage((data) => {
      const payload = JSON.parse(String(data))
      pings.push(payload)
      if (payload.type === 'ping') socket.send(JSON.stringify({ type: 'pong', id: payload.id }))
    })
    send(socket, state(), 'room_snapshot')
  })
  const api = await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  const atTerminal = pings.length
  let finalReads = 0
  await page.route(`**/api/lots/${LOT}/bids`, (route) => { finalReads++; return route.fulfill({ status: 503, json: { code: 'internal_error' } }) })
  const instant = '2026-10-25T17:00:00.123456Z'
  sockets[0].send(JSON.stringify({ type: 'lot_closed', lot_id: LOT, outcome: 'unsold',
    winner_alias: null, final_amount_cents: null, bid_count: 0, final_hash: '0'.repeat(64),
    settled_at: instant, as_of: instant }))
  await expect(page.locator('.lot-page-status .lot-state')).toHaveText('Encerrado')
  await expect(page.locator('.room-phase-note')).toHaveText('Encerrado')
  await expect(page.getByText(/apurando resultado/)).toHaveCount(0)
  await expect(page.getByRole('timer')).toHaveCount(0)
  await expect(page.getByText('Histórico possivelmente desatualizado.')).toBeVisible()
  expect(finalReads).toBe(1)
  await page.clock.runFor(90_000)
  expect(pings).toHaveLength(atTerminal)
  expect(sockets).toHaveLength(1)
  expect(api.bidPosts).toHaveLength(0)
  await expect(page.getByRole('heading', { name: 'Este lote foi cancelado' })).toHaveCount(0)
})

test('R6-AGG-01 terminal during retry survives the older pending GET released afterwards', async ({ page }) => {
  await page.clock.install()
  await page.clock.pauseAt(new Date())
  const pending = state(0, { as_of: '2026-10-25T17:00:00.000000Z', phase: 'ended', minimum_next_bid_cents: null })
  const sockets: WebSocketRoute[] = []
  const pings: unknown[] = []
  let closed = false
  await page.routeWebSocket('**/ws/lots/*', socket => {
    sockets.push(socket)
    socket.onClose(() => { closed = true })
    socket.onMessage(data => {
      const message = JSON.parse(String(data))
      pings.push(message)
      if (message.type === 'ping') socket.send(JSON.stringify({ type: 'pong', id: message.id }))
    })
    send(socket, pending, 'room_snapshot')
  })
  const api = await mockApi(page, { lots: LOTS })
  let detailReads = 0
  await page.route(`**/api/lots/${LOT}`, route => {
    detailReads++
    return detailReads === 1
      ? route.fulfill({ status: 503, json: { code: 'internal_error' } })
      : route.fallback()
  })
  let roomReads = 0
  let releaseOld = () => {}
  const oldRead = new Promise<void>(resolve => { releaseOld = resolve })
  let oldFulfilled = false
  await page.route(`**/api/lots/${LOT}/bids`, async route => {
    roomReads++
    if (roomReads === 2) {
      // This response was captured before settlement, even though delivered later.
      await oldRead
      await route.fulfill({ json: pending })
      oldFulfilled = true
      return
    }
    if (roomReads > 2) {
      // Terminal must stand on its own even if the final history read fails.
      await route.fulfill({ status: 503, json: { code: 'internal_error' } })
      return
    }
    await route.fulfill({ json: pending })
  })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByRole('heading', { name: 'Não foi possível carregar o lote' })).toBeVisible()
  await expect.poll(() => roomReads).toBe(1)
  const detail = api.hold(`GET /api/lots/${LOT}`)
  await page.getByRole('button', { name: 'Tentar novamente', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Carregando lote…' })).toBeVisible()
  await expect.poll(() => roomReads).toBe(2)
  const before = pings.length
  const instant = '2026-10-25T17:00:00.123456Z'
  sockets[0].send(JSON.stringify({ type: 'lot_closed', lot_id: LOT, outcome: 'unsold',
    winner_alias: null, final_amount_cents: null, bid_count: 0, final_hash: '0'.repeat(64),
    settled_at: instant, as_of: instant }))
  await expect.poll(() => closed).toBe(true)
  // Release the pre-terminal GET only after the transport accepted lot_closed.
  releaseOld()
  await expect.poll(() => oldFulfilled).toBe(true)
  detail.release()
  await expect(page.locator('.lot-page-status .lot-state')).toHaveText('Encerrado')
  await expect(page.locator('.room-phase-note')).toHaveText('Encerrado')
  await expect(page.getByText(/apurando resultado/)).toHaveCount(0)
  await expect(page.getByRole('timer')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Dar lance', exact: true })).toHaveCount(0)
  await page.clock.runFor(90_000)
  await expect(page.locator('.lot-page-status .lot-state')).toHaveText('Encerrado')
  await expect(page.getByText(/apurando resultado/)).toHaveCount(0)
  expect(roomReads).toBe(3)
  expect(pings).toHaveLength(before)
  expect(sockets).toHaveLength(1)
  expect(api.bidPosts).toHaveLength(0)
  expect(api.unexpected).toEqual([])
})

test('F44-01 sold terminal reconciles missed bids with final public GET', async ({ page }) => {
  await page.clock.install()
  await page.clock.pauseAt(new Date())
  const sockets: WebSocketRoute[] = []
  const messages: unknown[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => {
    sockets.push(socket)
    socket.onMessage((data) => messages.push(data))
    send(socket, state(1), 'room_snapshot')
  })
  await mockApi(page, { lots: LOTS, rooms: { [LOT]: { bids: makeBids(1, 11000) } } })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  const before = messages.length
  const instant = '2026-10-25T17:00:00.123456Z'
  const settlement = { outcome: 'sold' as const, winner_alias: OTHER_ALIAS, final_amount_cents: 13000,
    bid_count: 3, final_hash: 'a'.repeat(64), settled_at: instant }
  const final = state(3, { as_of: '2026-10-25T17:00:01Z', phase: 'ended', settlement_status: 'settled', settlement })
  let finalReads = 0
  await page.route(`**/api/lots/${LOT}/bids`, (route) => { finalReads++; return route.fulfill({ json: final }) })
  sockets[0].send(JSON.stringify({ type: 'lot_closed', lot_id: LOT, ...settlement, as_of: instant }))
  await expect(page.locator('.bid-history-count')).toHaveText('3 lances')
  await expect(page.locator('.bid-history li')).toHaveCount(3)
  for (const [index, bid] of final.bids.entries()) {
    const row = page.locator('.bid-history li').nth(index)
    await expect(row.locator('.bid-seq')).toHaveText(`#${bid.sequence}`)
    await expect(row.locator('.bid-alias')).toHaveText(bid.bidder_alias)
    await expect(row.locator('.bid-amount')).toHaveText(`R$\u00a0${bid.amount_cents / 100},00`)
  }
  await expect(page.locator('.bid-current')).toHaveText('R$\u00a0130,00')
  expect(finalReads).toBe(1)
  await page.clock.runFor(90_000)
  expect(messages).toHaveLength(before)
  expect(sockets).toHaveLength(1)
  await expect(page.locator('.lot-page-status .lot-state')).toHaveText('Encerrado')
  await expect(page.locator('.room-phase-note')).toHaveText('Encerrado')
  await expect(page.getByText(/apurando resultado/)).toHaveCount(0)
  await expect(page.getByRole('timer')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Dar lance', exact: true })).toHaveCount(0)
  await expect(page.getByText('Reconectando à sala…', { exact: true })).toHaveCount(0)
})

test('T22 offline during settlement reconnects once to a complete terminal snapshot without ping', async ({ page }) => {
  await page.clock.install()
  await page.clock.pauseAt(new Date())
  let settled = false
  const sockets: WebSocketRoute[] = []
  const pings: number[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => {
    const index = sockets.length
    sockets.push(socket)
    pings.push(0)
    socket.onMessage((data) => {
      const message = JSON.parse(String(data))
      if (message.type === 'ping') {
        pings[index]++
        socket.send(JSON.stringify({ type: 'pong', id: message.id }))
      }
    })
    send(socket, settled ? state(0, { phase: 'ended', settlement_status: 'settled', settlement: {
      outcome: 'unsold', winner_alias: null, final_amount_cents: null, bid_count: 0,
      final_hash: '0'.repeat(64), settled_at: '2026-10-25T17:00:00Z',
    } }) : state(), 'room_snapshot')
  })
  await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  await page.evaluate(() => window.dispatchEvent(new Event('offline')))
  await expect(page.getByText('Sem conexão com a rede', { exact: true })).toBeVisible()
  settled = true
  await page.evaluate(() => {
    window.dispatchEvent(new Event('online'))
    window.dispatchEvent(new Event('online'))
  })
  await expect(page.locator('.lot-page-status .lot-state')).toHaveText('Encerrado')
  await expect(page.locator('.room-phase-note')).toHaveText('Encerrado')
  await expect(page.getByText(/apurando resultado/)).toHaveCount(0)
  await expect(page.getByRole('timer')).toHaveCount(0)
  await page.clock.runFor(90_000)
  expect(sockets).toHaveLength(2)
  expect(pings[1]).toBe(0)
})

test('snapshots replace state, preserve input/focus, coalesce duplicates and recover disconnect', async ({ page }) => {
  await page.clock.install()
  await page.clock.pauseAt(new Date())
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket); initialize(socket) })
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
  await expect(page.getByText('Reconectando à sala…', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect.poll(() => api.count(ROOM)).toBeGreaterThan(1)
  // Fresh by manual reading, live updates still out; the socket is not "connected" again.
  await expect(page.getByText('Dados atualizados por leitura manual', { exact: false })).toBeVisible()
  await expect(page.getByText('Estado desatualizado', { exact: false })).toHaveCount(0)
  await expect(page.getByText('Sala conectada', { exact: false })).toHaveCount(0)
  expect(sockets).toHaveLength(1) // paused retry never races the manual refresh
  expect(api.bidPosts).toHaveLength(0)
})

test('old REST cannot replace WS and terminal cancellation at zero cannot be reversed', async ({ page }) => {
  let socket: WebSocketRoute
  await page.routeWebSocket('**/ws/lots/*', (value) => { socket = value; initialize(value, value.url().split('/').at(-1)!) })
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
  await page.routeWebSocket('**/ws/lots/*', (value) => { socket = value; initialize(value, value.url().split('/').at(-1)!) })
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
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket); initialize(socket); send(socket, state(1, { bids: initial }), 'room_snapshot') })
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
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket); initialize(socket) })
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
  await page.routeWebSocket('**/ws/lots/*', (value) => { socket = value; initialize(value, value.url().split('/').at(-1)!) })
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
  send(socket!, state(2, { ends_at: '2026-10-25T14:33:01.123456Z' }))
  held.release()
  await expect(page.locator('.bid-current')).toHaveText('R$\u00a0120,00')
  await expect(page.getByRole('timer')).toHaveText('02:01')
  await expect(page.getByText('Confirmando encerramento com o servidor…')).toHaveCount(0)
})

test('offline closes current generation; online immediately recovers through a new snapshot', async ({ page, context }) => {
  const sockets: WebSocketRoute[] = []
  let closedByPage = 0
  await page.routeWebSocket('**/ws/lots/*', (socket) => {
    sockets.push(socket)
    socket.onClose(() => { closedByPage++ })
    initialize(socket)
  })
  const api = await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  send(sockets[0], state(2), 'room_snapshot')
  await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
  await context.setOffline(true)
  await expect(page.getByText('Sem conexão com a rede')).toBeVisible()
  await expect.poll(() => closedByPage).toBe(1)
  await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
  await context.setOffline(false)
  await expect.poll(() => sockets.length).toBe(2)
  send(sockets[1], state(3), 'room_snapshot')
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  await expect(page.locator('.bid-current')).toHaveText('R$ 130,00')
  expect(api.bidPosts).toHaveLength(0)
})

test('socket error or close, before or after connecting, never erases the room', async ({ page }) => {
  await page.clock.install()
  await page.clock.pauseAt(new Date())
  let attempts = 0
  await page.routeWebSocket('**/ws/lots/*', (socket) => { attempts += 1; void socket.close({ code: 1011 }) })
  await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('Reconectando à sala…', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  await expect(page.locator('.bid-current')).toBeVisible()
  expect(attempts).toBe(1)
  await page.clock.runFor(1_000)
  await expect.poll(() => attempts).toBe(2)
  await expect(page.locator('.bid-current')).toBeVisible()
})

test('failed manual refresh keeps the last valid state locally and a later one applies the newer room', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket); initialize(socket) })
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

for (const privateFailure of [false, true]) {
  for (const recoveredCount of [2, 3]) {
    test(`reconnect snapshot clears public stale after failed manual refresh: count=${recoveredCount}, privateFailure=${privateFailure}`, async ({ page }) => {
      await page.clock.install()
      await page.clock.pauseAt(new Date())
      const sockets: WebSocketRoute[] = []
      await page.routeWebSocket('**/ws/lots/*', (socket) => {
        sockets.push(socket)
        socket.onMessage((data) => {
          const payload = JSON.parse(String(data))
          if (payload.type === 'ping') socket.send(JSON.stringify({ type: 'pong', id: payload.id }))
        })
        if (sockets.length === 1) send(socket, state(2), 'room_snapshot')
      })
      const api = await mockApi(page, {
        lots: LOTS, session: privateFailure ? 'BIDDER' : undefined,
        rooms: { [LOT]: { bids: makeBids(2, 11000) } },
      })
      if (privateFailure) {
        for (const path of [`/api/lots/${LOT}/bids/mine`, '/api/wallet']) {
          await page.route(`**${path}`, (route) => route.fulfill({ status: 503, json: { status: 503, code: 'internal_error', message: 'Indisponível' } }))
        }
      }
      await page.goto(`/lots/${LOT}`)
      const connected = page.getByText('Sala conectada', { exact: false })
      const staleRoom = page.getByText('Não foi possível atualizar a sala.', { exact: false })
      const staleHistory = page.getByText('Histórico possivelmente desatualizado.')
      await expect(connected).toBeVisible()
      await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
      await expect(page.locator('.bid-history-list li')).toHaveCount(2)
      await sockets[0].close({ code: 1011 })
      await expect(page.getByText('Reconectando à sala…')).toBeVisible()
      const reads = api.count(ROOM)
      const held = api.hold(ROOM)
      await page.getByRole('button', { name: 'Atualizar sala' }).click()
      await expect.poll(() => api.count(ROOM)).toBe(reads + 1)
      held.fail()
      await expect(staleRoom).toBeVisible()
      await expect(staleHistory).toBeVisible()
      await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
      await expect(page.locator('.bid-history-list li')).toHaveCount(2)
      await page.clock.runFor(1_000)
      await expect.poll(() => sockets.length).toBe(2)
      await expect(connected).toHaveCount(0) // open alone cannot clear the warnings
      await expect(staleRoom).toBeVisible()
      await expect(staleHistory).toBeVisible()
      send(sockets[1], state(recoveredCount), 'room_snapshot')
      await expect(connected).toBeVisible()
      await expect(staleRoom).toHaveCount(0)
      await expect(staleHistory).toHaveCount(0)
      await expect(page.locator('.bid-current')).toHaveText(recoveredCount === 2 ? 'R$ 120,00' : 'R$ 130,00')
      await expect(page.locator('.bid-history-list li')).toHaveCount(recoveredCount)
      if (privateFailure) {
        await expect(page.getByText('Não foi possível carregar sua participação.')).toBeVisible()
        await expect(page.getByText('Não foi possível carregar a carteira.')).toBeVisible()
      }
      expect(api.bidPosts).toHaveLength(0)
    })
  }
}

// A public snapshot must never certify previously loaded private data after failure.
for (const failure of ['mine', 'wallet', 'both'] as const) {
  test(`retained private data stays stale through identical recovery snapshot: ${failure}`, async ({ page }) => {
    await page.clock.install()
    await page.clock.pauseAt(new Date())
    const initial = makeBids(1, 11000, [OWN_ALIAS])
    const publicState = state(1, { bids: initial })
    const sockets: WebSocketRoute[] = []
    await page.routeWebSocket('**/ws/lots/*', (socket) => {
      sockets.push(socket)
      socket.onMessage((data) => socket.send(JSON.stringify({ type: 'pong', id: JSON.parse(String(data)).id })))
      if (sockets.length === 1) send(socket, publicState, 'room_snapshot')
    })
    const api = await mockApi(page, {
      lots: LOTS, session: 'BIDDER', rooms: { [LOT]: { bids: initial } },
      wallet: { total: 500000, committed: 11000 },
    })
    await page.goto(`/lots/${LOT}`)
    const winning = page.getByText('✓ Você está ganhando')
    const balance = page.locator('.bid-wallet strong')
    const mineError = page.getByText('Não foi possível carregar sua participação.')
    const walletError = page.getByText('Não foi possível carregar a carteira.')
    const publicError = page.getByText('Não foi possível atualizar a sala.', { exact: false })
    const historyError = page.getByText('Histórico possivelmente desatualizado.')
    await expect(winning).toBeVisible()
    await expect(balance).toHaveText('R$ 4.890,00')
    await sockets[0].close({ code: 1011 })
    await expect(page.getByText('Reconectando à sala…')).toBeVisible()
    const roomRead = api.hold(ROOM)
    const mineRead = api.hold(MINE)
    const walletRead = api.hold('GET /api/wallet')
    const previous = api.count(MINE)
    await page.getByRole('button', { name: 'Atualizar sala' }).click()
    await expect.poll(() => api.count(MINE)).toBe(previous + 1)
    await expect(winning).toHaveCount(0) // M1: pending private data is not current.
    await expect(mineError).toHaveCount(0)
    if (failure === 'wallet') roomRead.release()
    else roomRead.fail()
    if (failure === 'wallet') mineRead.release()
    else mineRead.fail()
    if (failure === 'mine') walletRead.release()
    else walletRead.fail()
    await expect(publicError).toHaveCount(failure === 'wallet' ? 0 : 1)
    await expect(historyError).toHaveCount(failure === 'wallet' ? 0 : 1)
    await expect(mineError).toHaveCount(failure === 'wallet' ? 0 : 1)
    await expect(walletError).toHaveCount(failure === 'mine' ? 0 : 1)
    await expect(balance).toHaveText('R$ 4.890,00')
    await page.clock.runFor(1_000)
    await expect.poll(() => sockets.length).toBe(2)
    const privateReads = api.count(MINE)
    send(sockets[1], publicState, 'room_snapshot')
    await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
    await expect(publicError).toHaveCount(0)
    await expect(historyError).toHaveCount(0)
    await expect(mineError).toHaveCount(failure === 'wallet' ? 0 : 1)
    await expect(walletError).toHaveCount(failure === 'mine' ? 0 : 1)
    await expect(winning).toHaveCount(failure === 'wallet' ? 1 : 0)
    await expect(page.getByText('↑ Você foi superado')).toHaveCount(0)
    await expect(balance).toHaveText('R$ 4.890,00')
    expect(api.count(MINE)).toBe(privateReads) // identical snapshot does no private validation
    if (failure === 'both') {
      // Recover each resource independently; a successful sibling cannot clear its error.
      for (const failingResource of ['wallet', 'mine']) {
        const held = api.hold(failingResource === 'mine' ? MINE : 'GET /api/wallet')
        const key = failingResource === 'mine' ? MINE : 'GET /api/wallet'
        const before = api.count(key)
        await page.getByRole('button', { name: 'Atualizar sala' }).click()
        await expect.poll(() => api.count(key)).toBe(before + 1)
        if (failingResource === 'wallet') await expect(mineError).toBeVisible() // start does not clear stale
        held.fail()
        await expect(page.getByRole('button', { name: 'Atualizar sala', exact: true })).toHaveAttribute('aria-busy', 'false')
        await expect(mineError).toHaveCount(failingResource === 'mine' ? 1 : 0)
        await expect(walletError).toHaveCount(failingResource === 'wallet' ? 1 : 0)
      }
    }
    // A genuine current private response updates data and clears only its own error.
    const newer = makeBids(2, 11000, [OWN_ALIAS, OTHER_ALIAS])
    api.setBids(LOT, newer)
    await page.route('**/api/wallet', (route) => route.fulfill({ json: {
      total_balance_cents: 600000, committed_balance_cents: 0, available_balance_cents: 600000,
    } }))
    await page.getByRole('button', { name: 'Atualizar sala' }).click()
    await expect(page.getByText('↑ Você foi superado')).toBeVisible()
    await expect(balance).toHaveText('R$ 6.000,00')
    await expect(mineError).toHaveCount(0)
    await expect(walletError).toHaveCount(0)
    expect(api.bidPosts).toHaveLength(0)
  })
}

test('superseded private HTTP 200 delivered after current failure cannot clear stale', async ({ page }) => {
  // Only A ignores transport cancellation. Production AbortSignals and generation
  // checks remain intact, and real routed HTTP responses still pass both API parsers.
  await page.addInitScript(() => {
    const nativeFetch = window.fetch.bind(window)
    const probe = { armed: false, started: [] as string[], consumed: [] as Array<{
      path: string; status: number; aborted: boolean; body: unknown
    }> }
    Object.assign(window, { supersededPrivateProbe: probe })
    window.fetch = async (input, options) => {
      const path = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url, location.origin).pathname
      const isA = probe.armed && (path.endsWith('/bids/mine') || path === '/api/wallet')
      if (!isA) return nativeFetch(input, options)
      const applicationSignal = options?.signal
      if (!applicationSignal) throw new Error('A must carry its production AbortSignal')
      probe.started.push(path)
      const response = await nativeFetch(input, { ...options, signal: undefined })
      const readJson = response.json.bind(response)
      response.json = async () => {
        const body: unknown = await readJson()
        probe.consumed.push({ path, status: response.status, aborted: applicationSignal.aborted, body })
        return body
      }
      return response
    }
  })
  const initial = makeBids(1, 11000, [OWN_ALIAS])
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => {
    sockets.push(socket); initialize(socket)
    send(socket, state(1, { bids: initial }), 'room_snapshot')
  })
  const api = await mockApi(page, {
    lots: LOTS, session: 'BIDDER', rooms: { [LOT]: { bids: initial } },
    wallet: { total: 500000, committed: 11000 },
  })
  await page.goto(`/lots/${LOT}`)
  const winning = page.getByText('✓ Você está ganhando')
  const outbid = page.getByText('↑ Você foi superado')
  const balance = page.locator('.bid-wallet strong')
  const mineError = page.getByText('Não foi possível carregar sua participação.')
  const walletError = page.getByText('Não foi possível carregar a carteira.')
  await expect(winning).toBeVisible()
  await expect(balance).toHaveText('R$ 4.890,00')

  let phase: 'A' | 'B' | 'C' = 'A'
  let receivedA = 0
  let releaseA: () => void = () => undefined
  const gateA = new Promise<void>((resolve) => { releaseA = resolve })
  const oldMine = { bidder_alias: OWN_ALIAS, my_bid_count: 1, last_bid_cents: 11000 }
  const oldWallet = { total_balance_cents: 100000, committed_balance_cents: 11000, available_balance_cents: 89000 }
  const currentMine = { bidder_alias: OWN_ALIAS, my_bid_count: 1, last_bid_cents: 11000 }
  const currentWallet = { total_balance_cents: 600000, committed_balance_cents: 0, available_balance_cents: 600000 }
  for (const resource of ['mine', 'wallet'] as const) {
    const path = resource === 'mine' ? `/api/lots/${LOT}/bids/mine` : '/api/wallet'
    await page.route(`**${path}`, async (route) => {
      const requestPhase = phase
      if (requestPhase === 'A') {
        receivedA++
        await gateA
        return route.fulfill({ status: 200, json: resource === 'mine' ? oldMine : oldWallet })
      }
      if (requestPhase === 'B') return route.fulfill({ status: 503, json: { status: 503, code: 'internal_error' } })
      return route.fulfill({ status: 200, json: resource === 'mine' ? currentMine : currentWallet })
    })
  }
  await page.evaluate(() => {
    const probe = (window as unknown as { supersededPrivateProbe: { armed: boolean } }).supersededPrivateProbe
    probe.armed = true
  })
  const incoming = state(2, { bids: makeBids(2, 11000, [OWN_ALIAS, OTHER_ALIAS]).reverse() })
  api.setBids(LOT, [...incoming.bids].reverse())
  send(sockets[0], incoming) // A: required private revalidation remains pending.
  await expect.poll(() => page.evaluate(() =>
    (window as unknown as { supersededPrivateProbe: { started: string[] } }).supersededPrivateProbe.started.length,
  )).toBe(2)
  await expect.poll(() => receivedA).toBe(2)
  await expect(winning).toHaveCount(0)
  await page.evaluate(() => {
    (window as unknown as { supersededPrivateProbe: { armed: boolean } }).supersededPrivateProbe.armed = false
  })
  phase = 'B'
  await page.getByRole('button', { name: 'Atualizar sala' }).click() // logically supersedes A
  await expect(mineError).toBeVisible()
  await expect(walletError).toBeVisible()
  await expect(page.getByRole('button', { name: 'Atualizar sala', exact: true })).toHaveAttribute('aria-busy', 'false')
  await expect(balance).toHaveText('R$ 4.890,00')
  // Only now can the two old successful responses reach the application.
  releaseA()
  await expect.poll(() => page.evaluate(() =>
    (window as unknown as { supersededPrivateProbe: { consumed: unknown[] } }).supersededPrivateProbe.consumed.length,
  )).toBe(2)
  const consumed = await page.evaluate(() =>
    (window as unknown as { supersededPrivateProbe: { consumed: unknown[] } }).supersededPrivateProbe.consumed,
  )
  expect(consumed).toEqual(expect.arrayContaining([
    { path: `/api/lots/${LOT}/bids/mine`, status: 200, aborted: true, body: oldMine },
    { path: '/api/wallet', status: 200, aborted: true, body: oldWallet },
  ]))
  // Both JSON reads have resolved. Drain the app's promise continuations and React
  // commit before asserting; a public frame would not establish this ordering.
  await page.evaluate(() => new Promise<void>((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
  }))
  await expect(mineError).toBeVisible()
  await expect(walletError).toBeVisible()
  await expect(winning).toHaveCount(0)
  await expect(outbid).toHaveCount(0)
  await expect(balance).toHaveText('R$ 4.890,00') // A's R$ 890,00 must not replace it.
  await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
  await expect(page.locator('.bid-history-list li')).toHaveCount(2)

  phase = 'C'
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect(outbid).toBeVisible()
  await expect(balance).toHaveText('R$ 6.000,00')
  await expect(mineError).toHaveCount(0)
  await expect(walletError).toHaveCount(0)
  expect(api.bidPosts).toHaveLength(0)
})

test('a late failed public refresh cannot restore stale after a same-state snapshot', async ({ page }) => {
  await page.clock.install()
  await page.clock.pauseAt(new Date())
  let socket: WebSocketRoute
  await page.routeWebSocket('**/ws/lots/*', (value) => { socket = value; initialize(value) })
  const api = await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  const reads = api.count(ROOM)
  const held = api.hold(ROOM)
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect.poll(() => api.count(ROOM)).toBe(reads + 1)
  // Same public values, later as_of: no round cancellation or private reread.
  const clockBefore = await page.locator('.as-of').textContent()
  send(socket!, state(0, { as_of: '2026-10-25T14:35:00Z' }), 'room_snapshot')
  await expect(page.locator('.as-of')).not.toHaveText(clockBefore!)
  held.fail()
  await expect(page.getByRole('button', { name: 'Atualizar sala', exact: true })).toHaveAttribute('aria-busy', 'false')
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  await expect(page.getByText('Não foi possível atualizar a sala.', { exact: false })).toHaveCount(0)
  await expect(page.getByText('Histórico possivelmente desatualizado.')).toHaveCount(0)
  await expect(page.getByText('Nenhum lance ainda.').last()).toBeVisible()
})

test('lot_cancelled is terminal and moves focus; a pending read and a later frame cannot bring the room back', async ({ page }) => {
  let socket: WebSocketRoute
  await page.routeWebSocket('**/ws/lots/*', (value) => { socket = value; initialize(value, value.url().split('/').at(-1)!) })
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
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket); initialize(socket) })
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
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket); initialize(socket) })
  const { api, room, mine, pending } = await ambiguousPostThenFrame(page, sockets)
  const during = api.count(MINE)
  await page.getByRole('button', { name: 'Atualizar sala' }).click() // aborts the in-flight /mine
  await expect.poll(() => api.count(MINE)).toBeGreaterThan(during)
  room.release()
  mine.fail() // the replacing round's private read fails
  await expect(page.getByText('Não foi possível carregar sua participação.')).toBeVisible()
  await expect(page.getByText('Não foi possível atualizar a sala.', { exact: false })).toHaveCount(0)
  await expect(page.getByText('Histórico possivelmente desatualizado.')).toHaveCount(0)
  await expect(page.getByText(RESOLVED, { exact: false })).toHaveCount(0)
  await expect(pending).toBeVisible()
})

test('a private revalidation that fails directly keeps the ambiguous POST partial', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket); initialize(socket) })
  const { room, mine, pending } = await ambiguousPostThenFrame(page, sockets)
  mine.fail()
  await expect(page.getByText('Não foi possível carregar sua participação.')).toBeVisible()
  await expect(page.getByText(RESOLVED, { exact: false })).toHaveCount(0)
  await expect(pending).toBeVisible()
  room.release()
})

test('a replaced private read is decided by the round that replaced it', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket); initialize(socket) })
  const { api, room, mine, pending } = await ambiguousPostThenFrame(page, sockets)
  const during = api.count(MINE)
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect.poll(() => api.count(MINE)).toBeGreaterThan(during)
  room.release()
  mine.release() // the replacing round succeeds
  await expect(page.getByText(RESOLVED, { exact: false })).toBeVisible()
  await expect(pending).toHaveCount(0)
})

test('open awaits snapshot, lost pong reconnects automatically, and snapshot alone never resends commands', async ({ page }) => {
  await page.clock.install()
  await page.clock.pauseAt(new Date())
  const sockets: WebSocketRoute[] = []
  const pings: Array<{ socket: number; id: number }> = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => {
    const index = sockets.length
    sockets.push(socket)
    socket.onMessage((data) => { pings.push({ socket: index, id: JSON.parse(String(data)).id }) })
  })
  const api = await mockApi(page, { lots: LOTS, session: 'BIDDER' })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('Conectando à sala…')).toBeVisible()
  await expect(page.getByText('Sala conectada', { exact: false })).toHaveCount(0)
  send(sockets[0], state(1)) // bid event before first snapshot is ignored
  await expect(page.getByText('Conectando à sala…')).toBeVisible()
  send(sockets[0], state(2), 'room_snapshot')
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  await expect.poll(() => pings.length).toBe(1)
  await page.getByLabel('Valor do lance').fill('222,00')
  await page.clock.runFor(10_000)
  await expect(page.getByText('Reconectando à sala…')).toBeVisible()
  await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
  await page.clock.runFor(1_000)
  await expect.poll(() => sockets.length).toBe(2)
  await expect(page.getByText('Sala conectada', { exact: false })).toHaveCount(0)
  send(sockets[1], state(3), 'room_snapshot')
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  await expect(page.locator('.bid-current')).toHaveText('R$ 130,00')
  await expect(page.getByLabel('Valor do lance')).toHaveValue('222,00')
  await expect(page.getByLabel('Valor do lance')).toBeFocused()
  expect(api.bidPosts).toHaveLength(0)
})

test('one diagnostic per recovery episode; 503 retries WS while confirmed 404 is terminal', async ({ page }) => {
  await page.clock.install()
  await page.clock.pauseAt(new Date())
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  const api = await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  let diagnostics = 0
  await page.route(`**/api/lots/${LOT}/bids`, async (route) => {
    diagnostics++
    await route.fulfill({ status: 503, json: { error: { code: 'internal_error' } } })
  })
  await sockets[0].close({ code: 1008 })
  await expect.poll(() => diagnostics).toBe(1)
  await page.clock.runFor(1_000)
  await expect.poll(() => sockets.length).toBe(2)
  await sockets[1].close({ code: 1008 })
  await page.clock.runFor(2_000)
  await expect.poll(() => sockets.length).toBe(3)
  expect(diagnostics).toBe(1)
  send(sockets[2], state(), 'room_snapshot')
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  await page.route(`**/api/lots/${LOT}/bids`, async (route) => {
    await route.fulfill({ status: 404, json: { error: { code: 'lot_not_found' } } })
  })
  await sockets[2].close({ code: 1011 })
  await expect(page.getByText('Reconectando à sala…')).toBeVisible()
  await page.clock.runFor(4_000)
  await expect.poll(() => sockets.length).toBe(4)
  await sockets[3].close({ code: 1008 })
  await expect(page.getByRole('heading', { name: 'Lote indisponível ou não encontrado' })).toBeVisible()
  await page.clock.runFor(120_000)
  expect(sockets).toHaveLength(4)
  expect(api.bidPosts).toHaveLength(0)
})

for (const width of [320, 375, 1280]) {
  test(`recovery status and keyboard refresh remain accessible at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 })
    const sockets: WebSocketRoute[] = []
    await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket); initialize(socket) })
    const api = await mockApi(page, { lots: LOTS })
    await page.goto(`/lots/${LOT}`)
    await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
    await page.evaluate(() => window.dispatchEvent(new Event('offline')))
    // Synthetic event retires the socket. navigator remains online, so visible
    // explicitly reevaluates health; this test claims UI behavior only.
    await expect(page.getByText('Sem conexão com a rede')).toBeVisible()
    const button = page.getByRole('button', { name: 'Atualizar sala' })
    await button.focus()
    await page.keyboard.press('Enter')
    await expect.poll(() => api.count(ROOM)).toBeGreaterThan(1)
    await expect(button).toBeFocused()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await expect(page.locator('.room-refresh [role="status"]')).toHaveText('Sem conexão com a rede')
  })
}

test('opening timeout and navigation invalidate pending retries across lots and back remount', async ({ page }) => {
  await page.clock.install()
  await page.clock.pauseAt(new Date())
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByText('Conectando à sala…')).toBeVisible()
  await page.clock.runFor(29_999)
  await expect(page.getByText('Conectando à sala…')).toBeVisible()
  await page.clock.runFor(1)
  await expect(page.getByText('Reconectando à sala…')).toBeVisible()
  // Navigate with History API so the previous instance's retry stays in this JS realm.
  await page.evaluate((url) => { history.pushState(null, '', url); dispatchEvent(new PopStateEvent('popstate')) }, `/lots/${lotId(2)}`)
  await expect.poll(() => sockets.length).toBe(2)
  send(sockets[1], state(2), 'room_snapshot', lotId(2))
  await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
  sockets[1].onMessage((data) => { sockets[1].send(JSON.stringify({ type: 'pong', id: JSON.parse(String(data)).id })) })
  await page.clock.runFor(2_000)
  expect(sockets).toHaveLength(2)
  await page.goBack()
  await expect.poll(() => sockets.length).toBe(3)
  send(sockets[2], state(3), 'room_snapshot')
  await expect(page.locator('.bid-current')).toHaveText('R$ 130,00')
})

test('manual room newer than reconnect snapshot is retained while transport becomes connected', async ({ page }) => {
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  await mockApi(page, { lots: LOTS, rooms: { [LOT]: { bids: makeBids(3, 11000) } } })
  await page.goto(`/lots/${LOT}`)
  await expect(page.locator('.bid-current')).toHaveText('R$ 130,00')
  await expect(page.getByText('Conectando à sala…')).toBeVisible()
  send(sockets[0], state(1), 'room_snapshot')
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  await expect(page.locator('.bid-current')).toHaveText('R$ 130,00')
})

test('snapshot invalidates an old coalesced diagnostic 404 without ending the recovered room', async ({ page }) => {
  await page.clock.install()
  await page.clock.pauseAt(new Date())
  const sockets: WebSocketRoute[] = []
  await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket) })
  await mockApi(page, { lots: LOTS })
  await page.goto(`/lots/${LOT}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
  let release: () => void = () => undefined
  const gate = new Promise<void>((resolve) => { release = resolve })
  let reads = 0
  await page.route(`**/api/lots/${LOT}/bids`, async (route) => {
    reads++
    await gate
    await route.fulfill({ status: 404, json: { error: { code: 'lot_not_found' } } })
  })
  await page.getByRole('button', { name: 'Atualizar sala' }).click()
  await expect.poll(() => reads).toBe(1)
  await sockets[0].close({ code: 1008 })
  await expect(page.getByText('Reconectando à sala…')).toBeVisible()
  expect(reads).toBe(1)
  await page.clock.runFor(1_000)
  await expect.poll(() => sockets.length).toBe(2)
  send(sockets[1], state(), 'room_snapshot')
  await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
  release()
  await expect(page.getByRole('button', { name: 'Atualizar sala' })).toBeVisible()
  await page.clock.runFor(16)
  await expect(page.getByRole('heading', { name: 'Lote indisponível ou não encontrado' })).toHaveCount(0)
})

for (const failure of ['lot_cancelled', 'not_found'] as const) {
  test(`POST ${failure} during reconnect confirms terminal and prevents late recovery`, async ({ page }) => {
    await page.clock.install()
    await page.clock.pauseAt(new Date())
    const sockets: WebSocketRoute[] = []
    await page.routeWebSocket('**/ws/lots/*', (socket) => { sockets.push(socket); initialize(socket) })
    const api = await mockApi(page, { lots: LOTS, session: 'BIDDER', wallet: { total: 500000, committed: 0 } })
    let posts = 0
    let release: () => void = () => undefined
    const gate = new Promise<void>((resolve) => { release = resolve })
    await page.route(`**/api/lots/${LOT}/bids`, async (route) => {
      if (route.request().method() !== 'POST') return route.fallback()
      posts++
      await gate
      const status = failure === 'lot_cancelled' ? 422 : 404
      await route.fulfill({ status,
        json: { status, code: failure === 'not_found' ? 'lot_not_found' : failure, message: 'MENSAGEM DO SERVIDOR' } })
    })
    await page.goto(`/lots/${LOT}`)
    await expect(page.getByText('Sala conectada', { exact: false })).toBeVisible()
    await page.getByLabel('Valor do lance').fill('110,00')
    await page.getByRole('button', { name: 'Dar lance' }).click()
    await expect.poll(() => posts).toBe(1)
    await sockets[0].close({ code: 1011 })
    await expect(page.getByText('Reconectando à sala…')).toBeVisible()
    const reads = api.count(ROOM)
    release()
    const heading = page.getByRole('heading', { name: failure === 'lot_cancelled'
      ? 'Este lote foi cancelado' : 'Lote indisponível ou não encontrado' })
    await expect(heading).toBeVisible()
    if (failure === 'lot_cancelled') await expect(heading).toBeFocused()
    await page.evaluate(() => window.dispatchEvent(new Event('online')))
    await page.clock.runFor(120_000)
    await expect(heading).toBeVisible()
    expect(sockets).toHaveLength(1)
    expect(posts).toBe(1)
    expect(api.count(ROOM)).toBe(reads)
    await expect(page.getByRole('heading', { name: 'Sala do lote' })).toHaveCount(0)
  })
}

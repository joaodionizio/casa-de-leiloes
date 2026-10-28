import assert from 'node:assert/strict'
import test from 'node:test'
import { createLotConnection, retryDelay, type RoomSocket } from './lotConnection.ts'
import type { RoomMessage, ConnectionState } from './lotRoomSocket.ts'
const LOT = '00000000-0000-4000-8000-000000000001'
const snapshot: RoomMessage = { type: 'room_snapshot', lot_id: LOT, room: {
  as_of: '2026-10-27T12:00:00Z', phase: 'live', ends_at: '2026-10-27T13:00:00Z',
  current_bid_cents: null, minimum_next_bid_cents: 10000, bid_count: 0, bids: [], settlement_status: 'pending', settlement: null,
} }
function harness(initialOnline = true, constructorFails = false) {
  let now = 0
  let network = initialOnline
  const sockets: Array<RoomSocket & { sent: string[]; closes: number }> = []
  const timers: Array<{ at: number; callback: () => void; cancelled: boolean }> = []
  const statuses: ConnectionState[] = []
  const messages: RoomMessage[] = []
  let diagnoses = 0
  let recoveries = 0
  const machine = createLotConnection(LOT, {
    now: () => now, online: () => network, random: () => 0,
    schedule: (callback, delay) => {
      const timer = { at: now + delay, callback, cancelled: false }
      timers.push(timer)
      return () => { timer.cancelled = true }
    },
    socket: () => {
      if (constructorFails) throw new Error('constructor')
      const socket: RoomSocket & { sent: string[]; closes: number } = {
        readyState: 1, onopen: null, onmessage: null, onerror: null, onclose: null,
        sent: [], closes: 0,
        send(data) { this.sent.push(data) }, close() { this.closes++ },
      }
      sockets.push(socket)
      return socket
    },
    status: (state) => statuses.push(state), message: (event) => messages.push(event),
    diagnose: () => { diagnoses++ }, recovered: () => { recoveries++ },
  })
  const frame = (value: unknown, socket = sockets.at(-1)!) => {
    socket.onmessage?.call(socket as unknown as WebSocket, { data: JSON.stringify(value) } as MessageEvent)
  }
  const advance = (time: number, run = true) => {
    now = time
    if (!run) return
    // The test advances the monotonic clock in one step, as after tab suspension.
    const due = timers.filter((timer) => !timer.cancelled && timer.at <= now)
    for (const timer of due) { timer.cancelled = true; timer.callback() }
  }
  const fault = () => sockets.at(-1)!.onerror?.call(sockets.at(-1) as unknown as WebSocket, {} as Parameters<NonNullable<RoomSocket['onerror']>>[0])
  return { machine, sockets, timers, statuses, messages, frame, advance, fault,
    network: (online: boolean) => { network = online; if (online) machine.online(); else machine.offline() },
    diagnoses: () => diagnoses, recoveries: () => recoveries }
}

test('T22/T23/T40 terminal initial snapshot reaches the consumer before any ping or retry', () => {
  for (const sold of [false, true]) {
    const h = harness(false)
    h.network(true)
    h.network(true)
    const final: RoomMessage = { ...snapshot, room: { ...snapshot.room,
      phase: 'ended', settlement_status: 'settled', settlement: {
        outcome: sold ? 'sold' : 'unsold', winner_alias: sold ? 'Licitante-AAAAAAAAAAAAAAAA' : null,
        final_amount_cents: sold ? 10000 : null, bid_count: sold ? 1 : 0,
        final_hash: (sold ? 'a' : '0').repeat(64), settled_at: '2026-10-27T13:00:00Z',
      } } }
    h.frame(final)
    assert.equal(h.statuses.at(-1), 'terminal')
    assert.deepEqual(h.messages, [final])
    assert.equal(h.sockets[0].sent.length, 0)
    h.network(false); h.network(true)
    h.advance(90_000)
    for (const timer of h.timers) timer.callback()
    assert.equal(h.sockets.length, 1)
    assert.equal(h.sockets[0].closes, 1)
  }
})

test('T21/T38 current lot_closed drains client activity; delayed callbacks stay retired', () => {
  const h = harness()
  h.frame(snapshot)
  h.frame({ type: 'pong', id: 1 })
  const oldMessage = h.sockets[0].onmessage!
  const frame = { type: 'lot_closed', lot_id: LOT, outcome: 'unsold', winner_alias: null,
    final_amount_cents: null, bid_count: 0, final_hash: '0'.repeat(64),
    settled_at: '2026-10-27T13:00:00Z', as_of: '2026-10-27T13:00:00Z' }
  h.frame(frame)
  assert.equal(h.statuses.at(-1), 'terminal')
  oldMessage.call(h.sockets[0] as unknown as WebSocket, { data: JSON.stringify(snapshot) } as MessageEvent)
  h.advance(120_000)
  h.network(true)
  assert.deepEqual(h.messages, [snapshot, frame])
  assert.equal(h.sockets.length, 1)
  assert.equal(h.sockets[0].sent.length, 1)
})

test('opening requires its own valid snapshot and one total 30s deadline', () => {
  const h = harness()
  h.sockets[0].onopen?.call(h.sockets[0] as unknown as WebSocket, {} as Event)
  for (const invalid of [{ type: 'pong', id: 1 }, { ...snapshot, type: 'bid_accepted' },
    { type: 'lot_cancelled', lot_id: LOT, cancelled_at: snapshot.room.as_of },
    { ...snapshot, lot_id: '00000000-0000-4000-8000-000000000002' }, {}]) h.frame(invalid)
  assert.equal(h.statuses.at(-1), 'connecting')
  assert.equal(h.messages.length, 0)
  h.advance(29_999)
  assert.equal(h.statuses.at(-1), 'connecting')
  h.advance(30_000)
  assert.equal(h.statuses.at(-1), 'reconnecting')
  assert.equal(h.diagnoses(), 1)
  assert.equal(h.sockets[0].closes, 1)
  h.machine.stop()
})
test('first ping is immediate; pong does not move the next send from t=20s', () => {
  const h = harness()
  h.frame(snapshot)
  assert.equal(h.statuses.at(-1), 'connected')
  assert.deepEqual(h.sockets[0].sent, ['{"type":"ping","id":1}'])
  h.advance(9_000)
  h.frame({ type: 'pong', id: 1 })
  h.frame({ type: 'pong', id: 1 })
  h.frame(snapshot) // duplicate snapshot does not restart heartbeat
  h.advance(19_999)
  assert.equal(h.sockets[0].sent.length, 1)
  h.advance(20_000)
  assert.equal(h.sockets[0].sent.length, 2)
  h.machine.stop()
})
test('pong at the exact deadline fails once; bid frames and wrong pongs never satisfy it', () => {
  const h = harness()
  h.frame(snapshot)
  const error = h.sockets[0].onerror!
  const close = h.sockets[0].onclose!
  h.advance(9_999)
  h.frame({ type: 'pong', id: 2 })
  h.frame({ ...snapshot, type: 'bid_accepted' })
  h.advance(10_000, false)
  h.frame({ type: 'pong', id: 1 })
  error.call(h.sockets[0] as unknown as WebSocket, {} as Parameters<NonNullable<RoomSocket['onerror']>>[0])
  close.call(h.sockets[0] as unknown as WebSocket, {} as CloseEvent)
  assert.equal(h.sockets[0].closes, 1)
  assert.equal(h.timers.filter((t) => !t.cancelled).length, 1)
  h.advance(10_500)
  assert.equal(h.sockets.length, 2)
  h.machine.stop()
})
test('equal jitter saturates without overflow', () => {
  for (const failures of [0, 1, 2, 4, 5, 100_000]) {
    const cap = Math.min(30_000, 1_000 * 2 ** Math.min(failures, 5))
    assert.equal(retryDelay(failures, 0), cap / 2)
    assert.equal(retryDelay(failures, .5), cap * .75)
    assert.equal(retryDelay(failures, 1), cap)
  }
})
test('error without close retries; only snapshot plus its first valid pong resets backoff', () => {
  const h = harness()
  h.fault()
  h.advance(500)
  h.frame(snapshot)
  h.fault() // snapshot alone does not reset k
  h.advance(1_499)
  assert.equal(h.sockets.length, 2)
  h.advance(1_500)
  h.frame(snapshot)
  h.frame({ type: 'pong', id: 1 })
  h.fault()
  h.advance(2_000)
  assert.equal(h.sockets.length, 4)
  h.machine.stop()
})
test('offline mounts no socket and flapping online deduplicates without waiting for CLOSED', () => {
  const h = harness(false)
  assert.equal(h.sockets.length, 0)
  h.network(true)
  h.network(true)
  assert.equal(h.sockets.length, 1)
  const oldMessage = h.sockets[0].onmessage!
  const oldClose = h.sockets[0].onclose!
  h.network(false)
  h.network(true)
  h.frame(snapshot)
  oldMessage.call(h.sockets[0] as unknown as WebSocket, { data: JSON.stringify({ type: 'lot_cancelled', lot_id: LOT, cancelled_at: snapshot.room.as_of }) } as MessageEvent)
  oldClose.call(h.sockets[0] as unknown as WebSocket, {} as CloseEvent)
  assert.equal(h.statuses.at(-1), 'connected')
  assert.equal(h.messages.length, 1)
  assert.equal(h.sockets.length, 2)
  h.machine.stop()
})
test('cancelled retry and disposed callbacks stay inert, including remount', () => {
  const h = harness()
  h.fault()
  const retry = h.timers.at(-1)!.callback
  h.network(true)
  retry()
  assert.equal(h.sockets.length, 2)
  h.machine.stop()
  for (const timer of h.timers) timer.callback()
  h.network(true)
  assert.equal(h.sockets.length, 2)
  const next = harness()
  assert.equal(next.sockets.length, 1)
  next.machine.stop()
})
test('visible reevaluates one expired deadline or send, never catches up missed ticks', () => {
  const h = harness()
  h.frame(snapshot)
  h.frame({ type: 'pong', id: 1 })
  h.advance(90_000, false)
  h.machine.visible()
  assert.equal(h.sockets[0].sent.length, 2)
  h.advance(100_000, false)
  h.machine.visible()
  assert.equal(h.sockets[0].closes, 1)
  h.advance(120_000, false)
  h.machine.visible()
  assert.equal(h.sockets.length, 2)
  for (const timer of h.timers.filter((t) => t.cancelled)) timer.callback()
  assert.equal(h.sockets.length, 2)
  h.machine.stop()
})
test('terminal delivery stops all activity and a retired pong cannot satisfy current ping', () => {
  const h = harness()
  h.frame(snapshot)
  const message = h.sockets[0].onmessage!
  h.fault()
  h.advance(500)
  h.frame(snapshot)
  message.call(h.sockets[0] as unknown as WebSocket, { data: '{"type":"pong","id":1}' } as MessageEvent)
  h.advance(10_500)
  assert.equal(h.sockets[1].closes, 1)
  h.advance(11_500)
  h.frame(snapshot)
  h.frame({ type: 'lot_cancelled', lot_id: LOT, cancelled_at: snapshot.room.as_of })
  assert.equal(h.messages.at(-1)?.type, 'lot_cancelled')
  const total = h.sockets.length
  for (const timer of h.timers) timer.callback()
  h.network(true)
  assert.equal(h.sockets.length, total)
})
test('constructor exception gets one recovery timer and one diagnostic per episode', () => {
  const h = harness(true, true)
  h.advance(500)
  h.advance(1_500)
  assert.equal(h.diagnoses(), 1)
  assert.equal(h.timers.filter((t) => !t.cancelled).length, 1)
  h.machine.stop()
})

test('repeated snapshot-only recoveries grow backoff, offline preserves k, and send failure recovers', () => {
  const h = harness()
  h.frame(snapshot)
  h.advance(10_000)
  h.advance(10_500)
  assert.equal(h.sockets.length, 2)
  h.frame(snapshot)
  h.advance(20_500)
  h.network(false)
  h.network(true) // immediate online does not reset the two failures
  h.frame(snapshot)
  h.advance(30_500)
  h.advance(32_499)
  assert.equal(h.sockets.length, 3)
  h.advance(32_500)
  assert.equal(h.sockets.length, 4)
  h.sockets[3].send = () => { throw new Error('send') }
  h.frame(snapshot)
  assert.equal(h.sockets[3].closes, 1)
  assert.equal(h.statuses.at(-1), 'reconnecting')
  h.machine.stop()
})
test('all old generation messages including the current ping id are powerless after replacement', () => {
  const h = harness()
  h.frame(snapshot)
  const oldMessage = h.sockets[0].onmessage!
  const oldOpen = h.sockets[0].onopen!
  h.network(false)
  h.network(true)
  h.frame(snapshot)
  const states = h.statuses.length
  const delivered = h.messages.length
  for (const value of [snapshot, { ...snapshot, type: 'bid_accepted', room: { ...snapshot.room, bid_count: 100 } }, { type: 'pong', id: 1 }]) {
    oldMessage.call(h.sockets[0] as unknown as WebSocket, { data: JSON.stringify(value) } as MessageEvent)
  }
  oldOpen.call(h.sockets[0] as unknown as WebSocket, {} as Event)
  assert.equal(h.statuses.length, states)
  assert.equal(h.messages.length, delivered)
  h.advance(10_000)
  assert.equal(h.sockets[1].closes, 1)
  h.machine.stop()
})

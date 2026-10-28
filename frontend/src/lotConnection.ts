import { parseRoomMessage, type ConnectionState, type RoomMessage } from './lotRoomSocket.ts'

export interface RoomSocket {
  readyState: number
  onopen: WebSocket['onopen']
  onmessage: WebSocket['onmessage']
  onerror: WebSocket['onerror']
  onclose: WebSocket['onclose']
  send(data: string): void
  close(): void
}
interface Adapter {
  socket: () => RoomSocket
  now: () => number
  schedule: (callback: () => void, delay: number) => () => void
  random: () => number
  online: () => boolean
  status: (state: ConnectionState, offline?: boolean) => void
  message: (event: RoomMessage) => void
  diagnose: () => void
  recovered: () => void
}
export function retryDelay(failures: number, random: number): number {
  const cap = Math.min(30_000, 1_000 * 2 ** Math.min(failures, 5))
  return cap / 2 + random * cap / 2
}

// Transport authority belongs to this instance and its current attempt. Timers carry
// identity too, so even an already queued, cancelled callback cannot reopen it.
export function createLotConnection(lotId: string, adapter: Adapter) {
  type Attempt = { socket: RoomSocket | null; initialized: boolean; verified: boolean;
    opening: number; heartbeat: number; pong: number | null; id: number }
  let current: Attempt | null = null
  let stopped = false
  let failures = 0
  let diagnosed = false
  let retry: number | null = null
  let cancelTimer: (() => void) | null = null
  let timerToken = 0
  const clearTimer = () => { timerToken++; cancelTimer?.(); cancelTimer = null }
  const retire = () => {
    const old = current
    current = null
    if (old?.socket) {
      old.socket.onopen = old.socket.onmessage = old.socket.onerror = old.socket.onclose = null
      try { old.socket.close() } catch { /* already closed */ }
    }
  }
  const valid = (attempt: Attempt) => !stopped && current === attempt
  const arm = (deadline: number) => {
    clearTimer()
    const token = timerToken
    cancelTimer = adapter.schedule(() => {
      if (stopped || token !== timerToken) return
      cancelTimer = null
      evaluate()
    }, Math.max(0, deadline - adapter.now()))
  }
  const fail = (attempt: Attempt) => {
    if (!valid(attempt)) return
    const needsDiagnosis = !attempt.initialized
    retire()
    clearTimer()
    adapter.status('unavailable', !adapter.online())
    if (!adapter.online()) return
    retry = adapter.now() + retryDelay(failures, adapter.random())
    failures = Math.min(failures + 1, 32)
    adapter.status('reconnecting')
    arm(retry)
    if (needsDiagnosis && !diagnosed) { diagnosed = true; adapter.diagnose() }
  }
  const ping = (attempt: Attempt) => {
    if (!valid(attempt) || attempt.pong !== null) return
    const now = adapter.now()
    attempt.id++
    attempt.pong = now + 10_000
    attempt.heartbeat = now + 20_000
    try {
      if (attempt.socket?.readyState !== 1) throw new Error('socket unavailable')
      attempt.socket.send(JSON.stringify({ type: 'ping', id: attempt.id }))
    } catch { fail(attempt); return }
    arm(attempt.pong)
  }
  const open = (initial = false) => {
    if (stopped || current !== null || !adapter.online()) return
    clearTimer()
    retry = null
    adapter.status(initial ? 'connecting' : 'reconnecting')
    const attempt: Attempt = { socket: null, initialized: false, verified: false,
      opening: adapter.now() + 30_000, heartbeat: Infinity, pong: null, id: 0 }
    current = attempt
    try { attempt.socket = adapter.socket() } catch { fail(attempt); return }
    const socket = attempt.socket
    socket.onopen = () => { if (valid(attempt)) evaluate() }
    socket.onerror = socket.onclose = () => fail(attempt)
    socket.onmessage = ({ data }) => {
      if (!valid(attempt)) return
      const now = adapter.now()
      if ((!attempt.initialized && now >= attempt.opening) ||
          (attempt.pong !== null && now >= attempt.pong)) { fail(attempt); return }
      let payload: unknown
      try { payload = typeof data === 'string' ? JSON.parse(data) : null } catch { payload = null }
      if (typeof payload === 'object' && payload !== null && !Array.isArray(payload)) {
        const pong = payload as Record<string, unknown>
        if (Object.keys(pong).length === 2 && pong.type === 'pong' &&
            Number.isSafeInteger(pong.id) && pong.id === attempt.id && attempt.pong !== null) {
          attempt.pong = null
          if (!attempt.verified) { attempt.verified = true; failures = 0 }
          arm(attempt.heartbeat)
          return
        }
      }
      const event = parseRoomMessage(data)
      if (event === null || event.lot_id !== lotId) return
      if (!attempt.initialized) {
        if (event.type !== 'room_snapshot') return
        attempt.initialized = true
        diagnosed = false
        adapter.recovered()
        if (event.room.settlement_status === 'settled') {
          stop('terminal')
          adapter.message(event)
          return
        }
        adapter.status('connected')
        adapter.message(event)
        if (valid(attempt)) ping(attempt)
      } else {
        if (event.type === 'lot_cancelled' || event.type === 'lot_closed' ||
            event.room.settlement_status === 'settled') stop('terminal')
        adapter.message(event)
      }
    }
    arm(attempt.opening)
  }
  function offline() {
    if (stopped) return
    retire(); clearTimer(); retry = null
    adapter.status('unavailable', true)
  }
  function evaluate() {
    if (stopped) return
    if (!adapter.online()) { offline(); return }
    const now = adapter.now()
    if (current !== null) {
      if ((!current.initialized && now >= current.opening) ||
          (current.pong !== null && now >= current.pong)) { fail(current); return }
      if (current.initialized && current.pong === null && now >= current.heartbeat) {
        ping(current); return
      }
      arm(!current.initialized ? current.opening : current.pong ?? current.heartbeat)
    } else if (retry !== null) {
      if (now >= retry) open()
      else arm(retry)
    }
  }
  function online() { if (!stopped && adapter.online() && current === null) open() }
  function stop(state: 'terminal' | 'disposed' = 'disposed') {
    if (stopped) return
    stopped = true; clearTimer(); retry = null; retire(); adapter.status(state)
  }
  if (adapter.online()) open(true)
  else offline()
  return { offline, online, visible: evaluate, stop }
}

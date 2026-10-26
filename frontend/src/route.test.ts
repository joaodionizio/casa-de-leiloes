// Testes das rotas do front (Story 2.5, P5, D7, D8): `node --test`, sem DOM.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  isAuctioneerRoute,
  isBidderRoute,
  isRestrictedRoute,
  parseRoute,
  readNavState,
  routePath,
  safeReturnPath,
  shouldHandleClick,
  type AppRoute,
  type ClickLike,
} from './route.ts'

const LOT_ID = '2d484387-2509-5e8e-2c43-22f9981972eb'

test('as seis rotas conhecidas', () => {
  assert.deepEqual(parseRoute('/'), { kind: 'vitrine' })
  assert.deepEqual(parseRoute(`/lots/${LOT_ID}`), { kind: 'lot', lotId: LOT_ID })
  assert.deepEqual(parseRoute('/login'), { kind: 'login' })
  assert.deepEqual(parseRoute('/auctioneer/lots'), { kind: 'my-lots' })
  assert.deepEqual(parseRoute('/auctioneer/lots/new'), { kind: 'create-lot' })
  assert.deepEqual(parseRoute('/bidder/wallet'), { kind: 'wallet' })
})

test('o que não é rota conhecida vira "não encontrado", sem chamar a API', () => {
  const unknown = [
    '',
    '/x',
    '/lots',
    '/lots/',
    '/lots/abc',
    `/lots/${LOT_ID.toUpperCase()}`,
    `/lots/${LOT_ID}/`,
    `/lots/${LOT_ID}/x`,
    '/lots/2d484387-2509-5e8e-2c43-22f9981972e',
    '/login/',
    '/auctioneer',
    '/auctioneer/lots/',
    '/auctioneer/lots/new/',
    '/api/lots',
    '//evil.com',
  ]
  for (const path of unknown) {
    assert.deepEqual(parseRoute(path), { kind: 'not-found' }, path)
  }
})

test('query e hash são ignorados', () => {
  assert.deepEqual(parseRoute('/?q=1'), { kind: 'vitrine' })
  assert.deepEqual(parseRoute(`/lots/${LOT_ID}#topo`), { kind: 'lot', lotId: LOT_ID })
  assert.deepEqual(parseRoute('/login?x=1#y'), { kind: 'login' })
})

test('routePath e parseRoute fazem ida e volta', () => {
  const routes: AppRoute[] = [
    { kind: 'vitrine' },
    { kind: 'lot', lotId: LOT_ID },
    { kind: 'login' },
    { kind: 'create-lot' },
    { kind: 'my-lots' },
    { kind: 'wallet' },
  ]
  for (const route of routes) {
    assert.deepEqual(parseRoute(routePath(route)), route)
  }
})

test('isAuctioneerRoute só vale para criar lote e meus lotes', () => {
  assert.equal(isAuctioneerRoute({ kind: 'create-lot' }), true)
  assert.equal(isAuctioneerRoute({ kind: 'my-lots' }), true)
  assert.equal(isAuctioneerRoute({ kind: 'vitrine' }), false)
  assert.equal(isAuctioneerRoute({ kind: 'login' }), false)
  assert.equal(isAuctioneerRoute({ kind: 'not-found' }), false)
})

test('/bidder/wallet é a carteira; variações viram não encontrado', () => {
  assert.deepEqual(parseRoute('/bidder/wallet'), { kind: 'wallet' })
  assert.deepEqual(parseRoute('/bidder/wallet?x=1#y'), { kind: 'wallet' })
  assert.equal(routePath({ kind: 'wallet' }), '/bidder/wallet')
  for (const path of ['/bidder/wallet/', '/bidder', '/bidder/', '/bidder/x', '/wallet']) {
    assert.deepEqual(parseRoute(path), { kind: 'not-found' }, path)
  }
})

test('isBidderRoute só vale para a carteira', () => {
  assert.equal(isBidderRoute({ kind: 'wallet' }), true)
  assert.equal(isBidderRoute({ kind: 'my-lots' }), false)
  assert.equal(isBidderRoute({ kind: 'vitrine' }), false)
  assert.equal(isBidderRoute({ kind: 'not-found' }), false)
})

test('isRestrictedRoute cobre as três áreas restritas e mais nada', () => {
  assert.equal(isRestrictedRoute({ kind: 'create-lot' }), true)
  assert.equal(isRestrictedRoute({ kind: 'my-lots' }), true)
  assert.equal(isRestrictedRoute({ kind: 'wallet' }), true)
  assert.equal(isRestrictedRoute({ kind: 'vitrine' }), false)
  assert.equal(isRestrictedRoute({ kind: 'login' }), false)
  assert.equal(isRestrictedRoute({ kind: 'lot', lotId: LOT_ID }), false)
  assert.equal(isRestrictedRoute({ kind: 'not-found' }), false)
})

test('safeReturnPath: a carteira só volta para quem entrou como BIDDER', () => {
  assert.equal(safeReturnPath('/bidder/wallet', 'BIDDER'), '/bidder/wallet')
  assert.equal(safeReturnPath('/bidder/wallet', 'AUCTIONEER'), '/')
  assert.equal(safeReturnPath('/bidder/wallet?next=https://evil.com', 'BIDDER'), '/bidder/wallet')
  assert.equal(safeReturnPath('//evil.com/bidder/wallet', 'BIDDER'), '/')
})

test('safeReturnPath aceita a vitrine e o lote', () => {
  assert.equal(safeReturnPath('/', 'BIDDER'), '/')
  assert.equal(safeReturnPath(`/lots/${LOT_ID}`, 'BIDDER'), `/lots/${LOT_ID}`)
  assert.equal(safeReturnPath(`/lots/${LOT_ID}`, 'AUCTIONEER'), `/lots/${LOT_ID}`)
})

test('safeReturnPath nunca deixa sair da aplicação (sem open redirect)', () => {
  const refused: unknown[] = [
    'https://evil.com',
    'http://evil.com/lots/x',
    '//evil.com',
    '/\\evil.com',
    'javascript:alert(1)',
    '/login',
    '/x',
    '/lots/abc',
    '',
    42,
    null,
    undefined,
    { path: '/' },
  ]
  for (const value of refused) {
    assert.equal(safeReturnPath(value, 'AUCTIONEER'), '/', String(value))
  }
})

test('safeReturnPath devolve o caminho normalizado, sem a query recebida', () => {
  assert.equal(safeReturnPath('/?next=https://evil.com', 'BIDDER'), '/')
  assert.equal(
    safeReturnPath(`/lots/${LOT_ID}?x=https://evil.com#y`, 'BIDDER'),
    `/lots/${LOT_ID}`,
  )
})

test('safeReturnPath: área do leiloeiro só para quem entrou como AUCTIONEER', () => {
  assert.equal(safeReturnPath('/auctioneer/lots', 'AUCTIONEER'), '/auctioneer/lots')
  assert.equal(
    safeReturnPath('/auctioneer/lots/new', 'AUCTIONEER'),
    '/auctioneer/lots/new',
  )
  assert.equal(safeReturnPath('/auctioneer/lots', 'BIDDER'), '/')
  assert.equal(safeReturnPath('/auctioneer/lots/new', 'BIDDER'), '/')
})

function click(overrides: Partial<ClickLike> = {}): ClickLike {
  return {
    button: 0,
    metaKey: false,
    ctrlKey: false,
    shiftKey: false,
    altKey: false,
    defaultPrevented: false,
    target: null,
    ...overrides,
  }
}

test('shouldHandleClick: só o clique simples é da SPA', () => {
  assert.equal(shouldHandleClick(click()), true)
  assert.equal(shouldHandleClick(click({ target: '' })), true)
  assert.equal(shouldHandleClick(click({ target: '_self' })), true)
})

test('shouldHandleClick: modificador, botão do meio, alvo externo ou evento tratado vão ao navegador', () => {
  const others: Array<Partial<ClickLike>> = [
    { metaKey: true },
    { ctrlKey: true },
    { shiftKey: true },
    { altKey: true },
    { button: 1 },
    { button: 2 },
    { defaultPrevented: true },
    { target: '_blank' },
  ]
  for (const override of others) {
    assert.equal(shouldHandleClick(click(override)), false, JSON.stringify(override))
  }
})

test('readNavState mantém um estado válido', () => {
  const state = readNavState({
    returnTo: '/',
    notice: 'expired',
    fromVitrine: true,
    restoreLotId: LOT_ID,
    endedVisible: 12,
  })
  assert.deepEqual(state, {
    returnTo: '/',
    notice: 'expired',
    fromVitrine: true,
    restoreLotId: LOT_ID,
    endedVisible: 12,
  })
})

test('readNavState descarta campo inválido sem derrubar os outros', () => {
  assert.deepEqual(
    readNavState({
      returnTo: 5,
      notice: 'outra',
      fromVitrine: 'sim',
      restoreLotId: 'abc',
      endedVisible: -1,
    }),
    {},
  )
  assert.deepEqual(readNavState({ endedVisible: 1.5, restoreLotId: LOT_ID }), {
    restoreLotId: LOT_ID,
  })
  assert.deepEqual(readNavState({ endedVisible: Number.NaN }), {})
  assert.deepEqual(readNavState({ fromVitrine: false }), {})
})

test('readNavState aceita qualquer coisa que não seja objeto', () => {
  for (const value of [null, undefined, 'texto', 7, true, []]) {
    assert.deepEqual(readNavState(value), {})
  }
})

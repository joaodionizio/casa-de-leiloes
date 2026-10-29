// Meus lotes e o cancelamento (Story 3.6): o que o navegador faz com a lista do dono e
// com as respostas do `POST /api/lots/{id}/cancel`. As regras do cancelamento (dono,
// gate, lances, fim, concorrência) são do back-end e têm testes em PostgreSQL real; aqui
// se prova DOM, foco, teclado e a contagem de pedidos contra a API simulada.
import { expect, test, type Page } from '@playwright/test'
import type { PrivateLotSettlementSummary } from '../src/api/lots'
import { formatCents } from '../src/money'
import { formatDateTime } from '../src/lotTime'
import {
  CANCELLED_AT,
  LONG_TITLE,
  lotId,
  makeLot,
  mockApi,
  type CancelMode,
  type MockMyLot,
  type MockOptions,
  type Phase,
} from './support/mockApi'

const MINE = 'GET /api/lots/mine'
const TARGET = lotId(1)
const PATH = '/auctioneer/lots'
const NEUTRAL_409 =
  'Não foi possível concluir a operação porque a integridade do lote não pôde ser confirmada.'
const AMBIGUOUS =
  'Não foi possível confirmar o cancelamento. Confira a lista atualizada antes de tentar novamente.'
const SOLD: PrivateLotSettlementSummary = { outcome: 'sold', winner_alias: 'Licitante-0123456789ABCDEF', final_amount_cents: 13000, bid_count: 3, settled_at: '2026-10-25T10:01:02.123456Z' }
const UNSOLD: PrivateLotSettlementSummary = { outcome: 'unsold', winner_alias: null, final_amount_cents: null, bid_count: 0, settled_at: SOLD.settled_at }
const STALE = 'Não foi possível atualizar a lista. Os dados exibidos podem estar desatualizados.'

function myLot(n: number, phase: Phase, overrides: Partial<MockMyLot> = {}): MockMyLot {
  const window =
    phase === 'live'
      ? { starts_at: '2026-10-25T09:00:00.000000Z', ends_at: '2026-10-26T09:00:00.000000Z' }
      : phase === 'scheduled'
        ? { starts_at: '2026-10-27T09:00:00.000000Z', ends_at: '2026-10-28T09:00:00.000000Z' }
        : { starts_at: '2026-10-20T09:00:00.000000Z', ends_at: '2026-10-21T09:00:00.000000Z' }
  return {
    id: lotId(n),
    title: `Obra de teste ${n}`,
    artist_display: `Artista ${n}`,
    ...window,
    phase,
    bid_count: 0,
    cancelled_at: null,
    ...overrides,
  }
}

function owner(cancel: CancelMode = 'ok', extra: MockOptions = {}): MockOptions {
  return {
    session: 'AUCTIONEER',
    myLots: [myLot(1, 'live'), myLot(2, 'scheduled')],
    cancel,
    ...extra,
  }
}

async function openList(page: Page) {
  await page.goto(PATH)
  await expect(page.getByRole('heading', { name: 'Meus lotes' })).toBeVisible()
  await expect(page.getByText('Obra de teste 1', { exact: true })).toBeVisible()
}

function row(page: Page, n: number) {
  return page.locator('li.lot-row').filter({ hasText: `Obra de teste ${n}` })
}

async function startCancel(page: Page, n = 1) {
  await row(page, n).getByRole('button', { name: /Cancelar lote/ }).click()
}

async function confirm(page: Page) {
  await page.getByRole('button', { name: 'Cancelar lote', exact: true }).click()
}

test.describe('elegibilidade e selo', () => {
  test('o CTA só aparece nas linhas aparentemente elegíveis; o cancelado leva o selo em texto', async ({
    page,
  }) => {
    await mockApi(page, {
      session: 'AUCTIONEER',
      myLots: [
        myLot(1, 'live'),
        myLot(2, 'scheduled'),
        myLot(3, 'live', { bid_count: 2 }),
        myLot(4, 'ended'),
        myLot(5, 'live', { cancelled_at: CANCELLED_AT }),
        myLot(6, 'ended', { cancelled_at: CANCELLED_AT }),
      ],
    })
    await openList(page)

    await expect(page.getByRole('button', { name: /Cancelar lote/ })).toHaveCount(3)
    await expect(row(page, 1).getByRole('button', { name: /Cancelar lote/ })).toBeVisible()
    await expect(row(page, 2).getByRole('button', { name: /Cancelar lote/ })).toBeVisible()
    for (const n of [4, 5, 6]) {
      await expect(row(page, n).getByRole('button')).toHaveCount(0)
    }
    // O cancelamento prevalece sobre a fase, inclusive sobre "Encerrado".
    await expect(row(page, 5).getByText('Cancelado', { exact: true })).toBeVisible()
    await expect(row(page, 6).getByText('Cancelado', { exact: true })).toBeVisible()
    await expect(row(page, 6).getByText('Encerrado', { exact: true })).toHaveCount(0)
    await expect(row(page, 1).getByText('Ao vivo', { exact: true })).toBeVisible()
    await expect(row(page, 2).getByText('Agendado', { exact: true })).toBeVisible()
    await expect(row(page, 3).getByText('2 lances')).toBeVisible()
    await expect(row(page, 1).getByText('0 lances')).toBeVisible()
  })

  test('a lista continua vazia sem lotes e o contrato antigo sem as_of não vira lista vazia', async ({
    page,
  }) => {
    await mockApi(page, { session: 'AUCTIONEER' })
    await page.goto(PATH)
    await expect(page.getByText('Você ainda não criou lotes.')).toBeVisible()

    await page.route('**/api/lots/mine', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      }),
    )
    await page.reload()
    await expect(page.getByText('Não foi possível carregar seus lotes.')).toBeVisible()
    await expect(page.getByText('Você ainda não criou lotes.')).toHaveCount(0)
  })
})

test.describe('resultado persistido e atualização (4.5)', () => {
  test('loading e falha inicial não inventam total nem vazio; retry recupera', async ({ page }) => {
    const api = await mockApi(page, owner())
    const held = api.hold(MINE)
    await page.goto(PATH)
    await expect(page.getByText('Carregando seus lotes…')).toBeVisible()
    await expect(page.locator('.my-lots-total')).toHaveCount(0)
    held.fail()
    await expect(page.getByText('Não foi possível carregar seus lotes.')).toBeVisible()
    await expect(page.getByText('Você ainda não criou lotes.')).toHaveCount(0)
    await expect(page.locator('.my-lots-total')).toHaveCount(0)
    await page.getByRole('button', { name: 'Tentar novamente' }).click()
    await expect(page.locator('li.lot-row')).toHaveCount(2)
    await expect(page.locator('.my-lots-total')).toContainText(formatCents(0))
    expect(api.count(MINE)).toBe(2)
  })

  test('sold/unsold/pending/cancelled mostram dados corretos e total na mesma lista', async ({ page }) => {
    const api = await mockApi(page, owner('ok', { myLots: [
      myLot(1, 'ended', { settlement: SOLD, bid_count: 3 }),
      myLot(2, 'ended', { settlement: UNSOLD }),
      myLot(3, 'ended'),
      myLot(4, 'ended', { cancelled_at: CANCELLED_AT }),
      myLot(5, 'live'), myLot(6, 'scheduled'),
    ] }))
    await openList(page)
    await expect(row(page, 1).getByText('Vendido', { exact: true })).toBeVisible()
    await expect(row(page, 1).getByText(SOLD.winner_alias!)).toBeVisible()
    await expect(row(page, 1).getByText(formatCents(13000))).toBeVisible()
    await expect(row(page, 1).getByText('3 lances')).toHaveCount(1)
    await expect(row(page, 1).getByText(formatDateTime(SOLD.settled_at))).toBeVisible()
    await expect(row(page, 2).getByText('Sem arremate', { exact: true })).toBeVisible()
    await expect(row(page, 2).getByText('Vencedor', { exact: true })).toHaveCount(0)
    await expect(row(page, 2).getByText('Valor final', { exact: true })).toHaveCount(0)
    await expect(row(page, 3).getByText('Encerrado, apurando resultado')).toBeVisible()
    await expect(row(page, 4).getByText('Cancelado', { exact: true })).toBeVisible()
    await expect(page.locator('.my-lots-total')).toContainText(formatCents(13000))
    await expect(page.getByText(/Situação atualizada:/)).toBeVisible()
    expect(api.count(MINE)).toBe(1)
    expect(api.unexpected).toEqual([])
  })

  for (const [outcome, result, label] of [['sold', SOLD, 'Vendido'], ['unsold', UNSOLD, 'Sem arremate']] as const) {
    test(`manual pending→${outcome} troca resultado e total juntos sem mover foco`, async ({ page }) => {
      const api = await mockApi(page, owner('ok', { myLots: [myLot(1, 'ended')] }))
      await openList(page)
      await expect(row(page, 1).getByText('Encerrado, apurando resultado')).toBeVisible()
      api.setMyLotSettlement(TARGET, result)
      const button = page.getByRole('button', { name: 'Atualizar', exact: true })
      await button.click()
      await expect(row(page, 1).getByText(label, { exact: true })).toBeVisible()
      await expect(button).toBeFocused()
      await expect(page.locator('.my-lots-total')).toContainText(formatCents(outcome === 'sold' ? 13000 : 0))
      expect(api.count(MINE)).toBe(2)
      expect(api.cancelPosts).toHaveLength(0)
    })
  }

  test('focus/visible/manual são deduplicados durante leitura e cancelamento pendente', async ({ page }) => {
    const api = await mockApi(page, owner('ok', { cancelDelayMs: 700 }))
    await openList(page)
    const held = api.hold(MINE)
    await page.getByRole('button', { name: 'Atualizar', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Atualizando…', exact: true })).toBeDisabled()
    await page.evaluate(() => {
      window.dispatchEvent(new Event('blur'))
      document.dispatchEvent(new Event('visibilitychange'))
      window.dispatchEvent(new Event('focus'))
    })
    expect(api.count(MINE)).toBe(2)
    held.release()
    await expect(page.getByRole('button', { name: 'Atualizar', exact: true })).toBeEnabled()
    await startCancel(page)
    await confirm(page)
    await expect(page.getByRole('button', { name: 'Cancelando…' })).toBeDisabled()
    await page.evaluate(() => { window.dispatchEvent(new Event('blur')); window.dispatchEvent(new Event('focus')) })
    expect(api.count(MINE)).toBe(2)
    await expect(page.getByText('Lote cancelado.', { exact: true })).toBeVisible()
    expect(api.count(MINE)).toBe(3)
  })

  test('foco relê resultado uma vez; refresh falho conserva snapshot e total com stale', async ({ page }) => {
    const api = await mockApi(page, owner('ok', { myLots: [myLot(1, 'ended', { settlement: SOLD, bid_count: 3 })] }))
    await openList(page)
    const held = api.hold(MINE)
    await page.evaluate(() => { window.dispatchEvent(new Event('blur')); window.dispatchEvent(new Event('focus')) })
    await expect(page.getByRole('button', { name: 'Atualizando…', exact: true })).toBeDisabled()
    held.fail()
    await expect(page.getByText(STALE, { exact: true })).toBeVisible()
    await expect(row(page, 1).getByText('Vendido', { exact: true })).toBeVisible()
    await expect(page.locator('.my-lots-total')).toContainText(formatCents(13000))
    await page.getByRole('button', { name: 'Atualizar', exact: true }).click()
    await expect(page.getByText(STALE, { exact: true })).toHaveCount(0)
    expect(api.count(MINE)).toBe(3)
  })

  for (const status of [401, 403]) {
    test(`${status} limpa resultado e total e encerra tentativas automáticas`, async ({ page }) => {
      await mockApi(page, owner('ok', { myLots: [myLot(1, 'ended', { settlement: SOLD, bid_count: 3 })] }))
      await openList(page)
      let requests = 0
      await page.route('**/api/lots/mine', (route) => {
        requests += 1
        return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify({ status, code: status === 401 ? 'unauthorized' : 'forbidden', message: 'PRIVATE' }) })
      })
      await page.getByRole('button', { name: 'Atualizar', exact: true }).click()
      await expect(page.locator('.my-lots-total')).toHaveCount(0)
      await expect(page.getByText(SOLD.winner_alias!)).toHaveCount(0)
      if (status === 403) {
        await expect(page.getByText('Sua conta não tem acesso a esta lista.')).toBeVisible()
        await expect(page.getByRole('button', { name: 'Tentar novamente' })).toHaveCount(0)
      }
      await page.evaluate(() => { window.dispatchEvent(new Event('blur')); window.dispatchEvent(new Event('focus')) })
      expect(requests).toBe(1)
      await expect(page.getByText('PRIVATE', { exact: true })).toHaveCount(0)
    })
  }

  test('contrato privado inesperado falha inteiro e conserva snapshot anterior', async ({ page }) => {
    await mockApi(page, owner('ok', { myLots: [myLot(1, 'ended', { settlement: SOLD, bid_count: 3 })] }))
    await openList(page)
    const current = await page.evaluate(async () => (await fetch('/api/lots/mine')).json())
    current.items[0].settlement.winner_user_id = 'PRIVATE-WINNER-ID'
    await page.route('**/api/lots/mine', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(current) }))
    await page.getByRole('button', { name: 'Atualizar', exact: true }).click()
    await expect(page.getByText(STALE, { exact: true })).toBeVisible()
    await expect(page.getByText('PRIVATE-WINNER-ID')).toHaveCount(0)
    await expect(page.locator('.my-lots-total')).toContainText(formatCents(13000))
  })

  test('resposta antiga entregue apesar de abort após remontagem não substitui sold', async ({ page }) => {
    await page.addInitScript(() => {
      const original = window.fetch.bind(window)
      let held = false
      window.fetch = async (...args) => {
        const response = await original(...args)
        if (!held && String(args[0]) === '/api/lots/mine') {
          held = true
          return new Promise<Response>((resolve) => {
            Object.assign(window, { releaseOldMine: () => resolve(response) })
          })
        }
        return response
      }
    })
    const api = await mockApi(page, owner('ok', { myLots: [myLot(1, 'ended')] }))
    await page.goto(PATH)
    await expect(page.getByText('Carregando seus lotes…')).toBeVisible()
    await expect.poll(() => api.count(MINE)).toBe(1)
    await page.getByRole('link', { name: 'Vitrine', exact: true }).click()
    api.setMyLotSettlement(TARGET, SOLD)
    await page.getByRole('link', { name: 'Meus lotes', exact: true }).click()
    await expect(row(page, 1).getByText('Vendido', { exact: true })).toBeVisible()
    await page.evaluate(() => { (window as unknown as { releaseOldMine: () => void }).releaseOldMine() })
    await expect(row(page, 1).getByText('Vendido', { exact: true })).toBeVisible()
    await expect(page.locator('.my-lots-total')).toContainText(formatCents(13000))
  })

  test('logout invalida uma leitura antiga antes de entrar em outra conta', async ({ page }) => {
    await page.addInitScript(() => {
      const original = window.fetch.bind(window)
      let reads = 0
      window.fetch = async (...args) => {
        const response = await original(...args)
        if (String(args[0]) === '/api/lots/mine' && ++reads === 2) {
          return new Promise<Response>((resolve) => {
            Object.assign(window, { releaseAccountRead: () => resolve(response) })
          })
        }
        return response
      }
    })
    const api = await mockApi(page, owner('ok', { myLots: [myLot(1, 'ended', { settlement: SOLD, bid_count: 3 })] }))
    await openList(page)
    await page.getByRole('button', { name: 'Atualizar', exact: true }).click()
    await expect.poll(() => api.count(MINE)).toBe(2)
    await page.getByRole('button', { name: 'Sair', exact: true }).click()
    await expect(page.getByText(SOLD.winner_alias!)).toHaveCount(0)
    await page.route('**/api/lots/mine', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ as_of: '2026-10-25T15:00:00Z', items: [], total_received_cents: 0 }) }))
    await page.getByRole('link', { name: 'Entrar', exact: true }).click()
    await page.getByLabel('E-mail', { exact: true }).fill('auctioneer2@example.com')
    await page.getByLabel('Senha', { exact: true }).fill('Demo123!')
    await page.getByRole('button', { name: 'Entrar', exact: true }).click()
    await page.getByRole('link', { name: 'Meus lotes', exact: true }).click()
    await expect(page.getByText('Você ainda não criou lotes.')).toBeVisible()
    await page.evaluate(() => { (window as unknown as { releaseAccountRead: () => void }).releaseAccountRead() })
    await expect(page.getByText('Você ainda não criou lotes.')).toBeVisible()
    await expect(page.getByText(SOLD.winner_alias!)).toHaveCount(0)
    await expect(page.locator('.my-lots-total')).toContainText(formatCents(0))
  })

  for (const width of [320, 375, 1440]) {
    test(`50 resultados, valor máximo e imagem falha em ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: width === 1440 ? 900 : 812 })
      await mockApi(page, owner('ok', { images: 'broken', myLots: Array.from({ length: 50 }, (_, index) => myLot(index + 1, 'ended', { title: index === 0 ? LONG_TITLE : `Obra de teste ${index + 1}`, bid_count: 3, settlement: { ...SOLD, final_amount_cents: index === 0 ? Number.MAX_SAFE_INTEGER - 49 * 13000 : 13000 } })) }))
      await page.goto(PATH)
      await expect(page.locator('li.lot-row')).toHaveCount(50)
      await expect(page.locator('.my-lots-total')).toContainText(formatCents(Number.MAX_SAFE_INTEGER))
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
    })
  }
})

test.describe('confirmação inline', () => {
  test('o clique abre a confirmação na linha, com foco no botão; Voltar devolve o foco ao CTA', async ({
    page,
  }) => {
    const api = await mockApi(page, owner())
    await openList(page)

    await startCancel(page)

    const confirmation = row(page, 1).getByRole('group')
    await expect(confirmation).toContainText('O lote sai da vitrine e não pode ser reaberto.')
    await expect(page.getByRole('button', { name: 'Cancelar lote', exact: true })).toBeFocused()
    // Só uma confirmação por vez e nenhum pedido ainda.
    await expect(page.getByRole('button', { name: 'Cancelar lote', exact: true })).toHaveCount(1)
    expect(api.cancelPosts).toHaveLength(0)

    await page.getByRole('button', { name: 'Voltar' }).click()

    await expect(confirmation).toHaveCount(0)
    await expect(row(page, 1).getByRole('button', { name: /Cancelar lote/ })).toBeFocused()
    expect(api.cancelPosts).toHaveLength(0)
  })

  test('teclado: Enter abre, Enter confirma, e o foco vai ao título', async ({ page }) => {
    const api = await mockApi(page, owner())
    await openList(page)

    const cta = row(page, 1).getByRole('button', { name: /Cancelar lote/ })
    await cta.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('button', { name: 'Cancelar lote', exact: true })).toBeFocused()
    await page.keyboard.press('Enter')

    await expect(page.getByText('Lote cancelado.', { exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Meus lotes' })).toBeFocused()
    expect(api.cancelPosts).toEqual([TARGET])
  })
})

test.describe('envio e sucesso', () => {
  test('sucesso: um POST, uma releitura, o item fica com o selo e sem CTA', async ({ page }) => {
    const api = await mockApi(page, owner())
    await openList(page)
    expect(api.count(MINE)).toBe(1)

    await startCancel(page)
    await confirm(page)

    await expect(page.getByText('Lote cancelado.', { exact: true })).toBeVisible()
    await expect(row(page, 1).getByText('Cancelado', { exact: true })).toBeVisible()
    await expect(row(page, 1).getByRole('button')).toHaveCount(0)
    await expect(row(page, 2).getByRole('button', { name: /Cancelar lote/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Meus lotes' })).toBeFocused()
    expect(api.cancelPosts).toEqual([TARGET])
    expect(api.count(MINE)).toBe(2)
    expect(api.unexpected).toEqual([])
  })

  test('envio pendente: botão desabilitado, "Cancelando…" e nenhum segundo POST', async ({
    page,
  }) => {
    const api = await mockApi(page, owner('ok', { cancelDelayMs: 600 }))
    await openList(page)
    await startCancel(page)

    const button = page.getByRole('button', { name: 'Cancelar lote', exact: true })
    await button.click()
    const pending = page.getByRole('button', { name: 'Cancelando…' })
    await expect(pending).toBeDisabled()
    await pending.click({ force: true }).catch(() => undefined)
    await page.keyboard.press('Enter')
    await expect(row(page, 2).getByRole('button', { name: /Cancelar lote/ })).toBeDisabled()
    await expect(row(page, 1).getByRole('button', { name: 'Voltar' })).toBeDisabled()

    await expect(page.getByText('Lote cancelado.', { exact: true })).toBeVisible()
    expect(api.cancelPosts).toHaveLength(1)
  })

  test('sucesso com a releitura falha: mantém "Lote cancelado." e avisa da lista', async ({
    page,
  }) => {
    const api = await mockApi(page, owner('ok', { mineRereadFail: true }))
    await openList(page)
    await startCancel(page)
    await confirm(page)

    await expect(
      page.getByText('Lote cancelado. Não foi possível atualizar a lista.'),
    ).toBeVisible()
    expect(api.cancelPosts).toHaveLength(1)
    expect(api.count(MINE)).toBe(2)
  })
})

test.describe('falhas de negócio, pelo code', () => {
  const cases: Array<[CancelMode, string, boolean]> = [
    ['ended', 'Este lote já foi encerrado.', true],
    ['integrity', NEUTRAL_409, false],
    ['forbidden', 'Você não pode cancelar este lote.', false],
    ['not_found', 'Lote não encontrado.', false],
  ]
  for (const [mode, text, refetches] of cases) {
    test(`${mode}: texto pelo code, sem mensagem do servidor e ${refetches ? 'com' : 'sem'} releitura`, async ({
      page,
    }) => {
      const api = await mockApi(page, owner(mode))
      await openList(page)
      await startCancel(page)
      await confirm(page)

      await expect(page.getByRole('alert').filter({ hasText: text })).toBeVisible()
      await expect(page.getByText('MENSAGEM DO SERVIDOR')).toHaveCount(0)
      await expect(page.getByText('Lote cancelado.', { exact: true })).toHaveCount(0)
      await expect(row(page, 1).getByText('Cancelado', { exact: true })).toHaveCount(0)
      expect(api.cancelPosts).toHaveLength(1)
      await expect.poll(() => api.count(MINE)).toBe(refetches ? 2 : 1)
    })
  }

  test('o 409 neutro não menciona lance, hash nem âncora', async ({ page }) => {
    await mockApi(page, owner('integrity'))
    await openList(page)
    await startCancel(page)
    await confirm(page)

    const alert = page.getByRole('alert')
    await expect(alert).toHaveText(NEUTRAL_409)
    await expect(alert).not.toContainText(/lance|hash|HMAC|âncora/i)
  })

  test('401: leva ao login com o aviso de sessão expirada', async ({ page }) => {
    await mockApi(page, owner('unauthorized'))
    await openList(page)
    await startCancel(page)
    await confirm(page)

    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByText('Sua sessão expirou. Entre novamente.')).toBeVisible()
  })
})

test.describe('erro ambíguo', () => {
  const modes: CancelMode[] = ['server_error', 'network', 'invalid_body']
  for (const mode of modes) {
    test(`${mode}: não afirma sucesso nem falha, relê uma vez e nunca reenvia`, async ({
      page,
    }) => {
      const api = await mockApi(page, owner(mode))
      await openList(page)
      await startCancel(page)
      await confirm(page)

      await expect(page.getByText(AMBIGUOUS)).toBeVisible()
      await expect(page.getByText('Lote cancelado.', { exact: true })).toHaveCount(0)
      await expect(page.getByRole('alert')).toHaveCount(0)
      await expect.poll(() => api.count(MINE)).toBe(2)
      // Nada de reenvio automático, nem depois de um tempo.
      await page.waitForTimeout(400)
      expect(api.cancelPosts).toHaveLength(1)
      expect(api.count(MINE)).toBe(2)
    })
  }

  test('o servidor chegou a gravar: a releitura mostra o selo, mas o aviso segue incerto', async ({
    page,
  }) => {
    await mockApi(page, owner('server_error', { cancelAppliedOnError: true }))
    await openList(page)
    await startCancel(page)
    await confirm(page)

    await expect(row(page, 1).getByText('Cancelado', { exact: true })).toBeVisible()
    await expect(page.getByText(AMBIGUOUS)).toBeVisible()
    await expect(page.getByText('Lote cancelado.', { exact: true })).toHaveCount(0)
  })

  test('ambíguo com a releitura também falha: texto próprio, sem loop', async ({ page }) => {
    const api = await mockApi(page, owner('network', { mineRereadFail: true }))
    await openList(page)
    await startCancel(page)
    await confirm(page)

    await expect(
      page.getByText(
        'Não foi possível confirmar o cancelamento nem atualizar a lista. Recarregue Meus lotes e confira antes de tentar novamente.',
      ),
    ).toBeVisible()
    await page.waitForTimeout(400)
    expect(api.cancelPosts).toHaveLength(1)
    expect(api.count(MINE)).toBe(2)
  })
})

test.describe('layout e toque', () => {
  test('alvos de toque de ~44 px e sem rolagem horizontal em 320 px com título longo', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 800 })
    await mockApi(page, {
      session: 'AUCTIONEER',
      myLots: [myLot(1, 'live', { title: LONG_TITLE }), myLot(2, 'scheduled')],
    })
    await page.goto(PATH)
    await expect(page.getByRole('heading', { name: 'Meus lotes' })).toBeVisible()

    const cta = page.getByRole('button', { name: /Cancelar lote/ }).first()
    const box = await cta.boundingBox()
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(43.5)
    await cta.click()
    for (const name of ['Cancelar lote', 'Voltar']) {
      const target = await page.getByRole('button', { name, exact: true }).boundingBox()
      expect(target?.height ?? 0).toBeGreaterThanOrEqual(43.5)
    }
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    expect(overflow).toBeLessThanOrEqual(0)
  })
})

for (const phase of ['live', 'scheduled'] as const) {
  test(`cancelar ${phase} com lances explica estorno, impede duplo envio e retira da Vitrine`, async ({ page }) => {
    const api = await mockApi(page, owner('ok', { cancelDelayMs: 500, lots: [makeLot(1, phase)], myLots: [myLot(1, phase, { bid_count: 3 })] }))
    await openList(page)
    await startCancel(page)
    const group = row(page, 1).getByRole('group')
    await expect(group).toContainText('Este lote possui lances. Ao cancelar, o saldo comprometido do licitante líder será liberado automaticamente.')
    await expect(group).not.toContainText(/Licitante-|@/)
    await group.getByRole('button', { name: 'Cancelar lote', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Cancelando…' })).toBeDisabled()
    await page.keyboard.press('Enter')
    await expect(row(page, 1).getByText('Cancelado', { exact: true })).toBeVisible()
    await expect(row(page, 1).getByText('3 lances')).toBeVisible()
    expect(api.cancelPosts).toEqual([TARGET])
    await page.getByRole('link', { name: 'Vitrine', exact: true }).click()
    await expect(page.getByText('Obra de teste 1', { exact: true })).toHaveCount(0)
  })
}

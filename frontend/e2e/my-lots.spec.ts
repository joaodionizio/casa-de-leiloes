// Meus lotes e o cancelamento (Story 3.6): o que o navegador faz com a lista do dono e
// com as respostas do `POST /api/lots/{id}/cancel`. As regras do cancelamento (dono,
// gate, lances, fim, concorrência) são do back-end e têm testes em PostgreSQL real; aqui
// se prova DOM, foco, teclado e a contagem de pedidos contra a API simulada.
import { expect, test, type Page } from '@playwright/test'
import {
  CANCELLED_AT,
  LONG_TITLE,
  lotId,
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
  await page.getByRole('button', { name: 'Confirmar cancelamento' }).click()
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

    await expect(page.getByRole('button', { name: /Cancelar lote/ })).toHaveCount(2)
    await expect(row(page, 1).getByRole('button', { name: /Cancelar lote/ })).toBeVisible()
    await expect(row(page, 2).getByRole('button', { name: /Cancelar lote/ })).toBeVisible()
    for (const n of [3, 4, 5, 6]) {
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

test.describe('confirmação inline', () => {
  test('o clique abre a confirmação na linha, com foco no botão; Voltar devolve o foco ao CTA', async ({
    page,
  }) => {
    const api = await mockApi(page, owner())
    await openList(page)

    await startCancel(page)

    const confirmation = row(page, 1).getByRole('group')
    await expect(confirmation).toContainText('O lote sai da vitrine e não pode ser reaberto.')
    await expect(page.getByRole('button', { name: 'Confirmar cancelamento' })).toBeFocused()
    // Só uma confirmação por vez e nenhum pedido ainda.
    await expect(page.getByRole('button', { name: 'Confirmar cancelamento' })).toHaveCount(1)
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
    await expect(page.getByRole('button', { name: 'Confirmar cancelamento' })).toBeFocused()
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

    const button = page.getByRole('button', { name: 'Confirmar cancelamento' })
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
    ['has_bids', 'Este lote não pode ser cancelado porque já recebeu lances.', true],
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
    for (const name of ['Confirmar cancelamento', 'Voltar']) {
      const target = await page.getByRole('button', { name }).boundingBox()
      expect(target?.height ?? 0).toBeGreaterThanOrEqual(43.5)
    }
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    expect(overflow).toBeLessThanOrEqual(0)
  })
})

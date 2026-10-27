// Sala do lote (Story 3.5): comportamento da interface contra a API simulada. As regras
// do lance (mínimo, saldo, concorrência) são do back-end e já têm testes em PostgreSQL
// real; aqui se prova o que o navegador faz com as respostas.
import { expect, test, type Page } from '@playwright/test'
import {
  ALIASES,
  LONG_TITLE,
  OTHER_ALIAS,
  OWN_ALIAS,
  lotId,
  makeBids,
  makeLot,
  makeLots,
  mockApi,
  type BidMode,
  type MockOptions,
} from './support/mockApi'

const LOTS = makeLots({ live: 2, scheduled: 1, ended: 1 })
const LOT = lotId(1)
const ROOM = `GET /api/lots/${LOT}/bids`
const MINE = `GET /api/lots/${LOT}/bids/mine`
const PASSWORD = 'Demo123!'

function bidder(options: MockOptions = {}): MockOptions {
  return {
    lots: LOTS,
    session: 'BIDDER',
    wallet: { total: 500_000, committed: 0 },
    ...options,
  }
}

async function openRoom(page: Page, id = LOT) {
  await page.goto(`/lots/${id}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote' })).toBeVisible()
}

async function bidAmount(page: Page, amount: string) {
  await page.getByLabel('Valor do lance').fill(amount)
  await page.getByRole('button', { name: 'Dar lance' }).click()
}

async function leaveAndReturn(page: Page) {
  await page.getByRole('link', { name: 'Vitrine' }).first().click()
  await page.goBack()
}

async function signIn(page: Page, email: string) {
  await page.getByLabel('E-mail').fill(email)
  await page.getByLabel('Senha').fill(PASSWORD)
  await page.getByRole('button', { name: 'Entrar' }).click()
}

test.describe('papéis', () => {
  test('visitante vê a sala sem formulário nem chamadas privadas e volta ao lote após entrar', async ({
    page,
  }) => {
    const api = await mockApi(page, { lots: LOTS })
    await openRoom(page)

    await expect(page.getByRole('button', { name: 'Dar lance' })).toHaveCount(0)
    await expect(page.getByLabel('Valor do lance')).toHaveCount(0)
    expect(api.count(MINE)).toBe(0)
    expect(api.count('GET /api/wallet')).toBe(0)

    await page.getByRole('link', { name: 'Entrar para dar lance' }).click()
    await expect(page).toHaveURL(/\/login$/)
    await signIn(page, 'bidder1@example.com')
    await expect(page).toHaveURL(new RegExp(`/lots/${LOT}$`))
    await expect(page.getByRole('button', { name: 'Dar lance' })).toBeVisible()
  })

  test('leiloeiro vê a sala sem formulário nem chamadas privadas', async ({ page }) => {
    const api = await mockApi(page, { lots: LOTS, session: 'AUCTIONEER' })
    await openRoom(page)

    await expect(
      page.getByText('Sua conta é de leiloeiro: você acompanha o lote, mas não dá lances.'),
    ).toBeVisible()
    await expect(page.getByRole('button', { name: 'Dar lance' })).toHaveCount(0)
    expect(api.count(MINE)).toBe(0)
    expect(api.count('GET /api/wallet')).toBe(0)
  })

  test('licitante vê formulário, saldo disponível e a hora do /bids', async ({ page }) => {
    await mockApi(page, bidder())
    await openRoom(page)

    await expect(page.getByLabel('Valor do lance')).toBeVisible()
    await expect(page.getByText('Saldo disponível:')).toContainText('R$ 5.000,00')
    // A hora vem do `as_of` de /bids (segundos :07), não do detalhe (14:30:00).
    await expect(page.getByText(/Situação atualizada às \d\d:\d\d:07/)).toBeVisible()
    await page.getByRole('button', { name: 'Atualizar sala' }).click()
    await expect(page.getByText(/Situação atualizada às \d\d:\d\d:08/)).toBeVisible()
  })
})

test.describe('lance', () => {
  test('aceito: valor, carteira e sucesso imediatos; depois histórico e posição', async ({
    page,
  }) => {
    await mockApi(page, bidder({ rereadDelayMs: 700 }))
    await openRoom(page)

    await bidAmount(page, '110,00')

    // Antes da releitura (atrasada): dados seguros do 201.
    await expect(page.getByText('Lance de R$ 110,00 registrado.')).toBeVisible()
    await expect(page.locator('.bid-current')).toHaveText('R$ 110,00')
    await expect(page.getByText('Saldo disponível:')).toContainText('R$ 4.890,00')
    await expect(page.getByText('Atualizando…').first()).toBeVisible()
    // Depois: mínimo, histórico e posição do servidor.
    await expect(page.locator('.bid-minimum')).toHaveText('R$ 120,00')
    await expect(page.locator('.bid-history-list li')).toHaveCount(1)
    await expect(page.locator('.bid-history-list')).toContainText('(Você)')
    await expect(page.getByText('✓ Você está ganhando')).toBeVisible()
    await expect(page.getByLabel('Valor do lance')).toHaveValue('')
  })

  test('anti-sniping: o prazo prorrogado aparece em fim, aviso e contagem', async ({ page }) => {
    await mockApi(page, bidder({ bid: 'anti_sniping' }))
    await openRoom(page)
    const before = await page.locator('.lot-page-when').innerText()

    await bidAmount(page, '110,00')

    await expect(page.getByText('Prazo prorrogado em 2 minutos.')).toBeVisible()
    await expect(page.locator('.lot-page-when')).not.toHaveText(before)
  })

  const refusals: Array<[BidMode, string]> = [
    ['below_minimum', 'Seu lance está abaixo do mínimo para este lote. Confira o valor mínimo acima.'],
    ['insufficient_balance', 'Saldo disponível insuficiente para este lance.'],
    ['already_winning', 'Você já está ganhando este lote.'],
    ['lot_not_started', 'Este lote ainda não começou.'],
    ['lot_ended', 'Este lote já foi encerrado.'],
    ['lot_cancelled', 'Este lote foi cancelado.'],
  ]
  for (const [mode, text] of refusals) {
    test(`recusa ${mode}: texto pelo code e valor mantido`, async ({ page }) => {
      const api = await mockApi(page, bidder({ bid: mode }))
      await openRoom(page)

      await bidAmount(page, '110,00')

      await expect(page.getByRole('alert').filter({ hasText: text })).toBeVisible()
      await expect(page.getByText('MENSAGEM DO SERVIDOR')).toHaveCount(0)
      await expect(page.getByLabel('Valor do lance')).toHaveValue('110,00')
      expect(api.bidPosts).toHaveLength(1)
      // Uma única releitura de sincronização, sem novo POST.
      await expect.poll(() => api.count(ROOM)).toBe(2)
    })
  }

  test('integridade: recusa própria, sem expor a causa', async ({ page }) => {
    await mockApi(page, bidder({ bid: 'integrity' }))
    await openRoom(page)
    await bidAmount(page, '110,00')
    await expect(
      page.getByText('Não foi possível verificar a integridade deste lote. O lance não foi registrado.'),
    ).toBeVisible()
  })

  test('abaixo do mínimo e acima do saldo chegam ao servidor; formato inválido não', async ({
    page,
  }) => {
    const api = await mockApi(page, bidder({ bid: 'below_minimum' }))
    await openRoom(page)

    await bidAmount(page, '0,01')
    await expect.poll(() => api.bidPosts.length).toBe(1)
    await bidAmount(page, '999.999,00')
    await expect.poll(() => api.bidPosts.length).toBe(2)
    await bidAmount(page, 'abc')
    await expect(page.getByLabel('Valor do lance')).toHaveAttribute('aria-invalid', 'true')

    expect(api.bidPosts.map((item) => item.body)).toEqual([
      { amount_cents: 1 },
      { amount_cents: 99_999_900 },
    ])
  })

  test('envio pendente: um só POST, botões desabilitados e volta ao normal', async ({ page }) => {
    const api = await mockApi(page, bidder({ bidDelayMs: 800 }))
    await openRoom(page)

    await page.getByLabel('Valor do lance').fill('110,00')
    await page.getByLabel('Valor do lance').press('Enter')
    await expect(page.getByRole('button', { name: 'Enviando lance…' })).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Atualizar sala' })).toBeDisabled()
    await page.getByLabel('Valor do lance').press('Enter')

    await expect(page.getByText('Lance de R$ 110,00 registrado.')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Atualizar sala' })).toBeEnabled()
    expect(api.bidPosts).toHaveLength(1)
  })

  test('sair e voltar durante o envio acompanha o mesmo POST', async ({ page }) => {
    const api = await mockApi(page, bidder({ bidDelayMs: 1_000 }))
    await openRoom(page)
    await bidAmount(page, '110,00')

    await page.getByRole('link', { name: 'Vitrine' }).first().click()
    await page.goBack()

    await expect(page.getByRole('button', { name: 'Enviando lance…' })).toBeDisabled()
    await expect(page.getByText('Lance de R$ 110,00 registrado.')).toBeVisible()
    expect(api.bidPosts).toHaveLength(1)
  })

  test('erro ambíguo: texto neutro, valor mantido, uma releitura e nenhum reenvio', async ({
    page,
  }) => {
    const api = await mockApi(page, bidder({ bid: 'network', bidAppliedOnError: true }))
    await openRoom(page)

    await bidAmount(page, '110,00')

    const neutral = page.getByText(/Não foi possível confirmar o lance\. O estado abaixo/)
    await expect(neutral).toBeVisible()
    await expect(page.getByText(/registrado/)).toHaveCount(0)
    await expect(page.getByLabel('Valor do lance')).toHaveValue('110,00')
    expect(api.bidPosts).toHaveLength(1)
    expect(api.count(ROOM)).toBe(2)
  })

  test('erro ambíguo com releitura falha não afirma o estado atual', async ({ page }) => {
    await mockApi(page, bidder({ bid: 'server_error', rereadFail: 'all' }))
    await openRoom(page)
    await bidAmount(page, '110,00')
    await expect(
      page.getByText(/nem atualizar todos os dados da sala\. Use Atualizar sala/),
    ).toBeVisible()
    await expect(page.getByText(/estado abaixo é o atual/)).toHaveCount(0)
  })

  test('201 inválido é ambíguo', async ({ page }) => {
    await mockApi(page, bidder({ bid: 'invalid201' }))
    await openRoom(page)
    await bidAmount(page, '110,00')
    await expect(page.getByText(/Não foi possível confirmar o lance/)).toBeVisible()
  })

  test('aceito, mas a releitura falha: mantém o sucesso e avisa', async ({ page }) => {
    await mockApi(page, bidder({ rereadFail: 'room' }))
    await openRoom(page)
    await bidAmount(page, '110,00')

    await expect(page.getByText('Lance de R$ 110,00 registrado.')).toBeVisible()
    await expect(page.getByText('Lance aceito, mas não foi possível atualizar a sala.')).toBeVisible()
    await expect(page.getByText('Mínimo indisponível')).toBeVisible()
    await expect(page.locator('.bid-current')).toHaveText('R$ 110,00')
  })
})

test.describe('contagem', () => {
  const CLOSE = { [LOT]: { ends_at: '2026-10-25T12:00:10.000Z' } }

  test('zero faz uma única releitura por fim e não bloqueia o lance', async ({ page }) => {
    await page.clock.install()
    const api = await mockApi(page, bidder({ rooms: CLOSE }))
    await openRoom(page)
    await expect(page.getByRole('timer')).toHaveText('00:03')

    await page.clock.runFor(4_000)

    await expect(page.getByText('Confirmando encerramento com o servidor…')).toBeVisible()
    await expect(page.getByRole('timer')).toHaveText('0:00')
    await expect(page.getByRole('button', { name: 'Dar lance' })).toBeEnabled()
    await expect.poll(() => api.count(ROOM)).toBe(2)
    await page.clock.runFor(60_000)
    expect(api.count(ROOM)).toBe(2)
  })

  test('snapshot encerrado remove o formulário; Atualizar sala faz uma rodada', async ({
    page,
  }) => {
    await page.clock.install()
    const api = await mockApi(
      page,
      bidder({ rooms: { [LOT]: { ends_at: '2026-10-25T12:00:10.000Z', script: [{}, { phase: 'ended' }] } } }),
    )
    await openRoom(page)
    await page.clock.runFor(4_000)

    await expect(page.getByText('Encerrado, apurando resultado').first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Dar lance' })).toHaveCount(0)

    const before = api.count(ROOM)
    await page.getByRole('button', { name: 'Atualizar sala' }).click()
    await expect.poll(() => api.count(ROOM)).toBe(before + 1)
  })
})

test.describe('remontagem com envio pendente', () => {
  test('o 201 chega antes do detalhe: aceite visível e a sala não fica presa', async ({
    page,
  }) => {
    const api = await mockApi(page, bidder({ bidDelayMs: 600 }))
    await openRoom(page)
    await bidAmount(page, '110,00')

    const detail = api.hold(`GET /api/lots/${LOT}`)
    await leaveAndReturn(page)
    await expect(page.getByRole('heading', { name: 'Carregando lote…' })).toBeVisible()
    await expect.poll(() => api.bidResponses).toBe(1)
    await page.waitForTimeout(300)
    detail.release()

    await expect(page.getByText('Lance de R$ 110,00 registrado.')).toBeVisible()
    await expect(page.getByText('Carregando sala…')).toHaveCount(0)
    await expect(page.locator('.bid-current')).toHaveText('R$ 110,00')
    await expect(page.locator('.bid-minimum')).toHaveText('R$ 120,00')
    await expect(page.getByText('✓ Você está ganhando')).toBeVisible()
    expect(api.bidPosts).toHaveLength(1)
  })

  test('detalhe pronto, sala pendente e releitura pública falha: o aceite continua', async ({
    page,
  }) => {
    const api = await mockApi(page, bidder({ bidDelayMs: 600 }))
    await openRoom(page)
    await bidAmount(page, '110,00')

    const room = api.hold(ROOM)
    await leaveAndReturn(page)
    await expect(page.getByText('Carregando sala…')).toBeVisible()
    await expect.poll(() => api.bidResponses).toBe(1)
    await page.waitForTimeout(300)
    room.fail()

    await expect(page.getByText('Lance de R$ 110,00 registrado.')).toBeVisible()
    await expect(page.getByText('Lance aceito, mas não foi possível atualizar a sala.')).toBeVisible()
    await expect(page.locator('.bid-current')).toHaveText('R$ 110,00')
    await expect(page.getByText('Saldo disponível:')).toContainText('R$ 4.890,00')
    await expect(page.getByText('Não foi possível carregar a sala do lote.')).toHaveCount(0)
  })
})

test.describe('rodadas de leitura', () => {
  const CLOSE = { [LOT]: { ends_at: '2026-10-25T12:00:10.000Z' } }

  test('atualização manual atravessa o zero: uma só rodada e nenhuma falha residual', async ({
    page,
  }) => {
    await page.clock.install()
    const api = await mockApi(page, bidder({ rooms: CLOSE }))
    await openRoom(page)
    expect(api.count(ROOM)).toBe(1)

    const room = api.hold(ROOM)
    await page.getByRole('button', { name: 'Atualizar sala' }).click()
    await expect(page.getByRole('button', { name: 'Atualizando…' })).toBeVisible()
    await page.clock.runFor(4_000)
    await expect(page.getByText('Confirmando encerramento com o servidor…')).toBeVisible()
    room.release()

    await expect(page.getByRole('button', { name: 'Atualizar sala' })).toBeEnabled()
    await page.clock.runFor(60_000)
    expect(api.count(ROOM)).toBe(2)
    await expect(page.getByText('Histórico possivelmente desatualizado.')).toHaveCount(0)
    await expect(page.getByText(/Não foi possível confirmar o encerramento/)).toHaveCount(0)
  })

  test('falha da leitura do zero sai de Confirmando, avisa e não repete sozinha', async ({
    page,
  }) => {
    await page.clock.install()
    const api = await mockApi(page, bidder({ rooms: CLOSE }))
    await openRoom(page)

    const room = api.hold(ROOM)
    await page.clock.runFor(4_000)
    await expect(page.getByText('Confirmando encerramento com o servidor…')).toBeVisible()
    room.fail()

    await expect(
      page.getByRole('alert').filter({ hasText: 'Não foi possível confirmar o encerramento' }),
    ).toBeVisible()
    await expect(page.getByText('Confirmando encerramento com o servidor…')).toHaveCount(0)
    await page.clock.runFor(60_000)
    expect(api.count(ROOM)).toBe(2)

    await page.getByRole('button', { name: 'Atualizar sala' }).click()
    await expect.poll(() => api.count(ROOM)).toBe(3)
    await expect(page.getByText(/Não foi possível confirmar o encerramento/)).toHaveCount(0)
  })

  test('o zero durante o envio não abre leitura; a rodada pós-POST é a única', async ({
    page,
  }) => {
    await page.clock.install()
    const api = await mockApi(page, bidder({ rooms: CLOSE }))
    await openRoom(page)

    const post = api.hold(`POST /api/lots/${LOT}/bids`)
    await bidAmount(page, '110,00')
    await page.clock.runFor(4_000)
    await expect(page.getByRole('timer')).toHaveText('0:00')
    expect(api.count(ROOM)).toBe(1)
    post.release()

    await expect(page.getByText('Lance de R$ 110,00 registrado.')).toBeVisible()
    await expect.poll(() => api.count(ROOM)).toBe(2)
    await page.clock.runFor(60_000)
    expect(api.count(ROOM)).toBe(2)
    expect(api.bidPosts).toHaveLength(1)
  })

  test('anti-sniping: a contagem usa o novo fim antes da releitura', async ({ page }) => {
    await page.clock.install()
    const api = await mockApi(page, bidder({ rooms: CLOSE, bid: 'anti_sniping' }))
    await openRoom(page)
    await expect(page.getByRole('timer')).toHaveText('00:03')

    const room = api.hold(ROOM)
    await bidAmount(page, '110,00')

    // Fim prorrogado (12:02:10) menos o instante do lance (12:00:09): 2 min 1 s.
    await expect(page.getByText('Prazo prorrogado em 2 minutos.')).toBeVisible()
    await expect(page.getByRole('timer')).toHaveText('02:01')
    await page.clock.runFor(1_000)
    await expect(page.getByRole('timer')).toHaveText('02:00')
    room.release()
    await expect(page.locator('.bid-minimum')).toHaveText('R$ 120,00')
  })
})

test.describe('posição e participação', () => {
  const MINE_FAILED = 'Não foi possível carregar sua participação.'
  const POSITION = /Você (está|foi)/

  test('sala nova com /mine pendente ou falho: posição indisponível, nunca a antiga', async ({
    page,
  }) => {
    const bids = makeBids(2, 11_000, [OWN_ALIAS, OTHER_ALIAS])
    const api = await mockApi(page, bidder({ rooms: { [LOT]: { bids } } }))
    await openRoom(page)
    await expect(page.getByText('↑ Você foi superado')).toBeVisible()

    api.setBids(LOT, makeBids(3, 11_000, [OWN_ALIAS, OTHER_ALIAS]))
    const mine = api.hold(MINE)
    await page.getByRole('button', { name: 'Atualizar sala' }).click()
    await expect(page.locator('.bid-history-list li')).toHaveCount(3)
    await expect(page.getByText(POSITION)).toHaveCount(0)
    await expect(page.getByText(MINE_FAILED)).toHaveCount(0)

    mine.fail()
    await expect(page.getByText(MINE_FAILED)).toBeVisible()
    await expect(page.getByText(POSITION)).toHaveCount(0)
    // O pseudônimo, que não muda, continua visível.
    await expect(page.getByText('Seu pseudônimo neste lote:')).toContainText(OWN_ALIAS)

    await page.getByRole('button', { name: 'Atualizar sala' }).click()
    await expect(page.getByText('✓ Você está ganhando')).toBeVisible()
    await expect(page.getByText(MINE_FAILED)).toHaveCount(0)
  })

  test('/mine responde antes da sala: a posição espera o par da mesma rodada', async ({
    page,
  }) => {
    const bids = makeBids(2, 11_000, [OWN_ALIAS, OTHER_ALIAS])
    const api = await mockApi(page, bidder({ rooms: { [LOT]: { bids } } }))
    await openRoom(page)
    await expect(page.getByText('↑ Você foi superado')).toBeVisible()

    api.setBids(LOT, makeBids(3, 11_000, [OWN_ALIAS, OTHER_ALIAS]))
    const room = api.hold(ROOM)
    await page.getByRole('button', { name: 'Atualizar sala' }).click()
    await expect.poll(() => api.count(MINE)).toBe(2)
    await page.waitForTimeout(300)
    await expect(page.getByText(POSITION)).toHaveCount(0)
    await expect(page.locator('.bid-history-list li')).toHaveCount(2)

    room.release()
    await expect(page.getByText('✓ Você está ganhando')).toBeVisible()
    await expect(page.locator('.bid-history-list li')).toHaveCount(3)
  })

  test('sem lance próprio, o pseudônimo da conta aparece no painel', async ({ page }) => {
    await mockApi(page, bidder({ rooms: { [LOT]: { bids: makeBids(1, 11_000, [OTHER_ALIAS]) } } }))
    await openRoom(page)
    await expect(page.getByText('Seu pseudônimo neste lote:')).toHaveText(
      `Seu pseudônimo neste lote: ${OWN_ALIAS}`,
    )
    await expect(page.getByText(POSITION)).toHaveCount(0)
  })

  test('lote encerrado: último lance próprio fora dos 50 exibidos, sem afirmar resultado', async ({
    page,
  }) => {
    const bids = makeBids(51, 11_000, [OTHER_ALIAS])
    bids[0] = { ...bids[0], bidder_alias: OWN_ALIAS }
    await mockApi(page, bidder({ rooms: { [lotId(201)]: { bids } } }))
    await openRoom(page, lotId(201))

    await expect(page.getByText('Seu último lance:')).toHaveText('Seu último lance: R$ 110,00')
    await expect(page.getByText('Encerrado, apurando resultado').first()).toBeVisible()
    await expect(page.getByLabel('Valor do lance')).toHaveCount(0)
    await expect(page.locator('.bid-history-list')).not.toContainText(OWN_ALIAS)
    const text = await page.locator('.bid-panel').innerText()
    expect(text).not.toMatch(/vencedor|arremat|venceu|ganhou|vitória/i)
  })

  test('lote encerrado sem lance próprio não mostra último lance', async ({ page }) => {
    await mockApi(page, bidder({ rooms: { [lotId(201)]: { bids: makeBids(2, 11_000, [OTHER_ALIAS]) } } }))
    await openRoom(page, lotId(201))
    await expect(page.getByText('Seu pseudônimo neste lote:')).toBeVisible()
    await expect(page.getByText('Seu último lance:')).toHaveCount(0)
  })
})

test.describe('posição e histórico', () => {
  test('superado com o lance próprio fora dos 50 exibidos', async ({ page }) => {
    const bids = makeBids(51, 11_000, [OTHER_ALIAS])
    bids[0] = { ...bids[0], bidder_alias: OWN_ALIAS }
    await mockApi(page, bidder({ rooms: { [LOT]: { bids } } }))
    await openRoom(page)

    await expect(page.getByText('↑ Você foi superado')).toBeVisible()
    await expect(page.getByText('50 mais recentes de 51')).toBeVisible()
    await expect(page.locator('.bid-history-list li')).toHaveCount(50)
    await expect(page.locator('.bid-history-list li').first()).toContainText('#51')
  })

  test('ganhando e neutro', async ({ page }) => {
    await mockApi(page, bidder({ rooms: { [LOT]: { bids: makeBids(2, 11_000, [OTHER_ALIAS, OWN_ALIAS]) } } }))
    await openRoom(page)
    await expect(page.getByText('✓ Você está ganhando')).toBeVisible()
    await expect(page.getByText('Nenhum lance ainda.')).toHaveCount(0)
  })

  test('sem lances: lance inicial, histórico vazio e sem posição', async ({ page }) => {
    await mockApi(page, bidder())
    await openRoom(page)
    await expect(page.getByText('Nenhum lance ainda.')).toBeVisible()
    await expect(page.getByText('Sem lances ainda')).toBeVisible()
    await expect(page.getByText(/Você (está|foi)/)).toHaveCount(0)
  })

  test('privacidade: só pseudônimos na sala', async ({ page }) => {
    await mockApi(page, bidder({ rooms: { [LOT]: { bids: makeBids(3, 11_000) } } }))
    await openRoom(page)
    const text = await page.locator('.lot-page').innerText()
    expect(text).not.toMatch(/@/)
    expect(text).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}/)
    expect(text).toContain(ALIASES['bidder2@example.com'])
  })
})

test.describe('sessão', () => {
  for (const [label, options] of [
    ['POST', { bid: 'unauthorized' as BidMode }],
    ['/mine', { privateRead401: 'mine' as const }],
    ['carteira', { privateRead401: 'wallet' as const }],
  ] as const) {
    test(`401 em ${label}: login com aviso e volta ao mesmo lote`, async ({ page }) => {
      await mockApi(page, bidder(options))
      await page.goto(`/lots/${LOT}`)
      if (label === 'POST') {
        await bidAmount(page, '110,00')
      }
      await expect(page).toHaveURL(/\/login$/)
      await expect(page.getByText('Sua sessão expirou. Entre novamente.')).toBeVisible()
      await signIn(page, 'bidder1@example.com')
      await expect(page).toHaveURL(new RegExp(`/lots/${LOT}$`))
    })
  }
})

test.describe('layout', () => {
  for (const width of [320, 1280]) {
    test(`${width}px: sem overflow, painel antes do histórico, alvos de 44 px`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 800 })
      const long = makeLot(1, 'live', { title: LONG_TITLE })
      await mockApi(
        page,
        bidder({
          lots: [long],
          images: 'broken',
          rooms: { [LOT]: { bids: makeBids(51, 11_000) } },
        }),
      )
      await openRoom(page)

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      )
      expect(overflow).toBeLessThanOrEqual(0)
      const panel = await page.locator('.bid-panel').boundingBox()
      const history = await page.locator('.bid-history').boundingBox()
      expect(panel).not.toBeNull()
      expect(history).not.toBeNull()
      expect(history!.y).toBeGreaterThan(panel!.y)
      for (const name of ['Dar lance', 'Atualizar sala']) {
        const box = await page.getByRole('button', { name }).boundingBox()
        expect(box!.height).toBeGreaterThanOrEqual(43.5)
      }
    })
  }
})

test.describe('hierarquia no celular (320 px)', () => {
  test('estado e prazo, obra, título, painel e histórico, nessa ordem e com um só timer', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 800 })
    await mockApi(page, bidder({ rooms: { [LOT]: { bids: makeBids(3, 11_000) } } }))
    await openRoom(page)

    const top = async (selector: string) => {
      const box = await page.locator(selector).first().boundingBox()
      expect(box, selector).not.toBeNull()
      return box!
    }
    const status = await top('.lot-page-status')
    const art = await top('.lot-page-art')
    const title = await top('#lot-title')
    const panel = await top('.bid-panel')
    const history = await top('.bid-history')

    expect(status.y + status.height).toBeLessThanOrEqual(art.y + 0.5)
    expect(art.y + art.height).toBeLessThanOrEqual(title.y + 0.5)
    expect(title.y).toBeLessThan(panel.y)
    expect(panel.y + panel.height).toBeLessThanOrEqual(history.y + 0.5)
    await expect(page.getByRole('timer')).toHaveCount(1)
    await expect(page.getByRole('timer')).toBeVisible()
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    )
    expect(overflow).toBeLessThanOrEqual(0)
  })
})


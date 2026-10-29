import { expect, test, type Page, type WebSocketRoute } from '@playwright/test'
import { HELP } from '../src/contextHelpText'
import { AS_OF, OWN_ALIAS, OTHER_ALIAS, lotId, makeBids, makeLot, mockApi, type MockBid } from './support/mockApi'

const ID = lotId(1)
const lot = makeLot(1, 'live')
const contextual = 'Seu saldo disponível no momento também é menor que o próximo lance mínimo.'

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
}

for (const system of ['light', 'dark'] as const) {
  test(`tema segue sistema ${system}; escolha manual persiste em reload, History API e nova aba`, async ({ page, context }) => {
    await page.emulateMedia({ colorScheme: system })
    await mockApi(page, { lots: [lot] })
    await page.goto('/')
    await expect(page.locator('html')).toHaveAttribute('data-theme', system)
    const opposite = system === 'dark' ? 'light' : 'dark'
    const button = page.getByRole('button', { name: system === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro' })
    await button.focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('html')).toHaveAttribute('data-theme', opposite)
    expect(await page.evaluate(() => localStorage.getItem('atrio-theme'))).toBe(opposite)
    await page.reload()
    await expect(page.locator('html')).toHaveAttribute('data-theme', opposite)
    await page.getByRole('link', { name: 'Entrar', exact: true }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', opposite)
    await page.goBack()
    await expect(page.locator('html')).toHaveAttribute('data-theme', opposite)
    const another = await context.newPage()
    await mockApi(another)
    await another.goto('/')
    await expect(another.locator('html')).toHaveAttribute('data-theme', opposite)
    await another.close()
  })
}

test('preferência manual sobrevive a login/logout e alterna nos dois sentidos', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light', reducedMotion: 'reduce' })
  await mockApi(page)
  await page.goto('/login')
  await page.getByRole('button', { name: 'Ativar modo escuro' }).click()
  await page.getByRole('button', { name: 'Entrar como Licitante 1', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Sair', exact: true })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('button', { name: 'Sair', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Entrar', exact: true })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('button', { name: 'Ativar modo claro' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  expect(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)).toBe(true)
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual(['atrio-theme'])
})

test('storage indisponível ou inválido não impede sistema/toggle', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => { throw new Error('storage unavailable') }
    Storage.prototype.setItem = () => { throw new Error('storage unavailable') }
  })
  await mockApi(page)
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('button', { name: 'Ativar modo claro' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
})

test('preferência salva inválida segue o sistema antes de React montar', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.addInitScript(() => localStorage.setItem('atrio-theme', 'invalid'))
  await mockApi(page)
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
})

for (const theme of ['light', 'dark'] as const) {
  for (const width of [1440, 375, 320]) {
    test(`footer e contraste de tokens ${theme} ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await page.emulateMedia({ colorScheme: theme })
      await mockApi(page, { lots: [lot] })
      await page.goto('/')
      const footer = page.locator('footer')
      await expect(footer.getByRole('heading', { name: 'O projeto', exact: true })).toBeVisible()
      await expect(footer.getByText('© 2026 ÁTRIO — Leilões de Arte', { exact: true })).toBeVisible()
      await expect(footer.getByText('Desenvolvido por João Luís Dionízio — Desafio Elite Dev — Verzel', { exact: true })).toBeVisible()
      await expect(footer.getByText('Leilões de arte em domínio público, em tempo real.', { exact: true })).toBeVisible()
      await expect(footer.locator('.site-footer-disclaimer')).toHaveText('Leilões, saldos, depósitos e transações são simulados — este é um projeto de demonstração, não uma plataforma comercial em operação.')
      await expect(footer.getByRole('status')).toHaveText('Serviço no ar')
      const source = footer.getByRole('link', { name: 'Código-fonte', exact: true })
      await expect(source).toHaveAttribute('href', 'https://github.com/joaodionizio/casa-de-leiloes')
      await expect(footer.getByRole('link', { name: /Acervo artístico/ })).toHaveAttribute('href', 'https://www.artic.edu/collection')
      for (const link of await footer.getByRole('link').all()) {
        await expect(link).toHaveAttribute('rel', 'noopener noreferrer')
        await link.focus()
        expect(await link.evaluate(element => parseFloat(getComputedStyle(element).outlineWidth))).toBeGreaterThanOrEqual(2)
      }
      expect(await footer.locator('a').count()).toBe(2)
      await noOverflow(page)
      // Text/status tokens must be readable on both page and raised surfaces.
      const contrasts = await page.evaluate(() => {
        const styles = getComputedStyle(document.documentElement)
        const luminance = (token: string) => {
          let hex = styles.getPropertyValue(token).trim().slice(1)
          if (hex.length === 3) hex = [...hex].map(char => char + char).join('')
          const channels = [0, 2, 4].map(index => parseInt(hex.slice(index, index + 2), 16) / 255).map(c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4)
          return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722
        }
        const pairs = ['--color-text', '--color-muted', '--color-brand-strong', '--color-success', '--color-warning', '--color-danger'].flatMap(fg => ['--color-canvas', '--color-surface', '--color-surface-subtle'].map(bg => [fg, bg]))
        pairs.push(['--color-on-action', '--color-action'], ['--color-on-action', '--color-action-hover'])
        return pairs.map(([fg, bg]) => {
          const a = luminance(fg), b = luminance(bg)
          return { fg, bg, ratio: (Math.max(a, b) + .05) / (Math.min(a, b) + .05) }
        })
      })
      for (const pair of contrasts) expect(pair.ratio, `${theme} ${pair.fg}/${pair.bg}`).toBeGreaterThanOrEqual(4.5)
    })
  }
}

for (const theme of ['light', 'dark'] as const) {
  test(`ajuda ${theme}: exclusividade A → B → C, teclado, foco, Escape, click e 320px`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: theme })
    await page.setViewportSize({ width: 320, height: 812 })
    const api = await mockApi(page, { session: 'BIDDER', wallet: { total: 50000, committed: 10000 } })
    await page.goto('/bidder/wallet')
    const total = page.getByRole('button', { name: 'Ajuda: Saldo total', exact: true })
    const committed = page.getByRole('button', { name: 'Ajuda: Saldo comprometido', exact: true })
    await expect(total).toHaveAttribute('aria-expanded', 'false')
    const id = await total.getAttribute('aria-controls')
    expect(id).toBeTruthy()
    await total.focus(); await page.keyboard.press('Enter')
    await expect(total).toHaveAttribute('aria-expanded', 'true')
    await expect(page.getByText(HELP.total, { exact: true })).toBeVisible()
    await committed.click()
    await expect(page.getByText(HELP.committed, { exact: true })).toBeVisible()
    await expect(page.getByText(HELP.total, { exact: true })).not.toBeVisible()
    await expect(total).toHaveAttribute('aria-expanded', 'false')
    await expect(committed).toHaveAttribute('aria-expanded', 'true')
    await expect(page.locator('.context-help-text:visible')).toHaveCount(1)
    const available = page.getByRole('button', { name: 'Ajuda: Saldo disponível', exact: true })
    await available.click()
    await expect(committed).toHaveAttribute('aria-expanded', 'false')
    await expect(page.getByText(HELP.committed, { exact: true })).not.toBeVisible()
    await expect(available).toHaveAttribute('aria-expanded', 'true')
    await expect(page.locator('.context-help-text:visible')).toHaveCount(1)
    await available.click()
    await expect(available).toHaveAttribute('aria-expanded', 'false')
    await expect(page.locator('.context-help-text:visible')).toHaveCount(0)
    await committed.focus()
    await page.keyboard.press('Space')
    await expect(committed).toHaveAttribute('aria-expanded', 'true')
    await page.keyboard.press('Escape')
    await expect(committed).toBeFocused()
    await expect(committed).toHaveAttribute('aria-expanded', 'false')
    await expect(total).toHaveAttribute('aria-expanded', 'false')
    await expect(page.locator('.context-help-text:visible')).toHaveCount(0)
    await available.click()
    await expect(page.getByText(HELP.available, { exact: true })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
    for (const trigger of [total, committed, available]) {
      const contentId = await trigger.getAttribute('aria-controls')
      expect(await page.locator('[id]').evaluateAll((elements, id) => elements.filter(element => element.id === id).length, contentId)).toBe(1)
    }
    await available.focus()
    expect(await available.evaluate(element => parseFloat(getComputedStyle(element).outlineWidth))).toBeGreaterThanOrEqual(2)
    await noOverflow(page)
    // A ajuda ativa desmonta por navegação real via History API.
    await page.getByRole('link', { name: 'ÁTRIO — Leilões de Arte — ir para a vitrine' }).click()
    await expect(page.locator('.context-help-text:visible')).toHaveCount(0)
    await page.goBack()
    await expect(total).toHaveAttribute('aria-expanded', 'false')
    await expect(page.locator('.context-help-text:visible')).toHaveCount(0)
    await total.click()
    await expect(total).toHaveAttribute('aria-expanded', 'true')
    await expect(page.locator('.context-help-text:visible')).toHaveCount(1)
    // Escape também fecha a ativa depois que o foco sai do trigger.
    await page.getByRole('button', { name: 'Depositar', exact: true }).focus()
    await page.keyboard.press('Escape')
    await expect(total).toHaveAttribute('aria-expanded', 'false')
    await expect(page.getByRole('button', { name: 'Depositar', exact: true })).toBeFocused()
    expect(api.requests.filter(item => item.startsWith('POST'))).toEqual([])
  })
}

test('ajuda aceita toque e fecha sem mutação', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 320, height: 812 }, hasTouch: true })
  try {
    const page = await context.newPage()
    await mockApi(page, { session: 'BIDDER' })
    await page.goto('http://127.0.0.1:4173/bidder/wallet')
    const help = page.getByRole('button', { name: 'Ajuda: Saldo total', exact: true })
    await help.tap(); await expect(page.getByText(HELP.total, { exact: true })).toBeVisible()
    const other = page.getByRole('button', { name: 'Ajuda: Saldo comprometido', exact: true })
    await other.tap()
    await expect(help).toHaveAttribute('aria-expanded', 'false')
    await expect(page.getByText(HELP.total, { exact: true })).not.toBeVisible()
    await expect(other).toHaveAttribute('aria-expanded', 'true')
    await expect(page.locator('.context-help-text:visible')).toHaveCount(1)
    await other.tap()
    await expect(other).toHaveAttribute('aria-expanded', 'false')
    await expect(page.locator('.context-help-text:visible')).toHaveCount(0)
    await noOverflow(page)
  } finally { await context.close() }
})

interface Room {
  as_of: string; phase: 'live' | 'ended'; ends_at: string
  current_bid_cents: number; minimum_next_bid_cents: number | null
  bid_count: number; bids: MockBid[]; settlement_status: 'pending'; settlement: null
}
function room(bids: MockBid[], extra: Partial<Room> = {}): Room {
  return { as_of: '2026-10-25T12:01:00.000000Z', phase: 'live', ends_at: lot.ends_at,
    current_bid_cents: bids.at(-1)!.amount_cents, minimum_next_bid_cents: bids.at(-1)!.amount_cents + 1000,
    bid_count: bids.length, bids: [...bids].reverse(), settlement_status: 'pending', settlement: null, ...extra }
}
async function leaderRoom(page: Page, options: { total?: number; failWallet?: boolean; outbid?: boolean; unknownMinimum?: boolean; refusal?: boolean } = {}) {
  let socket: WebSocketRoute | undefined
  let current = room(makeBids(options.outbid ? 2 : 1, 11000, [OWN_ALIAS, OTHER_ALIAS]), { minimum_next_bid_cents: options.unknownMinimum ? null : 12000 })
  await page.routeWebSocket('**/ws/lots/*', value => {
    socket = value
    value.onMessage(data => { const message = JSON.parse(String(data)); if (message.type === 'ping') value.send(JSON.stringify({ type: 'pong', id: message.id })) })
    value.send(JSON.stringify({ type: 'room_snapshot', lot_id: ID, room: current }))
  })
  const bids = [...current.bids].reverse()
  const api = await mockApi(page, { lots: [lot], session: 'BIDDER', wallet: { total: options.total ?? 20000, committed: 11000 }, rooms: { [ID]: { bids } }, bid: options.refusal ? 'already_winning' : 'accepted' })
  if (options.failWallet) await page.route('**/api/wallet', route => route.fulfill({ status: 503, json: { status: 503, code: 'internal_error' } }))
  await page.goto(`/lots/${ID}`)
  await expect(page.getByRole('heading', { name: 'Sala do lote', exact: true })).toBeVisible()
  await expect(page.getByText(/Sala conectada/)).toBeVisible()
  await expect(page.getByText(options.outbid ? '↑ Você foi superado' : '✓ Você está ganhando', { exact: true })).toBeVisible()
  return { api, update: (next: Room) => {
    current = next; api.setBids(ID, [...next.bids].reverse())
    socket!.send(JSON.stringify({ type: 'bid_accepted', lot_id: ID, room: next }))
  } }
}

for (const sample of [
  { name: 'winning + saldo suficiente', total: 100000, expected: false },
  { name: 'winning + saldo baixo no momento', total: 20000, expected: true },
  { name: 'outbid + saldo baixo', outbid: true, expected: false },
  { name: 'carteira falhou', failWallet: true, expected: false },
  { name: 'mínimo desconhecido', unknownMinimum: true, expected: false },
]) {
  test(`contexto do líder: ${sample.name}`, async ({ page }) => {
    const { api } = await leaderRoom(page, sample)
    await expect(page.getByText(contextual, { exact: true })).toHaveCount(sample.expected ? 1 : 0)
    expect(api.bidPosts).toEqual([])
    if (!sample.outbid) await expect(page.getByText('✓ Você está ganhando', { exact: true })).toBeVisible()
  })
}

test('already_winning preserva motivo autoritativo e contexto só enquanto confiável', async ({ page }) => {
  const { api } = await leaderRoom(page, { refusal: true })
  await expect(page.getByText(contextual, { exact: true })).toBeVisible()
  await page.getByLabel('Valor do lance').fill('120,00')
  await page.getByRole('button', { name: 'Dar lance', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Você já está ganhando este lote.')
  await expect(page.getByRole('alert')).not.toContainText('Saldo disponível insuficiente')
  await expect(page.getByText(contextual, { exact: true })).toBeVisible()
  expect(api.bidPosts).toHaveLength(1)
  await page.evaluate(() => window.dispatchEvent(new Event('offline')))
  await expect(page.getByText(contextual, { exact: true })).toHaveCount(0)
  await expect(page.getByText('✓ Você está ganhando', { exact: true })).toBeVisible()
})

test('WS recalcula mínimo/carteira/posição; stale, overlay, outbid e fim não inferem saldo', async ({ page }) => {
  const { api, update } = await leaderRoom(page)
  await expect(page.getByText(contextual, { exact: true })).toBeVisible()
  const wallet = api.hold('GET /api/wallet')
  update(room(makeBids(2, 11000, [OTHER_ALIAS, OWN_ALIAS]), { as_of: '2026-10-25T12:02:00.000000Z', minimum_next_bid_cents: 13000 }))
  await expect(page.getByText(contextual, { exact: true })).toHaveCount(0)
  wallet.fail()
  await expect(page.getByText('Não foi possível carregar a carteira.', { exact: true })).toBeVisible()
  await expect(page.getByText(contextual, { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Atualizar sala', exact: true }).click()
  await expect(page.getByText(contextual, { exact: true })).toBeVisible()
  // Same leader, new balance from the ordinary private reread.
  await page.route('**/api/wallet', route => route.fulfill({ json: { total_balance_cents: 100000, committed_balance_cents: 12000, available_balance_cents: 88000 } }))
  update(room(makeBids(3, 11000, [OWN_ALIAS]), { as_of: '2026-10-25T12:03:00.000000Z' }))
  await expect(page.getByText(contextual, { exact: true })).toHaveCount(0)
  update(room(makeBids(4, 11000, [OWN_ALIAS, OTHER_ALIAS]), { as_of: '2026-10-25T12:04:00.000000Z' }))
  await expect(page.getByText('↑ Você foi superado', { exact: true })).toBeVisible()
  await expect(page.getByText(contextual, { exact: true })).toHaveCount(0)
  update(room(makeBids(5, 11000, [OWN_ALIAS]), { as_of: '2026-10-25T12:05:00.000000Z', phase: 'ended', minimum_next_bid_cents: null }))
  await expect(page.getByText(contextual, { exact: true })).toHaveCount(0)
})

test('ajuda de mínimo, pseudônimo e integridade usa explicações precisas', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.setViewportSize({ width: 320, height: 812 })
  await leaderRoom(page)
  await page.getByRole('button', { name: 'Ajuda: Próximo lance mínimo', exact: true }).click()
  await expect(page.getByText(HELP.minimum, { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Ajuda: Pseudônimo', exact: true }).click()
  await expect(page.getByText(HELP.alias, { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Ajuda: Próximo lance mínimo', exact: true })).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByText(HELP.minimum, { exact: true })).not.toBeVisible()
  await expect(page.locator('.context-help-text:visible')).toHaveCount(1)
  await noOverflow(page)
  await page.route(`**/api/lots/${ID}/audit`, route => route.fulfill({ json: {
    lot_id: ID, as_of: AS_OF, integrity: 'verified', phase: 'live', settlement_status: 'pending', settlement: null,
    bid_count: 0, final_hash: '0'.repeat(64), bids: [],
  } }))
  await page.getByRole('link', { name: 'Consultar auditoria pública', exact: true }).click()
  await expect(page.locator('.context-help-text:visible')).toHaveCount(0)
  await page.getByRole('button', { name: 'Ajuda: Integridade verificada', exact: true }).click()
  await expect(page.getByText(HELP.integrity, { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Ajuda: Pseudônimo', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Ajuda: Integridade verificada', exact: true })).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByText(HELP.integrity, { exact: true })).not.toBeVisible()
  await expect(page.getByText(HELP.alias, { exact: true })).toBeVisible()
  await expect(page.locator('.context-help-text:visible')).toHaveCount(1)
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await noOverflow(page)
  await page.goBack()
  await expect(page.getByRole('button', { name: 'Ajuda: Próximo lance mínimo', exact: true })).toHaveAttribute('aria-expanded', 'false')
  await expect(page.locator('.context-help-text:visible')).toHaveCount(0)
  await page.getByRole('button', { name: 'Ajuda: Próximo lance mínimo', exact: true }).click()
  await expect(page.getByText(HELP.minimum, { exact: true })).toBeVisible()
  await expect(page.locator('.context-help-text:visible')).toHaveCount(1)
})

// Carteira do licitante (Story 3.1, CAP-10 a CAP-12). A API é simulada por
// interceptação de rede (`e2e/support/mockApi.ts`); o que garante o saldo é o teste
// transacional do back-end, não este.
import { expect, test, type Locator, type Page } from '@playwright/test'
import { MAX_CENTS, makeLots, mockApi, type MockOptions } from './support/mockApi'

const LOTS = makeLots({ live: 2, scheduled: 1, ended: 1 })
const WALLET = '/bidder/wallet'
const PASSWORD = 'Demo123!'
const TOLERANCE = 2

function bidder(options: MockOptions = {}): MockOptions {
  return { lots: LOTS, session: 'BIDDER', ...options }
}

async function deposit(page: Page, amount: string) {
  await page.getByLabel('Valor do depósito').fill(amount)
  await page.getByRole('button', { name: 'Depositar' }).click()
}

async function signIn(page: Page, email: string) {
  await page.getByLabel('E-mail').fill(email)
  await page.getByLabel('Senha').fill(PASSWORD)
  await page.getByRole('button', { name: 'Entrar', exact: true }).click()
}

interface Rect {
  x: number
  y: number
  right: number
  bottom: number
}

async function rect(locator: Locator): Promise<Rect> {
  const box = await locator.boundingBox()
  if (box === null) throw new Error('elemento sem caixa (não está visível?)')
  return { x: box.x, y: box.y, right: box.x + box.width, bottom: box.y + box.height }
}

// `b` fica à direita de `a` ou abaixo dele: nunca por cima.
function sideBySideOrBelow(a: Rect, b: Rect): boolean {
  return b.x >= a.right - TOLERANCE || b.y >= a.bottom - TOLERANCE
}

test.describe('header e acesso por papel', () => {
  test('BIDDER vê "Carteira" no header e, na carteira, o link é a página atual', async ({
    page,
  }) => {
    await mockApi(page, bidder())
    await page.goto('/')

    const nav = page.getByRole('navigation', { name: 'Principal' })
    await expect(nav.getByRole('link', { name: 'Carteira' })).toBeVisible()

    await nav.getByRole('link', { name: 'Carteira' }).click()

    await expect(page).toHaveURL(/\/bidder\/wallet$/)
    await expect(page.getByRole('heading', { name: 'Carteira', level: 1 })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Carteira' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await expect(page).toHaveTitle(/Carteira — ÁTRIO/)
  })

  test('anônimo e AUCTIONEER não veem "Carteira" no header', async ({ page }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/')
    await expect(page.getByRole('link', { name: 'Entrar', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Carteira' })).toHaveCount(0)

    const other = await page.context().newPage()
    await mockApi(other, { lots: LOTS, session: 'AUCTIONEER' })
    await other.goto('/')
    await expect(other.getByRole('button', { name: 'Sair' })).toBeVisible()
    await expect(other.getByRole('link', { name: 'Carteira' })).toHaveCount(0)
  })

  test('AUCTIONEER em /bidder/wallet vê "Área do licitante" e nenhum GET /api/wallet sai', async ({
    page,
  }) => {
    const api = await mockApi(page, { lots: LOTS, session: 'AUCTIONEER' })
    await page.goto(WALLET)

    await expect(
      page.getByRole('heading', { name: 'Área do licitante', level: 1 }),
    ).toBeVisible()
    await expect(page.getByText('Esta área é só para a conta de licitante.')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Carteira', level: 1 })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Depositar' })).toHaveCount(0)
    // Espera a sessão estabilizar antes de contar: nenhuma leitura da carteira.
    await expect(page.getByRole('button', { name: 'Sair' })).toBeVisible()
    expect(api.count('GET /api/wallet')).toBe(0)
    expect(api.count('POST /api/wallet/deposit')).toBe(0)
  })

  test('anônimo em /bidder/wallet vai ao login; BIDDER volta à carteira', async ({
    page,
  }) => {
    const api = await mockApi(page, { lots: LOTS })
    await page.goto(WALLET)

    await expect(page).toHaveURL(/\/login$/)
    expect(api.count('GET /api/wallet')).toBe(0)

    await signIn(page, 'bidder1@example.com')

    await expect(page).toHaveURL(/\/bidder\/wallet$/)
    await expect(page.getByText('Disponível para lances')).toBeVisible()
  })

  test('anônimo em /bidder/wallet que entra como AUCTIONEER vai à vitrine', async ({
    page,
  }) => {
    const api = await mockApi(page, { lots: LOTS })
    await page.goto(WALLET)
    await expect(page).toHaveURL(/\/login$/)

    await signIn(page, 'auctioneer@example.com')

    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('heading', { name: 'Ao vivo', level: 2 })).toBeVisible()
    expect(api.count('GET /api/wallet')).toBe(0)
  })

  test('link direto e refresh mantêm a carteira', async ({ page }) => {
    await mockApi(page, bidder({ wallet: { total: 125000, committed: 40000 } }))
    await page.goto(WALLET)
    await expect(page.getByText('R$ 850,00')).toBeVisible()

    await page.reload()

    await expect(page).toHaveURL(/\/bidder\/wallet$/)
    await expect(page.getByText('R$ 850,00')).toBeVisible()
  })

  test('uma sessão que expira na carteira volta ao login com o aviso', async ({
    page,
  }) => {
    await mockApi(page, bidder())
    await page.route('**/api/wallet', (route) =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ status: 401, code: 'unauthorized', message: 'x' }),
      }),
    )
    await page.goto(WALLET)

    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByText('Sua sessão expirou. Entre novamente.')).toBeVisible()
  })
})

test.describe('leitura', () => {
  test('três saldos, o disponível primeiro e em destaque', async ({ page }) => {
    await mockApi(page, bidder({ wallet: { total: 125000, committed: 40000 } }))
    await page.goto(WALLET)

    const labels = page.locator('.wallet-balances dt')
    await expect(labels).toHaveText([
      'Disponível para lances',
      'Saldo total',
      'Comprometido em lances',
    ])
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 850,00')
    await expect(page.locator('.wallet-balance').nth(0)).toContainText('R$ 1.250,00')
    await expect(page.locator('.wallet-balance').nth(1)).toContainText('R$ 400,00')
    // O disponível é o valor visualmente maior.
    const sizes = await page.evaluate(() => {
      const size = (selector: string) =>
        parseFloat(getComputedStyle(document.querySelector(selector)!).fontSize)
      return {
        available: size('.wallet-available dd'),
        support: size('.wallet-balance dd'),
      }
    })
    expect(sizes.available).toBeGreaterThan(sizes.support)
  })

  test('a lista de saldos é um dl válido: cada grupo direto tem o seu dt e dd', async ({
    page,
  }) => {
    await mockApi(page, bidder({ wallet: { total: 125000, committed: 40000 } }))
    await page.goto(WALLET)
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 850,00')

    // No HTML, um `div` filho de `dl` só pode conter `dt`/`dd` (sem outro `div` no meio).
    const groups = await page.evaluate(() =>
      Array.from(document.querySelectorAll('.wallet-balances > *')).map((child) => ({
        tag: child.tagName,
        children: Array.from(child.children).map((inner) => inner.tagName),
      })),
    )
    expect(groups).toEqual([
      { tag: 'DIV', children: ['DT', 'DD'] },
      { tag: 'DIV', children: ['DT', 'DD'] },
      { tag: 'DIV', children: ['DT', 'DD', 'DD'] },
    ])
    await expect(page.getByRole('term')).toHaveText([
      'Disponível para lances',
      'Saldo total',
      'Comprometido em lances',
    ])
  })

  test('carteira zerada mostra R$ 0,00 nos três e nenhum controle sem função', async ({
    page,
  }) => {
    await mockApi(page, bidder())
    await page.goto(WALLET)

    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 0,00')
    await expect(page.getByRole('button')).toHaveText(['Sair', 'Depositar'])
    await expect(page.locator('canvas, svg[role="img"]')).toHaveCount(0) // sem gráfico
  })
})

test.describe('depósito', () => {
  test('sucesso mostra a confirmação e os saldos da resposta do POST', async ({ page }) => {
    const api = await mockApi(page, bidder())
    await page.goto(WALLET)

    await deposit(page, '1.250,00')

    await expect(page.getByRole('status').filter({ hasText: 'confirmado.' })).toHaveText(
      /Depósito de R\$ 1\.250,00 confirmado\./,
    )
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 1.250,00')
    await expect(page.getByLabel('Valor do depósito')).toHaveValue('')
    expect(api.count('POST /api/wallet/deposit')).toBe(1)
    // O saldo vem da resposta do POST: nenhuma releitura foi necessária.
    expect(api.count('GET /api/wallet')).toBe(1)

    // Ao começar a digitar outro valor, o "confirmado" anterior sai de cena.
    await page.getByLabel('Valor do depósito').fill('5')
    await expect(page.getByText(/Depósito de .* confirmado\./)).toHaveCount(0)
  })

  test('o aviso de resultado entra numa região status que já existia antes do envio', async ({
    page,
  }) => {
    await mockApi(page, bidder({ deposit: 'server_error', reread: 'fail' }))
    await page.goto(WALLET)

    // Montada e vazia antes do envio: o leitor de tela anuncia a mudança de conteúdo.
    const region = page.locator('form.wallet-deposit [role="status"]')
    await expect(region).toHaveCount(1)
    await expect(region).toHaveText('')
    const handle = await region.elementHandle()

    await deposit(page, '20,00')

    await expect(region).toHaveText(/Não foi possível confirmar se o depósito foi feito\./)
    // É o mesmo elemento, não um novo inserido já preenchido.
    expect(await handle?.evaluate((node) => node.isConnected)).toBe(true)
    expect(
      await handle?.evaluate((node) => node.textContent?.includes('Não foi possível')),
    ).toBe(true)
  })

  test('valor inválido no navegador não chega ao servidor', async ({ page }) => {
    const api = await mockApi(page, bidder())
    await page.goto(WALLET)

    await deposit(page, 'abc')
    await expect(page.getByText(/Use só números/)).toBeVisible()
    await deposit(page, '0')
    await expect(page.getByText('O valor precisa ser maior que zero.')).toBeVisible()

    expect(api.count('POST /api/wallet/deposit')).toBe(0)
  })

  test('recusa 422 de teto mostra a mensagem no campo e não muda o saldo', async ({
    page,
  }) => {
    const api = await mockApi(page, bidder({ deposit: 'limit', wallet: { total: 5000, committed: 0 } }))
    await page.goto(WALLET)

    await deposit(page, '10,00')

    await expect(
      page.getByText('O depósito ultrapassaria o limite de saldo da carteira.'),
    ).toBeVisible()
    await expect(page.getByLabel('Valor do depósito')).toHaveAttribute('aria-invalid', 'true')
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 50,00')
    expect(api.count('POST /api/wallet/deposit')).toBe(1)
    expect(api.count('GET /api/wallet')).toBe(1)
  })

  test('recusa 422 de validação mostra a mensagem e não muda o saldo', async ({ page }) => {
    await mockApi(page, bidder({ deposit: 'validation' }))
    await page.goto(WALLET)

    await deposit(page, '10,00')

    await expect(page.getByText('Informe um valor válido em reais.')).toBeVisible()
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 0,00')
  })

  test('duplo envio gera exatamente um POST e o botão fica bloqueado', async ({ page }) => {
    const api = await mockApi(page, bidder({ depositDelayMs: 800 }))
    await page.goto(WALLET)
    await page.getByLabel('Valor do depósito').fill('10,00')
    const button = page.getByRole('button', { name: 'Depositar' })

    await button.dblclick()
    // Com o primeiro POST já pendente (o dblclick o enviou), mais dois envios
    // programáticos seguidos, que não passam pelo botão desabilitado: só a barreira do
    // depósito em andamento os segura.
    await page.evaluate(() => {
      const form = document.querySelector('form.wallet-deposit') as HTMLFormElement
      form.requestSubmit()
      form.requestSubmit()
    })
    await expect(page.getByRole('button', { name: 'Depositando…' })).toBeDisabled()
    // Durante o envio o valor não muda: nada digitado agora se perderia no sucesso.
    await expect(page.getByLabel('Valor do depósito')).not.toBeEditable()
    await expect(page.getByLabel('Valor do depósito')).toHaveValue('10,00')
    await page.getByLabel('Valor do depósito').press('Enter')

    await expect(page.getByText(/Depósito de R\$ 10,00 confirmado\./)).toBeVisible()
    expect(api.count('POST /api/wallet/deposit')).toBe(1)
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 10,00')
    await expect(button).toBeEnabled()
    await expect(page.getByLabel('Valor do depósito')).toBeEditable()
  })

  // F-08 do code review: a página remonta a cada navegação, mas o depósito pendente
  // não pertence a ela. Voltar à carteira durante o envio mantém o bloqueio.
  test('voltar à carteira com o depósito pendente mantém o bloqueio e não abre um segundo POST', async ({
    page,
  }) => {
    const api = await mockApi(page, bidder({ depositDelayMs: 2500 }))
    await page.goto(WALLET)
    const nav = page.getByRole('navigation', { name: 'Principal' })
    const settled = page.waitForResponse((response) =>
      response.url().endsWith('/api/wallet/deposit'),
    )

    await deposit(page, '10,00')
    await expect(page.getByRole('button', { name: 'Depositando…' })).toBeDisabled()
    await expect.poll(() => api.count('POST /api/wallet/deposit')).toBe(1)

    // 1) Outro clique em "Carteira": mesma URL, página remontada (relê o saldo).
    await nav.getByRole('link', { name: 'Carteira' }).click()
    await expect.poll(() => api.count('GET /api/wallet')).toBe(2)
    await expect(page.getByRole('button', { name: 'Depositando…' })).toBeDisabled()
    await expect(page.getByLabel('Valor do depósito')).not.toBeEditable()

    // 2) Sai para a vitrine e volta pelo Back: outra remontagem.
    await nav.getByRole('link', { name: 'Vitrine' }).click()
    await expect(page).toHaveURL(/\/$/)
    await page.goBack()
    await expect(page).toHaveURL(/\/bidder\/wallet$/)
    await expect.poll(() => api.count('GET /api/wallet')).toBe(3)
    await expect(page.getByRole('button', { name: 'Depositando…' })).toBeDisabled()
    await expect(page.getByLabel('Valor do depósito')).not.toBeEditable()

    // Um envio programático, que não passa pelo botão, também não sai.
    await page.evaluate(() => {
      const form = document.querySelector('form.wallet-deposit') as HTMLFormElement
      form.requestSubmit()
    })
    expect(api.count('POST /api/wallet/deposit')).toBe(1)

    // O POST original termina: a página remontada mostra o resultado dele.
    await settled
    await expect(page.getByText(/Depósito de R\$ 10,00 confirmado\./)).toBeVisible()
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 10,00')
    await expect(page.getByRole('button', { name: 'Depositar' })).toBeEnabled()
    await expect(page.getByLabel('Valor do depósito')).toBeEditable()
    expect(api.count('POST /api/wallet/deposit')).toBe(1)
  })

  test('trocar de conta com um depósito pendente não bloqueia nem alimenta a outra conta', async ({
    page,
  }) => {
    const api = await mockApi(page, bidder({ depositDelayMs: 2500 }))
    await page.goto(WALLET)
    const nav = page.getByRole('navigation', { name: 'Principal' })
    const settled = page.waitForResponse((response) =>
      response.url().endsWith('/api/wallet/deposit'),
    )

    // bidder1 inicia o depósito e sai antes da resposta.
    await deposit(page, '10,00')
    await expect(page.getByRole('button', { name: 'Depositando…' })).toBeDisabled()
    await page.getByRole('button', { name: 'Sair' }).click()
    await page.getByRole('link', { name: 'Entrar', exact: true }).click()
    await signIn(page, 'bidder2@example.com')
    await expect(page.getByRole('button', { name: 'Sair' })).toBeVisible()
    await nav.getByRole('link', { name: 'Carteira' }).click()

    // bidder2 não herda o bloqueio de bidder1.
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 0,00')
    await expect(page.getByRole('button', { name: 'Depositar' })).toBeEnabled()
    await expect(page.getByLabel('Valor do depósito')).toBeEditable()

    // O depósito de bidder1 termina: nada dele aparece na tela de bidder2.
    await settled
    await page.waitForTimeout(300)
    await expect(page.getByText(/Depósito de .* confirmado\./)).toHaveCount(0)
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 0,00')

    // E bidder2 deposita normalmente na própria carteira.
    await deposit(page, '5,00')
    await expect(page.getByText(/Depósito de R\$ 5,00 confirmado\./)).toBeVisible()
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 5,00')
    expect(api.count('POST /api/wallet/deposit')).toBe(2)
  })

  for (const mode of ['server_error', 'network'] as const) {
    test(`erro ambíguo (${mode}): uma releitura mostra o saldo real e nada de novo POST`, async ({
      page,
    }) => {
      // O servidor gravou e a resposta se perdeu: a releitura mostra o depósito.
      const api = await mockApi(page, bidder({ deposit: mode, depositAppliedOnError: true }))
      await page.goto(WALLET)

      await deposit(page, '20,00')

      await expect(page.getByText(/Não foi possível confirmar o depósito\./)).toBeVisible()
      await expect(page.locator('.wallet-available dd')).toHaveText('R$ 20,00')
      await expect(page.getByText(/Depósito de .* confirmado\./)).toHaveCount(0)
      expect(api.count('POST /api/wallet/deposit')).toBe(1)
      expect(api.count('GET /api/wallet')).toBe(2) // carga + uma releitura
      // Nada dispara um segundo POST depois.
      await page.waitForTimeout(500)
      expect(api.count('POST /api/wallet/deposit')).toBe(1)
    })
  }

  test('erro ambíguo sem depósito gravado: a releitura mostra o saldo antigo, sem afirmar nada', async ({
    page,
  }) => {
    const api = await mockApi(page, bidder({ deposit: 'server_error', wallet: { total: 5000, committed: 0 } }))
    await page.goto(WALLET)

    await deposit(page, '20,00')

    await expect(page.getByText(/Não foi possível confirmar o depósito\./)).toBeVisible()
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 50,00')
    expect(api.count('POST /api/wallet/deposit')).toBe(1)
  })

  test('erro ambíguo com a releitura falhando: mensagem neutra, sem sucesso e sem novo POST', async ({
    page,
  }) => {
    const api = await mockApi(
      page,
      bidder({ deposit: 'server_error', reread: 'fail', depositAppliedOnError: true }),
    )
    await page.goto(WALLET)

    await deposit(page, '20,00')

    await expect(
      page.getByText(/Não foi possível confirmar se o depósito foi feito\./),
    ).toBeVisible()
    await expect(page.getByText(/Depósito de .* confirmado\./)).toHaveCount(0)
    // O saldo na tela não foi atualizado por palpite: continua o da última leitura.
    await expect(page.locator('.wallet-available dd')).toHaveText('R$ 0,00')
    expect(api.count('POST /api/wallet/deposit')).toBe(1)
    expect(api.count('GET /api/wallet')).toBe(2)
    await page.waitForTimeout(500)
    expect(api.count('POST /api/wallet/deposit')).toBe(1)
  })
})

const VIEWPORTS = [
  { width: 1440, height: 900 },
  { width: 375, height: 812 },
  { width: 320, height: 812 },
]

for (const viewport of VIEWPORTS) {
  test.describe(`layout ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport })

    test('sem rolagem horizontal, mesmo com o maior saldo possível', async ({ page }) => {
      await mockApi(page, bidder({ wallet: { total: MAX_CENTS, committed: 0 } }))
      await page.goto(WALLET)
      await expect(page.locator('.wallet-available dd')).toHaveText('R$ 90.071.992.547.409,91')

      const overflow = await page.evaluate(() => ({
        page: document.documentElement.scrollWidth,
        width: document.documentElement.clientWidth,
      }))
      expect(overflow.page).toBeLessThanOrEqual(overflow.width)
      for (const selector of ['.wallet-available dd', '.wallet-balance', '.wallet-deposit']) {
        for (const part of await page.locator(selector).all()) {
          const box = await rect(part)
          expect(box.x, selector).toBeGreaterThanOrEqual(-TOLERANCE)
          expect(box.right, selector).toBeLessThanOrEqual(viewport.width + TOLERANCE)
        }
      }
      // Os três números e o depósito aparecem na ordem: disponível, apoio, formulário.
      const available = await rect(page.locator('.wallet-available'))
      const total = await rect(page.locator('.wallet-balance').nth(0))
      const committed = await rect(page.locator('.wallet-balance').nth(1))
      const form = await rect(page.locator('.wallet-deposit'))
      expect(total.y).toBeGreaterThanOrEqual(available.bottom - TOLERANCE)
      expect(committed.y).toBeGreaterThanOrEqual(available.bottom - TOLERANCE)
      expect(sideBySideOrBelow(total, committed)).toBe(true)
      expect(form.y).toBeGreaterThanOrEqual(Math.max(total.bottom, committed.bottom) - TOLERANCE)
    })

    test('o header do BIDDER não sobrepõe marca, Vitrine, Carteira e conta', async ({
      page,
    }) => {
      await mockApi(page, bidder())
      await page.goto(WALLET)
      await expect(page.getByRole('button', { name: 'Sair' })).toBeVisible()

      const nav = page.getByRole('navigation', { name: 'Principal' })
      const brand = await rect(page.locator('.site-brand'))
      const account = await rect(page.locator('.account'))
      const vitrine = await rect(nav.getByRole('link', { name: 'Vitrine' }))
      const wallet = await rect(nav.getByRole('link', { name: 'Carteira' }))

      for (const [name, part] of Object.entries({ brand, account, vitrine, wallet })) {
        expect(part.x, name).toBeGreaterThanOrEqual(-TOLERANCE)
        expect(part.right, name).toBeLessThanOrEqual(viewport.width + TOLERANCE)
      }
      expect(sideBySideOrBelow(brand, vitrine)).toBe(true)
      expect(sideBySideOrBelow(brand, wallet)).toBe(true)
      expect(sideBySideOrBelow(vitrine, wallet)).toBe(true)
      expect(sideBySideOrBelow(brand, account)).toBe(true)
      const overflow = await page.evaluate(() => ({
        page: document.documentElement.scrollWidth,
        width: document.documentElement.clientWidth,
      }))
      expect(overflow.page).toBeLessThanOrEqual(overflow.width)
    })
  })
}

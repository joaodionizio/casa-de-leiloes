// Login, retorno à página de origem, logout e header por papel (Story 2.5, CAP-8).
// A sessão é simulada: nenhuma credencial real e nenhum banco.
import { expect, test, type Page } from '@playwright/test'
import { lotId, makeLots, mockApi } from './support/mockApi'

const LOTS = makeLots({ live: 3, scheduled: 1, ended: 2 })
const PASSWORD = 'Demo123!'

async function signIn(page: Page, email: string, password = PASSWORD) {
  await page.getByLabel('E-mail').fill(email)
  await page.getByLabel('Senha').fill(password)
  await page.getByRole('button', { name: 'Entrar' }).click()
}

test.describe('login e returnTo', () => {
  test('lote público → Entrar → login → volta ao mesmo lote; Sair leva à vitrine', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto(`/lots/${lotId(2)}`)
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 2')

    await page.getByRole('link', { name: 'Entrar', exact: true }).click()
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByRole('heading', { name: 'Entrar', level: 1 })).toBeVisible()

    await signIn(page, 'bidder1@example.com')

    await expect(page).toHaveURL(new RegExp(`/lots/${lotId(2)}$`))
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 2')
    await expect(page.getByText('bidder1@example.com')).toBeVisible()

    await page.getByRole('button', { name: 'Sair' }).click()

    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('link', { name: 'Entrar', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sair' })).toHaveCount(0)
  })

  test('da vitrine, o login volta à vitrine', async ({ page }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/')

    await page.getByRole('link', { name: 'Entrar', exact: true }).click()
    await signIn(page, 'auctioneer@example.com')

    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('heading', { name: 'Ao vivo', level: 2 })).toBeVisible()
    // O leiloeiro que veio da vitrine não é jogado em "Criar lote".
    await expect(page.getByRole('heading', { name: 'Buscar obras' })).toBeHidden()
  })

  test('/login aberto direto leva à vitrine depois de entrar', async ({ page }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/login')

    await signIn(page, 'bidder1@example.com')

    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByText('bidder1@example.com')).toBeVisible()
  })

  test('credenciais inválidas ficam em /login com a mensagem em português', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/login')

    await signIn(page, 'bidder1@example.com', 'errada')

    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByText('E-mail ou senha inválidos.')).toBeVisible()
  })

  test('um returnTo externo no history.state é ignorado (sem open redirect)', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/login')
    await page.evaluate(() =>
      window.history.replaceState({ returnTo: 'https://evil.example/' }, '', '/login'),
    )
    await page.reload()
    // Controle: o estado adulterado sobreviveu ao reload; quem barra o destino é a
    // validação do `returnTo`, não a perda do `history.state`.
    expect(await page.evaluate(() => (window.history.state as { returnTo?: string })?.returnTo))
      .toBe('https://evil.example/')

    await signIn(page, 'bidder1@example.com')

    await expect(page).toHaveURL(/\/$/)
    expect(new URL(page.url()).origin).toBe(new URL('http://127.0.0.1:4173').origin)
  })

  test('um returnTo interno válido sobrevive ao reload em /login e leva ao lote', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/login')
    const target = `/lots/${lotId(2)}`
    await page.evaluate(
      (returnTo) => window.history.replaceState({ returnTo }, '', '/login'),
      target,
    )
    await page.reload()
    // Controle positivo: o `history.state` realmente sobreviveu ao reload (se não
    // sobrevivesse, o login cairia em `/` e este teste falharia aqui, não passaria igual).
    expect(await page.evaluate(() => (window.history.state as { returnTo?: string })?.returnTo))
      .toBe(target)
    await expect(page).toHaveURL(/\/login$/)

    await signIn(page, 'bidder1@example.com')

    await expect(page).toHaveURL(new RegExp(`${target}$`))
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 2')
  })

  test('quem já está logado e abre /login é levado para a vitrine', async ({ page }) => {
    await mockApi(page, { lots: LOTS, session: 'BIDDER' })

    await page.goto('/login')

    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('heading', { name: 'Ao vivo', level: 2 })).toBeVisible()
  })

  test('anônimo numa área do leiloeiro vai ao login e volta para ela', async ({ page }) => {
    await mockApi(page, { lots: LOTS })

    await page.goto('/auctioneer/lots')
    await expect(page).toHaveURL(/\/login$/)

    await signIn(page, 'auctioneer@example.com')

    await expect(page).toHaveURL(/\/auctioneer\/lots$/)
    await expect(page.getByRole('heading', { name: 'Meus lotes', level: 1 })).toBeVisible()
  })

  test('licitante numa área do leiloeiro vê "Área do leiloeiro" e volta à vitrine', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS, session: 'BIDDER' })

    await page.goto('/auctioneer/lots/new')

    await expect(page.getByRole('heading', { name: 'Área do leiloeiro' })).toBeVisible()
    await page.getByRole('link', { name: 'Ir para a vitrine', exact: true }).click()
    await expect(page).toHaveURL(/\/$/)
  })
})

test.describe('header por papel', () => {
  test('BIDDER: Vitrine, identificação e Sair; sem Criar lote nem Meus lotes', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS, session: 'BIDDER' })

    await page.goto('/')

    const nav = page.getByRole('navigation', { name: 'Principal' })
    await expect(nav.getByRole('link', { name: 'Vitrine' })).toBeVisible()
    await expect(page.getByText('bidder1@example.com')).toBeVisible()
    await expect(page.getByText('Licitante', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sair' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Criar lote' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'Meus lotes' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'Entrar', exact: true })).toHaveCount(0)
    // O licitante vê o mesmo detalhe público, sem carteira nem lance.
    await page.locator(`[data-lot-id="${lotId(2)}"]`).click()
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 2')
    await expect(page.getByRole('button', { name: /dar lance/i })).toHaveCount(0)
    await expect(page.getByText(/carteira/i)).toHaveCount(0)
  })

  test('AUCTIONEER: Vitrine, Criar lote, Meus lotes e Sair', async ({ page }) => {
    await mockApi(page, { lots: LOTS, session: 'AUCTIONEER' })

    await page.goto('/')

    const nav = page.getByRole('navigation', { name: 'Principal' })
    await expect(nav.getByRole('link', { name: 'Vitrine' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Criar lote' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Meus lotes' })).toBeVisible()
    await expect(page.getByText('Leiloeiro', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sair' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Entrar', exact: true })).toHaveCount(0)

    await nav.getByRole('link', { name: 'Criar lote' }).click()
    await expect(page).toHaveURL(/\/auctioneer\/lots\/new$/)
    await expect(page.getByRole('heading', { name: 'Buscar obras' })).toBeVisible()

    await nav.getByRole('link', { name: 'Meus lotes' }).click()
    await expect(page).toHaveURL(/\/auctioneer\/lots$/)
    await expect(page.getByRole('heading', { name: 'Meus lotes', level: 1 })).toBeVisible()

    // O rascunho de "Criar lote" sobrevive à ida e volta (fica montado e oculto).
    await nav.getByRole('link', { name: 'Criar lote' }).click()
    await expect(page.getByRole('heading', { name: 'Buscar obras' })).toBeVisible()
  })

  test('aria-current marca só o item da rota atual', async ({ page }) => {
    await mockApi(page, { lots: LOTS, session: 'AUCTIONEER' })
    await page.goto('/')
    const nav = page.getByRole('navigation', { name: 'Principal' })
    const vitrine = nav.getByRole('link', { name: 'Vitrine' })
    const create = nav.getByRole('link', { name: 'Criar lote' })
    const mine = nav.getByRole('link', { name: 'Meus lotes' })

    await expect(vitrine).toHaveAttribute('aria-current', 'page')
    await expect(create).not.toHaveAttribute('aria-current', /.+/)
    await expect(mine).not.toHaveAttribute('aria-current', /.+/)

    await create.click()
    await expect(create).toHaveAttribute('aria-current', 'page')
    await expect(vitrine).not.toHaveAttribute('aria-current', /.+/)

    await mine.click()
    await expect(mine).toHaveAttribute('aria-current', 'page')
    await expect(create).not.toHaveAttribute('aria-current', /.+/)

    // Na página de um lote nenhum item do header é a página atual.
    await page.goto(`/lots/${lotId(1)}`)
    await expect(nav.locator('[aria-current]')).toHaveCount(0)
  })

  test('a sessão expirada numa área do leiloeiro leva ao login com aviso', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS, session: 'AUCTIONEER' })
    // Registrada depois: o Playwright consulta primeiro a rota mais recente.
    await page.route('**/api/lots/mine', (route) =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ status: 401, code: 'unauthorized', message: 'x' }),
      }),
    )

    await page.goto('/auctioneer/lots')

    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByText('Sua sessão expirou. Entre novamente.')).toBeVisible()
  })
})

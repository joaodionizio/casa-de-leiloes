// Pilha real (opcional): FastAPI servindo o build, com banco de teste e seed. Só roda
// quando `E2E_REAL_BASE_URL` aponta para uma instância assim; sem ela, o arquivo inteiro
// é ignorado e o resto da suíte segue simulado. Prova o que a simulação não pode: que
// `/api/*` nunca cai no fallback da SPA e que as rotas públicas reais respondem JSON.
//
// Exemplo (veja o README, "Testes de navegador"):
//   E2E_REAL_BASE_URL=http://localhost:8000 npm run test:e2e -- real-stack
import { expect, test } from '@playwright/test'

const base = process.env.E2E_REAL_BASE_URL ?? ''
const UNKNOWN = '00000000-0000-4000-8000-0000000009ff'

test.describe('pilha real (FastAPI + build + PostgreSQL)', () => {
  test.skip(base === '', 'defina E2E_REAL_BASE_URL para rodar contra a pilha real')

  test('/api/lots é JSON e tem o contrato da vitrine, nunca HTML', async ({
    request,
  }) => {
    const response = await request.get(`${base}/api/lots`)

    expect(response.status()).toBe(200)
    expect(response.headers()['content-type']).toContain('application/json')
    expect(response.headers()['cache-control']).toBe('no-store')
    expect(Object.keys(await response.json()).sort()).toEqual([
      'as_of',
      'ended',
      'live',
      'scheduled',
    ])
  })

  test('caminhos /api/* inexistentes são 404 JSON, não a SPA', async ({ request }) => {
    for (const path of ['/api/nao-existe', '/api/lots/x/y', `/api/lots/${UNKNOWN}`]) {
      const response = await request.get(`${base}${path}`)
      expect(response.status(), path).toBe(404)
      expect(response.headers()['content-type'], path).toContain('application/json')
      expect(await response.text(), path).not.toContain('<!doctype html>')
    }
    const malformed = await request.get(`${base}/api/lots/abc`)
    expect(malformed.status()).toBe(422)
    expect(malformed.headers()['content-type']).toContain('application/json')
  })

  test('rotas do front devolvem a SPA (deep-link)', async ({ request }) => {
    for (const path of ['/', `/lots/${UNKNOWN}`, '/login', '/register', '/auctioneer/lots']) {
      const response = await request.get(`${base}${path}`)
      expect(response.status(), path).toBe(200)
      expect(response.headers()['content-type'], path).toContain('text/html')
    }
  })

  for (const role of ['BIDDER', 'AUCTIONEER'] as const) {
    test(`cadastro real ${role}, login manual e sessão depois de reload`, async ({ page, context }) => {
      const email = `registration-${role.toLowerCase()}-${crypto.randomUUID()}@example.com`
      const password = 'Cadastro local 123!'
      await page.route('**/api/catalog/images/**', route => route.abort())
      await page.goto(`${base}/register`)
      await expect(page.getByRole('heading', { name: 'Cadastro', exact: true })).toBeVisible()
      await page.reload()
      await page.locator(`input[type=radio][value=${role}]`).check()
      await page.getByLabel('E-mail', { exact: true }).fill(email)
      await page.getByLabel('Senha', { exact: true }).fill(password)
      await page.getByLabel('Confirmar senha', { exact: true }).fill(password)
      const result = page.waitForResponse(response => response.url().endsWith('/api/auth/register') && response.request().method() === 'POST')
      await page.getByRole('button', { name: 'Criar conta', exact: true }).click()
      const response = await result
      expect(response.status()).toBe(201)
      expect(await response.json()).toEqual({ email, role })
      expect(response.headers()['set-cookie']).toBeUndefined()
      await expect(page).toHaveURL(`${base}/login`)
      await expect(page.getByText('Conta criada com sucesso. Entre para continuar.')).toBeVisible()
      expect((await context.request.get(`${base}/api/me`)).status()).toBe(401)
      await page.getByLabel('E-mail', { exact: true }).fill(email)
      await page.getByLabel('Senha', { exact: true }).fill(password)
      await page.getByRole('button', { name: 'Entrar', exact: true }).click()
      await expect(page).toHaveURL(`${base}/`)
      await expect(page.locator('.site-header').getByText(role === 'BIDDER' ? 'Licitante' : 'Leiloeiro', { exact: true })).toBeVisible()
      await page.reload()
      await expect(page.getByText(email, { exact: true })).toBeVisible()
      expect(await (await context.request.get(`${base}/api/me`)).json()).toEqual({ email, role })
      const wallet = await context.request.get(`${base}/api/wallet`)
      if (role === 'BIDDER') {
        expect(wallet.status()).toBe(200)
        expect(await wallet.json()).toEqual({ total_balance_cents: 0, committed_balance_cents: 0, available_balance_cents: 0 })
      } else expect(wallet.status()).toBe(403)
    })
  }

  test('no navegador, /api/lots mostra JSON e um lote inexistente mostra o aviso', async ({
    page,
  }) => {
    await page.goto(`${base}/api/lots`)
    const text = await page.locator('body').innerText()
    expect(() => JSON.parse(text)).not.toThrow()

    await page.goto(`${base}/lots/${UNKNOWN}`)
    await expect(page.locator('#lot-title')).toHaveText('Lote indisponível ou não encontrado')
    await page.reload()
    await expect(page.locator('#lot-title')).toHaveText('Lote indisponível ou não encontrado')
  })

  test('a vitrine real abre para visitante, sem erro e sem pedir login', async ({
    page,
  }) => {
    await page.goto(`${base}/`)

    await expect(page.getByRole('heading', { name: 'Encerrados' })).toBeVisible()
    await expect(page.getByText('Não foi possível carregar a vitrine.')).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'Entrar', exact: true })).toBeVisible()
    await expect(page).toHaveURL(new RegExp(`${base.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/$`))
  })
})

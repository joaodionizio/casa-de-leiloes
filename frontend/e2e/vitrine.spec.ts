// Vitrine pública em navegador real (Story 2.5): anônimo, deep-link, History API,
// "Mostrar mais" e imagem quebrada. API simulada por interceptação de rede.
import { expect, test } from '@playwright/test'
import { lotId, makeLots, mockApi } from './support/mockApi'

const LOTS = makeLots({ live: 3, scheduled: 2, ended: 3 })

test.describe('anônimo', () => {
  test('abre a vitrine sem forçar login e sem controles do leiloeiro', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })

    await page.goto('/')

    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('heading', { name: 'Vitrine', level: 1 })).toBeAttached()
    await expect(page.getByRole('heading', { name: 'Ao vivo', level: 2 })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Próximos lotes' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Encerrados' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Entrar', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Criar lote' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'Meus lotes' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Sair' })).toHaveCount(0)
    await expect(page.getByLabel('E-mail')).toHaveCount(0)
  })

  test('clicar num lote abre /lots/{uuid} com o título do lote', async ({ page }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/')

    await page.locator(`[data-lot-id="${lotId(2)}"]`).click()

    await expect(page).toHaveURL(new RegExp(`/lots/${lotId(2)}$`))
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 2')
  })

  test('mostra o destaque, o estado em texto e nenhum controle de lance', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })

    await page.goto('/')

    const featured = page.locator('.featured')
    await expect(featured).toContainText('Ao vivo')
    await expect(featured).toContainText('Lance inicial')
    await expect(page.getByText('Encerrado, apurando resultado').first()).toBeVisible()
    await expect(page.getByRole('button', { name: /dar lance/i })).toHaveCount(0)
    await expect(page.getByText(/lance atual/i)).toHaveCount(0)
  })

  test('falha da API mostra erro e "Tentar novamente" refaz o pedido', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })
    // Registrada depois: o Playwright consulta primeiro a rota mais recente.
    let fail = true
    await page.route('**/api/lots', (route) =>
      fail
        ? route.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
        : route.fallback(),
    )

    await page.goto('/')
    await expect(page.getByText('Não foi possível carregar a vitrine.')).toBeVisible()

    fail = false
    await page.getByRole('button', { name: 'Tentar novamente' }).click()
    await expect(page.getByRole('heading', { name: 'Ao vivo', level: 2 })).toBeVisible()
  })

  test('sem nenhum lote a vitrine continua válida', async ({ page }) => {
    await mockApi(page, { lots: [] })

    await page.goto('/')

    await expect(page.getByText('Nenhum lote em leilão agora')).toBeVisible()
    await expect(page.getByText('Nenhum lote ao vivo agora.')).toBeVisible()
    await expect(page.getByText('Nenhum lote agendado.')).toBeVisible()
    await expect(page.getByText('Nenhum lote encerrado ainda.')).toBeVisible()
  })
})

test.describe('deep-link', () => {
  test('abre /lots/{uuid} direto e continua nele depois de recarregar', async ({
    page,
  }) => {
    const api = await mockApi(page, { lots: LOTS })

    await page.goto(`/lots/${lotId(1)}`)
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 1')
    await expect(page.getByRole('heading', { name: 'Leilão' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Ficha da obra' })).toBeVisible()
    // A sala (3.5) também mostra o lance inicial: o termo estático fica no bloco Leilão.
    await expect(
      page.locator('.lot-page-block').getByText('Lance inicial', { exact: true }),
    ).toBeVisible()
    await expect(page.getByText('Incremento mínimo')).toBeVisible()
    await expect(page.getByRole('button', { name: /dar lance/i })).toHaveCount(0)

    await page.reload()

    await expect(page).toHaveURL(new RegExp(`/lots/${lotId(1)}$`))
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 1')
    expect(api.count(`GET /api/lots/${lotId(1)}`)).toBe(2)
  })

  test('lote inexistente mostra "Lote não encontrado"; rota inválida não chama a API', async ({
    page,
  }) => {
    const api = await mockApi(page, { lots: LOTS })

    await page.goto(`/lots/${lotId(999)}`)
    await expect(page.locator('#lot-title')).toHaveText('Lote não encontrado')

    await page.goto('/lots/abc')
    await expect(page.locator('h1:visible')).toHaveText('Página não encontrada')
    expect(api.requests.filter((item) => item.includes('/api/lots/abc'))).toEqual([])
  })

  test('a página do lote lê só /api/lots/{id}, nunca o catálogo da AIC', async ({
    page,
  }) => {
    const api = await mockApi(page, { lots: LOTS })

    await page.goto(`/lots/${lotId(1)}`)
    await expect(page.locator('#lot-title')).toBeVisible()
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Ao vivo', level: 2 })).toBeVisible()

    expect(api.requests.some((item) => item.includes('/api/catalog/artworks'))).toBe(false)
    expect(api.unexpected).toEqual([])
  })
})

test.describe('History API', () => {
  test('vitrine → detalhe → Back → vitrine → Forward → detalhe', async ({ page }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/')

    await page.locator(`[data-lot-id="${lotId(2)}"]`).click()
    await expect(page).toHaveURL(new RegExp(`/lots/${lotId(2)}$`))
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 2')

    await page.goBack()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('heading', { name: 'Ao vivo', level: 2 })).toBeVisible()

    await page.goForward()
    await expect(page).toHaveURL(new RegExp(`/lots/${lotId(2)}$`))
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 2')
  })

  test('"← Vitrine" depois de chegar pela vitrine se comporta como o Back', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/')
    await page.locator(`[data-lot-id="${lotId(2)}"]`).click()
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 2')

    await page.getByRole('link', { name: /Vitrine$/ }).filter({ hasText: '←' }).click()

    await expect(page).toHaveURL(/\/$/)
    await expect(page.locator(`[data-lot-id="${lotId(2)}"]`)).toBeFocused()
  })

  test('"← Vitrine" num link direto leva à vitrine', async ({ page }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto(`/lots/${lotId(1)}`)
    await expect(page.locator('#lot-title')).toBeVisible()

    await page.getByRole('link', { name: /Vitrine$/ }).filter({ hasText: '←' }).click()

    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('heading', { name: 'Ao vivo', level: 2 })).toBeVisible()
  })

  test('Ctrl+clique não navega a página atual (abre fora da SPA)', async ({ page }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/')

    await page.locator(`[data-lot-id="${lotId(2)}"]`).click({ modifiers: ['ControlOrMeta'] })

    await expect(page).toHaveURL(/\/$/)
  })
})

test.describe('Mostrar mais encerrados', () => {
  test('começa com 6, revela de 6 em 6 e não faz novo pedido à API', async ({ page }) => {
    const api = await mockApi(page, { lots: makeLots({ live: 1, ended: 14 }) })
    await page.goto('/')
    const rows = page.locator('.closed-row')

    await expect(rows).toHaveCount(6)
    await expect(page.getByText('Mostrando 6 de 14 encerrados.')).toBeVisible()
    expect(api.count('GET /api/lots')).toBe(1)

    await page.getByRole('button', { name: 'Mostrar mais encerrados' }).click()
    await expect(rows).toHaveCount(12)
    await expect(page.getByText('Mostrando 12 de 14 encerrados.')).toBeVisible()

    await page.getByRole('button', { name: 'Mostrar mais encerrados' }).click()
    await expect(rows).toHaveCount(14)
    await expect(
      page.getByRole('button', { name: 'Mostrar mais encerrados' }),
    ).toHaveCount(0)

    expect(api.count('GET /api/lots')).toBe(1)
  })

  test('com 6 ou menos encerrados não há botão', async ({ page }) => {
    await mockApi(page, { lots: makeLots({ live: 1, ended: 6 }) })
    await page.goto('/')

    await expect(page.locator('.closed-row')).toHaveCount(6)
    await expect(
      page.getByRole('button', { name: 'Mostrar mais encerrados' }),
    ).toHaveCount(0)
  })

  test('o Back devolve a vitrine com os encerrados que estavam à mostra', async ({
    page,
  }) => {
    await mockApi(page, { lots: makeLots({ live: 1, ended: 14 }) })
    await page.goto('/')
    await page.getByRole('button', { name: 'Mostrar mais encerrados' }).click()
    await expect(page.locator('.closed-row')).toHaveCount(12)

    await page.locator(`[data-lot-id="${lotId(211)}"]`).click()
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 211')
    await page.goBack()

    await expect(page.locator('.closed-row')).toHaveCount(12)
    await expect(page.locator(`[data-lot-id="${lotId(211)}"]`)).toBeFocused()
  })
})

test.describe('imagem quebrada', () => {
  test('a vitrine troca pelo placeholder e o resto continua funcional', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS, images: 'broken' })

    await page.goto('/')

    const featuredImage = page.locator('.featured img')
    await expect(featuredImage).toHaveAttribute('src', /\/artwork-placeholder\.svg$/)
    await expect(page.locator('.featured')).toContainText('Obra de teste 1')
    await expect(page.locator('.featured')).toContainText('Imagem indisponível')
    await expect(page.locator('.featured-cta')).toBeVisible()

    const railImage = page.locator('.rail-live .rail-link img').first()
    await railImage.scrollIntoViewIfNeeded()
    await expect(railImage).toHaveAttribute('src', /\/artwork-placeholder\.svg$/)
    await expect(page.locator('.rail-live .rail-title').first()).toBeVisible()
    await expect(page.locator('.rail-live .rail-link').first()).toBeVisible()

    await page.locator('.featured-cta').click()
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 1')
  })

  test('a página do lote mostra o placeholder e mantém ficha e valores', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS, images: 'broken' })

    await page.goto(`/lots/${lotId(1)}`)

    await expect(page.locator('.lot-page img')).toHaveAttribute(
      'src',
      /\/artwork-placeholder\.svg$/,
    )
    await expect(page.locator('.lot-page')).toContainText('Imagem indisponível')
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 1')
    await expect(page.getByRole('heading', { name: 'Ficha da obra' })).toBeVisible()
    await expect(page.locator('.lot-money').first()).toBeVisible()
  })
})

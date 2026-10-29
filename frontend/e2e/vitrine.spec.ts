// Vitrine pública em navegador real (Story 2.5): anônimo, deep-link, History API,
// "Mostrar mais" e imagem quebrada. API simulada por interceptação de rede.
import { expect, test } from '@playwright/test'
import { lotId, makeBids, makeLot, makeLots, mockApi, OWN_ALIAS, OTHER_ALIAS } from './support/mockApi'

const LOTS = makeLots({ live: 3, scheduled: 2, ended: 3 })

test('indicadores decorativos: Ao vivo em toda a Vitrine, Encerrados mais lento e movimento reduzido estático', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await mockApi(page, { lots: LOTS })
  await page.goto('/')

  for (const name of ['Ao vivo', 'Próximos lotes', 'Encerrados']) {
    const heading = page.getByRole('heading', { name, exact: true, level: 2 })
    await expect(heading).toHaveAccessibleName(name)
    await expect(heading.locator('.vitrine-section-indicator')).toHaveAttribute('aria-hidden', 'true')
  }
  const live = page.locator('#live-heading .vitrine-section-indicator')
  const animationNames = () => page.locator('.vitrine-section-indicator').evaluateAll(nodes =>
    nodes.map(node => getComputedStyle(node, '::before').animationName),
  )
  expect(await animationNames()).toEqual(['vitrine-live-breathe', 'none', 'vitrine-ended-breathe'])
  expect(await page.locator('.vitrine-section-indicator-ended').evaluate(node =>
    getComputedStyle(node, '::before').animationDuration,
  )).toBe('2.8s')
  const lotDots = page.locator('.vitrine .lot-state-dot')
  await expect(lotDots).toHaveCount(3) // Hero e dois itens ao vivo, sem duplicar o destaque.
  for (const dot of await lotDots.all()) {
    await expect(dot).toHaveAttribute('aria-hidden', 'true')
    expect(await dot.evaluate(node => getComputedStyle(node).animationName)).toBe('vitrine-live-breathe')
  }
  const before = await live.boundingBox()
  await live.evaluate(node => {
    for (const animation of node.getAnimations({ subtree: true })) {
      animation.pause()
      animation.currentTime = 900
    }
  })
  expect(await live.boundingBox()).toEqual(before)

  await page.emulateMedia({ reducedMotion: 'reduce' })
  expect(await animationNames()).toEqual(['none', 'none', 'none'])
  await expect(live).toBeVisible()
  expect(await page.locator('.vitrine-section-indicator').evaluateAll(nodes =>
    nodes.flatMap(node => node.getAnimations({ subtree: true })).length,
  )).toBe(0)
  for (const dot of await lotDots.all()) {
    await expect(dot).toBeVisible()
    expect(await dot.evaluate(node => getComputedStyle(node).animationName)).toBe('none')
  }

  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await page.locator('.featured-cta').click()
  await expect(page.locator('.lot-page .lot-state-dot')).toBeVisible()
  expect(await page.locator('.lot-page .lot-state-dot').evaluate(node =>
    getComputedStyle(node).animationName,
  )).toBe('none')
})

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

  test('lote inexistente mostra "Lote indisponível ou não encontrado"; rota inválida não chama a API', async ({
    page,
  }) => {
    const api = await mockApi(page, { lots: LOTS })

    await page.goto(`/lots/${lotId(999)}`)
    await expect(page.locator('#lot-title')).toHaveText('Lote indisponível ou não encontrado')

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
    const api = await mockApi(page, { lots: LOTS, images: 'broken' })

    await page.goto('/')

    const featuredImage = page.locator('.featured img')
    await expect(featuredImage).toHaveAttribute('src', /\/artwork-placeholder\.svg$/)
    await expect(page.locator('.featured')).toContainText('Obra de teste 1')
    await expect(page.locator('.featured')).toContainText('Imagem indisponível')
    await expect(page.locator('.featured')).toContainText('R$ 110,00')
    expect(api.count(`GET ${LOTS[0].image_url}`)).toBeGreaterThan(0)
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
    const api = await mockApi(page, {
      lots: LOTS,
      images: 'broken',
      rooms: { [lotId(1)]: { bids: makeBids(2, LOTS[0].starting_bid_cents) } },
    })

    await page.goto(`/lots/${lotId(1)}`)

    await expect(page.locator('.lot-page img')).toHaveAttribute(
      'src',
      /\/artwork-placeholder\.svg$/,
    )
    await expect(page.locator('.lot-page')).toContainText('Imagem indisponível')
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 1')
    await expect(page.getByRole('heading', { name: 'Ficha da obra' })).toBeVisible()
    await expect(page.locator('.lot-money').first()).toBeVisible()
    await expect(page.locator('.bid-current')).toHaveText('R$ 120,00')
    await expect(page.locator('.lot-page')).toContainText('Ao vivo')
    await expect(page.getByText(OWN_ALIAS, { exact: true })).toBeVisible()
    await expect(page.getByText(OTHER_ALIAS, { exact: true })).toBeVisible()
    expect(api.count(`GET ${LOTS[0].image_url}`)).toBeGreaterThan(0)
    expect(api.count(`GET /api/lots/${lotId(1)}/bids`)).toBeGreaterThan(0)
  })
})


for (const width of [1440, 375, 320]) {
  test(`R6.4-01: pending/settled e nomes acessíveis sem overflow em ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    const pending = makeLot(201, 'ended', { title: 'Resultado pendente', settlement_status: 'pending' })
    const settled = makeLot(202, 'ended', { title: 'Resultado apurado', settlement_status: 'settled' })
    const api = await mockApi(page, { lots: [
      makeLot(1, 'live'), makeLot(101, 'scheduled'), pending, settled,
    ] })
    await page.goto('/')
    const pendingLink = page.locator(`[data-lot-id="${pending.id}"]`)
    const settledLink = page.locator(`[data-lot-id="${settled.id}"]`)
    await expect(pendingLink.locator('.lot-state')).toHaveText('Encerrado, apurando resultado')
    await expect(pendingLink).toHaveAccessibleName('Resultado pendente. Encerrado, apurando resultado.')
    await expect(settledLink.locator('.lot-state')).toHaveText('Encerrado')
    await expect(settledLink).toHaveAccessibleName('Resultado apurado. Encerrado.')
    await expect(settledLink).not.toContainText('apurando resultado')
    await expect(page.locator('.featured .lot-state')).toHaveText('●Ao vivo')
    await expect(page.locator('.rail-item-upcoming .lot-state')).toHaveText('Agendado')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    for (const link of [pendingLink, settledLink]) {
      await link.scrollIntoViewIfNeeded()
      await expect(link.locator('.lot-state')).toBeVisible()
      const bounds = await link.boundingBox()
      expect(bounds).not.toBeNull()
      expect(bounds!.x).toBeGreaterThanOrEqual(0)
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width)
    }
    expect(api.count('GET /api/lots')).toBe(1)
    expect(api.requests.filter(request => /GET \/api\/lots\//.test(request))).toEqual([])
    expect(api.unexpected).toEqual([])
  })
}

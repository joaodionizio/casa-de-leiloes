// Layout e responsividade em viewports reais (Story 2.5, CAP-12). Asserts por
// estrutura e caixas delimitadoras (bounding boxes) com tolerância; nenhum screenshot
// diff. Os viewports são os do pedido: desktop 1440×900 e celular 375×812 e 320×812.
import { expect, test, type Page } from '@playwright/test'
import {
  LONG_TITLE,
  MAX_CENTS,
  lotId,
  makeLot,
  makeLots,
  mockApi,
  type MockLot,
} from './support/mockApi'

const TOLERANCE = 2 // px: arredondamento de subpixel e barra de rolagem

const VIEWPORTS = [
  { name: 'desktop 1440×900', width: 1440, height: 900, wide: true },
  { name: 'celular 375×812', width: 375, height: 812, wide: false },
  { name: 'celular 320×812', width: 320, height: 812, wide: false },
] as const

// Vitrine de estresse: título longo, valor máximo, vários lotes em cada grupo.
function stressLots(): MockLot[] {
  const lots = makeLots({ live: 5, scheduled: 20, ended: 50 })
  lots[0] = makeLot(1, 'live', {
    title: LONG_TITLE,
    starting_bid_cents: MAX_CENTS,
    artist_display: 'Um Artista com um Nome Muito Comprido\n(Francês, 1859–1891)',
  })
  lots[1] = makeLot(2, 'live', { title: LONG_TITLE, starting_bid_cents: MAX_CENTS })
  return lots
}

interface Box {
  x: number
  y: number
  width: number
  height: number
  right: number
  bottom: number
}

async function box(page: Page, selector: string): Promise<Box> {
  const found = await page.locator(selector).first().boundingBox()
  expect(found, `${selector} precisa estar visível`).not.toBeNull()
  const { x, y, width, height } = found!
  return { x, y, width, height, right: x + width, bottom: y + height }
}

async function horizontalOverflow(page: Page): Promise<{ page: number; width: number }> {
  return page.evaluate(() => ({
    page: document.documentElement.scrollWidth,
    width: window.innerWidth,
  }))
}

// Elementos do conteúdo que passam da borda direita do viewport, fora dos rails (a
// rolagem horizontal deles é intencional) e fora do texto só para leitor de tela.
async function elementsBeyondViewport(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const limit = window.innerWidth + 1
    const offenders: string[] = []
    for (const element of document.querySelectorAll('header *, main *, footer *')) {
      if (element.closest('.rail, .visually-hidden, [hidden]') !== null) continue
      const rect = element.getBoundingClientRect()
      if (rect.width === 0 && rect.height === 0) continue
      if (rect.right > limit || rect.left < -1) {
        offenders.push(`${element.tagName.toLowerCase()}.${element.className} ${Math.round(rect.left)}→${Math.round(rect.right)}`)
      }
    }
    return offenders
  })
}

for (const viewport of VIEWPORTS) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } })

    test('vitrine: sem rolagem horizontal, header e conteúdo dentro do viewport', async ({
      page,
    }) => {
      await mockApi(page, { lots: stressLots() })
      await page.goto('/')
      await expect(page.locator('.featured')).toBeVisible()

      const overflow = await horizontalOverflow(page)
      expect(overflow.page).toBeLessThanOrEqual(overflow.width)
      expect(await elementsBeyondViewport(page)).toEqual([])

      const header = await box(page, '.site-header-inner')
      expect(header.x).toBeGreaterThanOrEqual(-TOLERANCE)
      expect(header.right).toBeLessThanOrEqual(viewport.width + TOLERANCE)
      for (const child of await page.locator('.site-header-inner > *').all()) {
        const rect = await child.boundingBox()
        if (rect === null) continue
        expect(rect.x + rect.width).toBeLessThanOrEqual(viewport.width + TOLERANCE)
      }
    })

    test('detalhe do lote: sem rolagem horizontal, com título longo e valor máximo', async ({
      page,
    }) => {
      await mockApi(page, { lots: stressLots() })
      await page.goto(`/lots/${lotId(1)}`)
      await expect(page.locator('#lot-title')).toBeVisible()
      await expect(page.locator('.lot-money').first()).toBeVisible()

      const overflow = await horizontalOverflow(page)
      expect(overflow.page).toBeLessThanOrEqual(overflow.width)
      expect(await elementsBeyondViewport(page)).toEqual([])

      const art = await box(page, '.lot-page-art')
      const info = await box(page, '.lot-page-info')
      if (viewport.wide) {
        // Duas colunas: obra à esquerda, ficha à direita, lado a lado.
        expect(info.x).toBeGreaterThanOrEqual(art.right - TOLERANCE)
        expect(info.y).toBeLessThan(art.bottom)
      } else {
        // Uma coluna: a ficha vem abaixo da obra.
        expect(info.y).toBeGreaterThanOrEqual(art.bottom - TOLERANCE)
      }
    })

    test('login: sem rolagem horizontal', async ({ page }) => {
      await mockApi(page, { lots: stressLots() })
      await page.goto('/login')
      await expect(page.getByLabel('E-mail')).toBeVisible()

      const overflow = await horizontalOverflow(page)
      expect(overflow.page).toBeLessThanOrEqual(overflow.width)
      expect(await elementsBeyondViewport(page)).toEqual([])
    })

    test('destaque: duas colunas no desktop e empilhado no celular', async ({ page }) => {
      await mockApi(page, { lots: stressLots() })
      await page.goto('/')
      await expect(page.locator('.featured-info')).toBeVisible()

      const art = await box(page, '.featured-art')
      const info = await box(page, '.featured-info')
      if (viewport.wide) {
        expect(art.x).toBeGreaterThanOrEqual(info.right - TOLERANCE)
        // A obra domina: cerca de 60% da largura do destaque.
        const featured = await box(page, '.featured')
        expect(art.width / featured.width).toBeGreaterThan(0.5)
        expect(art.width).toBeGreaterThan(info.width)
      } else {
        expect(info.y).toBeGreaterThanOrEqual(art.bottom - TOLERANCE)
        // No celular a obra ganha a largura toda do container.
        const main = await box(page, '.app-main')
        expect(art.width).toBeGreaterThan(main.width * 0.8)
      }
    })

    test('rails: itens legíveis, sem texto estourando o cartão', async ({ page }) => {
      await mockApi(page, { lots: stressLots() })
      await page.goto('/')
      await expect(page.locator('.rail-live')).toBeVisible()

      for (const item of await page.locator('.rail-item').all()) {
        const rect = await item.boundingBox()
        expect(rect).not.toBeNull()
        expect(rect!.width).toBeGreaterThanOrEqual(190)
      }
      const clipped = await page.evaluate(() =>
        [...document.querySelectorAll('.rail-title, .rail-value, .rail-when')]
          .filter((element) => element.scrollWidth > element.clientWidth + 1)
          .map((element) => element.className),
      )
      expect(clipped).toEqual([])
      // O rail rola por dentro (intencional), nunca a página.
      const railScrolls = await page.evaluate(() => {
        const rail = document.querySelector('.rail-live')!
        return rail.scrollWidth > rail.clientWidth
      })
      expect(railScrolls).toBe(true)
      const overflow = await horizontalOverflow(page)
      expect(overflow.page).toBeLessThanOrEqual(overflow.width)
    })

    test('encerrados: linhas densas legíveis, com a data e o estado visíveis', async ({
      page,
    }) => {
      await mockApi(page, { lots: stressLots() })
      await page.goto('/')
      const row = page.locator('.closed-row').first()
      await row.scrollIntoViewIfNeeded()

      const rowBox = await box(page, '.closed-row')
      expect(rowBox.right).toBeLessThanOrEqual(viewport.width + TOLERANCE)
      await expect(row).toContainText('Encerrado, apurando resultado')
      await expect(row).toContainText('Terminou')
      const clipped = await page.evaluate(() =>
        [...document.querySelectorAll('.closed-title, .closed-status')]
          .filter((element) => element.scrollWidth > element.clientWidth + 1)
          .map((element) => element.className),
      )
      expect(clipped).toEqual([])
    })
  })
}

test.describe('centralização no desktop', () => {
  test.use({ viewport: { width: 1440, height: 900 } })

  test('o conteúdo fica num container central e o destaque ocupa a largura dele', async ({
    page,
  }) => {
    await mockApi(page, { lots: stressLots() })
    await page.goto('/')
    await expect(page.locator('.featured')).toBeVisible()

    const main = await box(page, '.app-main')
    const featured = await box(page, '.featured')
    const header = await box(page, '.site-header-inner')
    const left = main.x
    const right = 1440 - main.right

    // Container centrado: margens esquerda e direita iguais e não negativas.
    expect(left).toBeGreaterThanOrEqual(0)
    expect(right).toBeGreaterThanOrEqual(0)
    expect(Math.abs(left - right)).toBeLessThanOrEqual(TOLERANCE * 3)
    // Não passa da largura máxima de 72rem (1152 px).
    expect(main.width).toBeLessThanOrEqual(1152 + TOLERANCE)
    // Header e conteúdo compartilham o mesmo container.
    expect(Math.abs(header.x - main.x)).toBeLessThanOrEqual(TOLERANCE)
    expect(Math.abs(header.right - main.right)).toBeLessThanOrEqual(TOLERANCE)
    // O destaque fica dentro do container e usa quase toda a largura útil dele.
    const inner = main.width - 2 * 32
    expect(featured.x).toBeGreaterThanOrEqual(main.x - TOLERANCE)
    expect(featured.right).toBeLessThanOrEqual(main.right + TOLERANCE)
    expect(featured.width).toBeGreaterThanOrEqual(inner * 0.95)

    // Cada rail está dentro do container (a rolagem é interna a ele).
    for (const rail of await page.locator('.rail').all()) {
      const rect = await rail.boundingBox()
      expect(rect!.x).toBeGreaterThanOrEqual(main.x - TOLERANCE)
      expect(rect!.x + rect!.width).toBeLessThanOrEqual(main.right + TOLERANCE)
    }
  })
})

test.describe('densidade das coleções no desktop', () => {
  test.use({ viewport: { width: 1440, height: 900 } })

  async function railExtent(page: Page, selector: string) {
    const rail = await box(page, selector)
    const items = await page.locator(`${selector} .rail-item`).all()
    const first = await items[0].boundingBox()
    const last = await items[items.length - 1].boundingBox()
    return {
      rail,
      count: items.length,
      first: first!,
      last: last!,
      span: last!.x + last!.width - first!.x,
    }
  }

  test('três lotes ao vivo no rail ocupam quase toda a faixa', async ({ page }) => {
    // O destaque é o primeiro; os outros três vão para o rail.
    await mockApi(page, { lots: makeLots({ live: 4 }) })
    await page.goto('/')
    await expect(page.locator('.rail-live')).toBeVisible()

    const extent = await railExtent(page, '.rail-live')

    expect(extent.count).toBe(3)
    expect(extent.span / extent.rail.width).toBeGreaterThan(0.9)
    // Sem rolagem: os três cabem.
    const scrolls = await page.evaluate(() => {
      const rail = document.querySelector('.rail-live')!
      return rail.scrollWidth > rail.clientWidth + 1
    })
    expect(scrolls).toBe(false)
  })

  test('dois lotes ao vivo dividem a faixa', async ({ page }) => {
    await mockApi(page, { lots: makeLots({ live: 3 }) })
    await page.goto('/')
    await expect(page.locator('.rail-live')).toBeVisible()

    const extent = await railExtent(page, '.rail-live')

    expect(extent.count).toBe(2)
    expect(extent.span / extent.rail.width).toBeGreaterThan(0.9)
  })

  test('um próximo lote sozinho vira um cartão largo e horizontal, não um quadrado perdido', async ({
    page,
  }) => {
    await mockApi(page, { lots: makeLots({ live: 1, scheduled: 1 }) })
    await page.goto('/')
    const item = page.locator('.rail-upcoming .rail-item')
    await expect(item).toHaveCount(1)

    const rail = await box(page, '.rail-upcoming')
    const card = await box(page, '.rail-upcoming .rail-item')
    const image = await box(page, '.rail-upcoming .artwork-image')
    const body = await box(page, '.rail-upcoming .rail-body')

    expect(card.width / rail.width).toBeGreaterThan(0.5)
    // Obra à esquerda e texto à direita, lado a lado.
    expect(body.x).toBeGreaterThanOrEqual(image.right - TOLERANCE)
    expect(Math.abs(image.y - body.y)).toBeLessThan(image.height)
  })

  test('com muitos lotes o rail volta a rolar e mostra parte do próximo', async ({
    page,
  }) => {
    await mockApi(page, { lots: makeLots({ live: 8 }) })
    await page.goto('/')
    await expect(page.locator('.rail-live')).toBeVisible()

    const state = await page.evaluate(() => {
      const rail = document.querySelector('.rail-live')!
      const railRect = rail.getBoundingClientRect()
      const items = [...rail.querySelectorAll('.rail-item')].map((item) =>
        item.getBoundingClientRect(),
      )
      return {
        scrolls: rail.scrollWidth > rail.clientWidth + 1,
        // Algum item começa dentro do rail e termina fora: continuidade visível.
        partial: items.some(
          (rect) => rect.left < railRect.right - 4 && rect.right > railRect.right + 4,
        ),
      }
    })
    expect(state.scrolls).toBe(true)
    expect(state.partial).toBe(true)
    // Há mais itens do que cabem, então os botões do rail existem no desktop.
    await expect(
      page.getByRole('button', { name: 'Ver mais lotes de Ao vivo' }),
    ).toBeVisible()
  })

  test('o espaço vertical entre as seções não vira vazio acidental', async ({ page }) => {
    await mockApi(page, { lots: makeLots({ live: 4, scheduled: 3, ended: 3 }) })
    await page.goto('/')
    await expect(page.locator('.closed-list')).toBeVisible()

    const sections = await page.evaluate(() =>
      [...document.querySelectorAll('.vitrine > section')].map((section) => {
        const rect = section.getBoundingClientRect()
        return { top: rect.top, bottom: rect.bottom }
      }),
    )
    for (let i = 1; i < sections.length; i += 1) {
      const gap = sections[i].top - sections[i - 1].bottom
      expect(gap).toBeGreaterThanOrEqual(16)
      expect(gap).toBeLessThanOrEqual(64)
    }
  })
})

test.describe('um lote ao vivo no celular ocupa a largura útil', () => {
  test.use({ viewport: { width: 375, height: 812 } })

  test('item único do rail', async ({ page }) => {
    await mockApi(page, { lots: makeLots({ live: 2 }) })
    await page.goto('/')
    const item = page.locator('.rail-live .rail-item')
    await expect(item).toHaveCount(1)

    const rail = await box(page, '.rail-live')
    const card = await box(page, '.rail-live .rail-item')

    expect(card.width / rail.width).toBeGreaterThan(0.9)
  })
})

for (const width of [1440, 768, 375, 320]) {
  test(`hero típico ${width}: ação no primeiro viewport e foco sem bloqueio`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 1440 ? 900 : 812 })
    await mockApi(page, { lots: makeLots({ live: 5, scheduled: 20, ended: 50 }) })
    await page.goto('/')
    const cta = page.locator('.featured-cta')
    await expect(cta).toBeVisible()
    const bounds = await cta.boundingBox()
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(width === 1440 ? 900 : 812)
    await cta.focus()
    expect(await cta.evaluate(node => getComputedStyle(node).outlineStyle)).toBe('solid')
    expect(await cta.evaluate(node => {
      const r = node.getBoundingClientRect()
      return node.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2))
    })).toBe(true)
    await expect(page.locator('.closed-row')).toHaveCount(6)
    await page.getByRole('button', { name: /Mostrar mais/ }).click()
    await expect(page.locator('.closed-row')).toHaveCount(12)
    await expect(page.locator('.rail-upcoming .rail-item')).toHaveCount(20)
    await page.locator('.rail-upcoming .rail-item').last().focus()
    expect(await horizontalOverflow(page)).toEqual({ page: width, width })
    expect(await elementsBeyondViewport(page)).toEqual([])
  })
}

for (const [shape, w, h] of [['paisagem', 1000, 670], ['retrato', 843, 1074], ['quadrada', 1000, 960]] as const) {
  test(`hero ${shape}: contain, transição segura e caixa estável após mídia lenta`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const lot = makeLot(1, 'live')
    await mockApi(page, { lots: [lot] })
    let release = () => {}
    const gate = new Promise<void>(resolve => { release = resolve })
    let downloads = 0
    await page.route(`**${lot.image_url}`, async route => {
      downloads++
      await gate
      await route.fulfill({ contentType: 'image/svg+xml', body: `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect width="100%" height="100%" fill="#967350"/></svg>` })
    })
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    await expect(page.locator('.featured-info')).toBeVisible()
    const before = await box(page, '.featured-info')
    release()
    await expect.poll(() => page.locator('.featured-art img').evaluate((img: HTMLImageElement) => img.naturalWidth)).toBe(w)
    expect(await box(page, '.featured-info')).toEqual(before)
    expect(downloads).toBe(1)
    expect(await page.locator('.featured-art img').evaluate(node => getComputedStyle(node).objectFit)).toBe('contain')
    const transition = await page.locator('.featured-art').evaluate(node => ({
      content: getComputedStyle(node, '::after').content,
      pointerEvents: getComputedStyle(node, '::after').pointerEvents,
    }))
    if (shape === 'paisagem') {
      expect(transition.content).toBe('""')
      expect(transition.pointerEvents).toBe('none')
    } else expect(transition.content).toBe('none')
    for (const width of [375, 320]) {
      await page.setViewportSize({ width, height: 812 })
      expect(await page.locator('.featured-art').evaluate(node => getComputedStyle(node, '::after').content)).toBe('none')
      expect(await elementsBeyondViewport(page)).toEqual([])
    }
  })
}

test('hero 503: fallback legível sem transição e CTA funcional', async ({ page }) => {
  await mockApi(page, { lots: makeLots({ live: 1 }), images: 'broken' })
  await page.goto('/')
  await expect(page.locator('.featured-art')).toContainText('Imagem indisponível')
  expect(await page.locator('.featured-art').evaluate(node => getComputedStyle(node, '::after').content)).toBe('none')
  await page.locator('.featured-cta').click()
  await expect(page).toHaveURL(new RegExp(`/lots/${lotId(1)}$`))
})

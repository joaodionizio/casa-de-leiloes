// Marca ÁTRIO (Story 2.5, rodada de 25/10/2026): nome visível, títulos da aba, nome
// acessível do link da marca e o header responsivo com a nova marca. A API é simulada.
import { expect, test, type Locator, type Page } from '@playwright/test'
import { lotId, makeLots, mockApi } from './support/mockApi'

const LOTS = makeLots({ live: 3, scheduled: 1, ended: 2 })
const TOLERANCE = 2
const OLD_NAME = 'Casa de Leilões'
const BRAND_NAME = 'ÁTRIO — Leilões de Arte — ir para a vitrine'

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

// `b` fica à direita de `a` ou abaixo dele (header que quebra de linha): nunca por cima.
function sideBySideOrBelow(a: Rect, b: Rect): boolean {
  return b.x >= a.right - TOLERANCE || b.y >= a.bottom - TOLERANCE
}

async function titleOf(page: Page): Promise<string> {
  return page.title()
}

test.describe('nome e títulos', () => {
  test('o título de cada página termina em "— ÁTRIO" e o nome antigo não aparece', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })

    await page.goto('/')
    await expect(page.locator('.featured')).toBeVisible()
    expect(await titleOf(page)).toBe('Vitrine — ÁTRIO')

    await page.goto(`/lots/${lotId(2)}`)
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 2')
    expect(await titleOf(page)).toBe('Obra de teste 2 — ÁTRIO')

    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Entrar', level: 1 })).toBeVisible()
    expect(await titleOf(page)).toBe('Entrar — ÁTRIO')

    await page.goto('/nao-existe')
    await expect(page.locator('#not-found-title')).toBeVisible()
    expect(await titleOf(page)).toBe('Página não encontrada — ÁTRIO')
    await expect(page.locator('body')).toContainText('nenhuma página do ÁTRIO')
    await expect(page.locator('body')).not.toContainText(OLD_NAME)
  })

  test('lote inexistente e áreas do leiloeiro também usam o nome novo', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS, session: 'AUCTIONEER' })

    await page.goto('/auctioneer/lots/new')
    await expect(page.getByRole('heading', { name: 'Buscar obras' })).toBeVisible()
    expect(await titleOf(page)).toBe('Criar lote — ÁTRIO')

    await page.goto('/auctioneer/lots')
    await expect(page.getByRole('heading', { name: 'Meus lotes', level: 1 })).toBeVisible()
    expect(await titleOf(page)).toBe('Meus lotes — ÁTRIO')

    await page.goto('/lots/00000000-0000-4000-8000-00000000dead')
    await expect(page.locator('#lot-title')).toHaveText('Lote indisponível ou não encontrado')
    expect(await titleOf(page)).toBe('Lote — ÁTRIO')
  })

  test('o HTML inicial, antes de qualquer JavaScript, já traz ÁTRIO', async ({ page }) => {
    await mockApi(page, { lots: LOTS })
    const response = await page.request.get('/')
    const html = await response.text()
    expect(html).toContain('<title>ÁTRIO — Leilões de Arte</title>')
    expect(html).not.toContain(OLD_NAME)
  })

  test('o favicon é o símbolo ÁTRIO, em SVG local', async ({ page }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/')
    const href = await page.locator('link[rel="icon"]').getAttribute('href')
    expect(href).toBe('/favicon.svg')
    const response = await page.request.get('/favicon.svg')
    expect(response.ok()).toBe(true)
    expect(response.headers()['content-type']).toContain('image/svg+xml')
    const svg = await response.text()
    expect(svg).toContain('<title>ÁTRIO</title>')
    // Marca própria: sem raster embutido e sem referência remota.
    expect(svg).not.toContain('data:image')
    expect(svg).not.toMatch(/https?:\/\/(?!www\.w3\.org)/)
  })
})

test.describe('marca no header: acessibilidade', () => {
  test('o link da marca tem um nome só, o SVG é decorativo e leva à vitrine', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto(`/lots/${lotId(2)}`)
    await expect(page.locator('#lot-title')).toHaveText('Obra de teste 2')

    const brand = page.getByRole('link', { name: BRAND_NAME, exact: true })
    await expect(brand).toHaveCount(1)
    // O símbolo não entra na árvore de acessibilidade: nada de "símbolo ÁTRIO" + "ÁTRIO".
    const symbol = brand.locator('svg')
    await expect(symbol).toHaveAttribute('aria-hidden', 'true')
    await expect(symbol).toHaveAttribute('focusable', 'false')
    await expect(symbol.locator('title')).toHaveCount(0)
    await expect(brand.locator('img')).toHaveCount(0)
    // A palavra visível é o texto real "ÁTRIO", não uma imagem de texto.
    await expect(brand.locator('.site-brand-name')).toHaveText('ÁTRIO')
    // Nenhum "img" no header: a marca não aparece duas vezes para o leitor de tela.
    await expect(page.locator('header').getByRole('img')).toHaveCount(0)

    await brand.click()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.locator('.featured')).toBeVisible()
  })
})

test.describe('símbolo ÁTRIO', () => {
  function luminance(hex: string): number {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
  }

  test('é alto e estreito, tem duas faces (clara à esquerda, intensa à direita) e o favicon usa a mesma geometria', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })
    await page.goto('/')
    await expect(page.locator('.featured')).toBeVisible()

    // Silhueta alta e fina, não uma ferradura larga (estrutura, não pixel).
    const box = await rect(page.locator('.site-header .site-brand svg'))
    expect((box.bottom - box.y) / (box.right - box.x)).toBeGreaterThan(1.2)

    const faces = page.locator('.site-header .site-brand svg path')
    await expect(faces).toHaveCount(2)
    const fills = await faces.evaluateAll((paths) => paths.map((p) => p.getAttribute('fill') ?? ''))
    const geometry = await faces.evaluateAll((paths) => paths.map((p) => p.getAttribute('d') ?? ''))
    expect(fills[0]).toMatch(/^#[0-9a-f]{6}$/i)
    expect(fills[1]).toMatch(/^#[0-9a-f]{6}$/i)
    expect(fills[0]).not.toBe(fills[1])
    // Duas faces, não um gradiente contínuo: a esquerda é mais clara que a direita.
    expect(luminance(fills[0])).toBeGreaterThan(luminance(fills[1]))
    await expect(page.locator('.site-header .site-brand svg linearGradient, .site-brand svg radialGradient')).toHaveCount(0)

    // O favicon desenha exatamente os mesmos caminhos e as mesmas cores.
    const favicon = await (await page.request.get('/favicon.svg')).text()
    const faviconPaths = [...favicon.matchAll(/<path fill="([^"]+)" d="([^"]+)"/g)].map(
      (match) => ({ fill: match[1], d: match[2] }),
    )
    expect(faviconPaths).toEqual(fills.map((fill, index) => ({ fill, d: geometry[index] })))
  })

  test('a palavra é leve (não bold) e o descritor é secundário', async ({ page }) => {
    await mockApi(page, { lots: LOTS })
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto('/')
    const name = await page.locator('.site-header .site-brand-name').evaluate((el) => {
      const style = getComputedStyle(el)
      return { weight: Number(style.fontWeight), size: parseFloat(style.fontSize) }
    })
    const tagline = await page.locator('.site-header .site-brand-tagline').evaluate((el) => {
      const style = getComputedStyle(el)
      return { weight: Number(style.fontWeight), size: parseFloat(style.fontSize) }
    })
    expect(name.weight).toBeLessThanOrEqual(400)
    expect(tagline.size).toBeLessThan(name.size)
    expect(tagline.weight).toBeLessThanOrEqual(400)
  })

  test('Label in Name: o nome acessível contém todo o texto visível do link da marca', async ({
    page,
  }) => {
    await mockApi(page, { lots: LOTS })
    for (const width of [1440, 375, 320]) {
      await page.setViewportSize({ width, height: 812 })
      await page.goto('/')
      await expect(page.locator('.featured')).toBeVisible()
      const brand = page.getByRole('link', { name: BRAND_NAME, exact: true })
      await expect(brand).toBeVisible()
      const visible = ((await brand.innerText()) ?? '').split('\n').map((line) => line.trim()).filter(Boolean)
      expect(visible.length, `${width}`).toBeGreaterThan(0)
      for (const piece of visible) {
        expect(BRAND_NAME, `${width}: "${piece}"`).toContain(piece)
      }
      // O descritor visível só existe onde há folga (desktop).
      expect(visible.includes('Leilões de Arte'), `${width}`).toBe(width === 1440)
    }
  })
})

const VIEWPORTS = [
  { name: '1440×900', width: 1440, height: 900, tagline: true },
  { name: '375×812', width: 375, height: 812, tagline: false },
  { name: '320×812', width: 320, height: 812, tagline: false },
]

for (const viewport of VIEWPORTS) {
  test.describe(`header com ÁTRIO em ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } })

    test(`${viewport.tagline ? 'mostra' : 'esconde'} "Leilões de Arte"; símbolo e nome sempre visíveis`, async ({
      page,
    }) => {
      await mockApi(page, { lots: LOTS })
      await page.goto('/')
      await expect(page.locator('.featured')).toBeVisible()

      await expect(page.locator('.site-header .site-brand svg')).toBeVisible()
      await expect(page.locator('.site-header .site-brand-name')).toBeVisible()
      await expect(page.locator('.site-header .site-brand-name')).toHaveText('ÁTRIO')
      if (viewport.tagline) {
        await expect(page.locator('.site-header .site-brand-tagline')).toBeVisible()
        await expect(page.locator('.site-header .site-brand-tagline')).toHaveText('Leilões de Arte')
      } else {
        await expect(page.locator('.site-header .site-brand-tagline')).toBeHidden()
      }
    })

    test('anônimo: marca, Vitrine e Entrar cabem, sem sobrepor e sem rolagem horizontal', async ({
      page,
    }) => {
      await mockApi(page, { lots: LOTS })
      await page.goto('/')
      await expect(page.locator('.featured')).toBeVisible()

      const brand = await rect(page.locator('.site-header .site-brand'))
      const nav = await rect(page.getByRole('navigation', { name: 'Principal' }))
      const login = await rect(page.getByRole('link', { name: 'Entrar', exact: true }))
      for (const part of [brand, nav, login]) {
        expect(part.x).toBeGreaterThanOrEqual(-TOLERANCE)
        expect(part.right).toBeLessThanOrEqual(viewport.width + TOLERANCE)
      }
      expect(sideBySideOrBelow(brand, nav)).toBe(true)
      expect(sideBySideOrBelow(brand, login)).toBe(true)
      const overflow = await page.evaluate(() => ({
        page: document.documentElement.scrollWidth,
        width: document.documentElement.clientWidth,
      }))
      expect(overflow.page).toBeLessThanOrEqual(overflow.width)
    })

    test('AUCTIONEER: a marca não esconde nem esmaga nenhuma navegação', async ({
      page,
    }) => {
      await mockApi(page, { lots: LOTS, session: 'AUCTIONEER' })
      await page.goto('/')
      await expect(page.getByRole('button', { name: 'Sair' })).toBeVisible()

      const nav = page.getByRole('navigation', { name: 'Principal' })
      const brand = await rect(page.locator('.site-header .site-brand'))
      for (const name of ['Vitrine', 'Criar lote', 'Meus lotes']) {
        const link = nav.getByRole('link', { name })
        await expect(link).toBeVisible()
        const box = await rect(link)
        expect(box.x, name).toBeGreaterThanOrEqual(-TOLERANCE)
        expect(box.right, name).toBeLessThanOrEqual(viewport.width + TOLERANCE)
        expect(sideBySideOrBelow(brand, box), name).toBe(true)
      }
      const logout = await rect(page.getByRole('button', { name: 'Sair' }))
      expect(logout.right).toBeLessThanOrEqual(viewport.width + TOLERANCE)
      expect(sideBySideOrBelow(brand, logout)).toBe(true)
      const overflow = await page.evaluate(() => ({
        page: document.documentElement.scrollWidth,
        width: document.documentElement.clientWidth,
      }))
      expect(overflow.page).toBeLessThanOrEqual(overflow.width)
    })

    test('BIDDER: marca e conta sem sobreposição', async ({ page }) => {
      await mockApi(page, { lots: LOTS, session: 'BIDDER' })
      await page.goto('/')
      await expect(page.getByRole('button', { name: 'Sair' })).toBeVisible()

      const brand = await rect(page.locator('.site-header .site-brand'))
      const account = await rect(page.locator('.account'))
      expect(account.right).toBeLessThanOrEqual(viewport.width + TOLERANCE)
      expect(sideBySideOrBelow(brand, account)).toBe(true)
    })
  })
}

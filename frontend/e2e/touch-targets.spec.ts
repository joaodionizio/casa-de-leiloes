// Alvos de toque (Story 2.5, review L3): o header e "← Vitrine" precisam de uma área
// acionável próxima de 44 px de altura, sem aumentar visualmente a fonte nem o header.
// A área vem de um pseudo-elemento do próprio link/botão; por isso o teste mede o que o
// toque acerta (`elementFromPoint`), não a caixa visual do elemento.
import { expect, test, type Locator, type Page } from '@playwright/test'
import { lotId, makeLots, mockApi } from './support/mockApi'

const LOTS = makeLots({ live: 3, scheduled: 1, ended: 2 })
const MIN_HIT_HEIGHT = 43 // 44 px com 1 px de tolerância de arredondamento
const SCAN = 40

// Altura contínua, a partir do centro do elemento, em que o toque cai nele ou num filho.
async function hitHeight(page: Page, target: Locator): Promise<number> {
  const box = await target.boundingBox()
  if (box === null) throw new Error('elemento sem caixa')
  const x = box.x + box.width / 2
  const y = box.y + box.height / 2
  const handle = await target.elementHandle()
  return page.evaluate(
    ({ el, cx, cy, scan }) => {
      const hits = (dy: number) => {
        const hit = document.elementFromPoint(cx, cy + dy)
        return hit !== null && (el as Element).contains(hit)
      }
      let up = 0
      while (up < scan && hits(-(up + 1))) up += 1
      let down = 0
      while (down < scan && hits(down + 1)) down += 1
      return up + down + 1
    },
    { el: handle, cx: x, cy: y, scan: SCAN },
  )
}

const VIEWPORTS = [
  { width: 1440, height: 900 },
  { width: 375, height: 812 },
  { width: 320, height: 812 },
]

for (const viewport of VIEWPORTS) {
  test.describe(`${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport })

    test('AUCTIONEER: marca, navegação e Sair têm alvo de ~44 px', async ({ page }) => {
      await mockApi(page, { lots: LOTS, session: 'AUCTIONEER' })
      await page.goto('/')
      await expect(page.getByRole('button', { name: 'Sair' })).toBeVisible()

      const nav = page.getByRole('navigation', { name: 'Principal' })
      const targets: Record<string, Locator> = {
        marca: page.locator('.site-brand'),
        Vitrine: nav.getByRole('link', { name: 'Vitrine' }),
        'Criar lote': nav.getByRole('link', { name: 'Criar lote' }),
        'Meus lotes': nav.getByRole('link', { name: 'Meus lotes' }),
        Sair: page.getByRole('button', { name: 'Sair' }),
      }
      for (const [name, locator] of Object.entries(targets)) {
        expect(await hitHeight(page, locator), name).toBeGreaterThanOrEqual(MIN_HIT_HEIGHT)
      }
    })

    test('anônimo: Entrar tem alvo de ~44 px', async ({ page }) => {
      await mockApi(page, { lots: LOTS })
      await page.goto('/')
      const login = page.getByRole('link', { name: 'Entrar', exact: true })
      await expect(login).toBeVisible()
      expect(await hitHeight(page, login)).toBeGreaterThanOrEqual(MIN_HIT_HEIGHT)
    })

    test('"← Vitrine" na página do lote tem alvo de ~44 px', async ({ page }) => {
      await mockApi(page, { lots: LOTS })
      await page.goto(`/lots/${lotId(2)}`)
      await expect(page.locator('#lot-title')).toBeVisible()
      expect(await hitHeight(page, page.locator('.back-link'))).toBeGreaterThanOrEqual(
        MIN_HIT_HEIGHT,
      )
    })

    test('o ganho de alvo não estoura o header nem cria rolagem horizontal', async ({
      page,
    }) => {
      await mockApi(page, { lots: LOTS, session: 'AUCTIONEER' })
      await page.goto('/')
      await expect(page.getByRole('button', { name: 'Sair' })).toBeVisible()
      const header = await page.locator('.site-header').boundingBox()
      // Teto folgado: no celular o header empilha marca, navegação e conta.
      expect(header?.height ?? 0).toBeLessThanOrEqual(viewport.width >= 1024 ? 70 : 190)
      const overflow = await page.evaluate(() => ({
        page: document.documentElement.scrollWidth,
        width: document.documentElement.clientWidth,
      }))
      expect(overflow.page).toBeLessThanOrEqual(overflow.width)
    })
  })
}

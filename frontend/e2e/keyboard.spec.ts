// Teclado e foco (Story 2.5, D11, CAP-12): o que só um navegador real prova.
import { expect, test, type Page } from '@playwright/test'
import { lotId, makeLots, mockApi } from './support/mockApi'

const LOTS = makeLots({ live: 3, scheduled: 2, ended: 8 })

interface Focused {
  tag: string
  label: string
  outlineStyle: string
  outlineWidth: number
}

async function focused(page: Page): Promise<Focused> {
  return page.evaluate(() => {
    const element = document.activeElement as HTMLElement
    const style = getComputedStyle(element)
    return {
      tag: element.tagName.toLowerCase(),
      label:
        element.getAttribute('aria-label') ?? (element.textContent ?? '').trim(),
      outlineStyle: style.outlineStyle,
      outlineWidth: parseFloat(style.outlineWidth),
    }
  })
}

test('Tab chega aos controles principais, na ordem, e o foco é visível', async ({
  page,
}) => {
  await mockApi(page, { lots: LOTS })
  await page.goto('/')
  await expect(page.locator('.closed-list')).toBeVisible()

  const wanted = [
    /^ÁTRIO — Leilões de Arte — ir para a vitrine$/,
    /^Vitrine$/,
    /^Entrar$/,
    /^Ver lote: /,
    /^Obra de teste 2\. Ao vivo\./,
    /^Obra de teste 201\. Encerrado/,
    /^Mostrar mais encerrados$/,
  ]
  const seen: string[] = []
  let next = 0
  for (let step = 0; step < 60 && next < wanted.length; step += 1) {
    await page.keyboard.press('Tab')
    const current = await focused(page)
    if (wanted[next].test(current.label)) {
      next += 1
      seen.push(current.label)
      // Foco visível por estilo, não por cor: contorno sólido de pelo menos 2 px.
      expect(current.outlineStyle, current.label).not.toBe('none')
      expect(current.outlineWidth, current.label).toBeGreaterThanOrEqual(2)
    }
  }

  expect(seen).toHaveLength(wanted.length)
})

test('Enter no destaque abre o lote e leva o foco ao h1', async ({ page }) => {
  await mockApi(page, { lots: LOTS })
  await page.goto('/')
  const cta = page.locator('.featured-cta')

  await cta.focus()
  await page.keyboard.press('Enter')

  await expect(page).toHaveURL(new RegExp(`/lots/${lotId(1)}$`))
  await expect(page.locator('h1#lot-title')).toHaveText('Obra de teste 1')
  await expect(page.locator('h1#lot-title')).toBeFocused()
})

test('no primeiro carregamento o foco não é roubado para o título', async ({ page }) => {
  await mockApi(page, { lots: LOTS })

  await page.goto(`/lots/${lotId(1)}`)
  await expect(page.locator('#lot-title')).toHaveText('Obra de teste 1')

  await expect(page.locator('#lot-title')).not.toBeFocused()
})

test('Back devolve o foco ao link do lote de onde a pessoa saiu', async ({ page }) => {
  await mockApi(page, { lots: LOTS })
  await page.goto('/')
  const link = page.locator(`[data-lot-id="${lotId(3)}"]`)

  await link.focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('h1#lot-title')).toBeFocused()
  await page.goBack()

  await expect(page.locator(`[data-lot-id="${lotId(3)}"]`)).toBeFocused()
})

test('"Mostrar mais encerrados" move o foco para o primeiro item revelado', async ({
  page,
}) => {
  await mockApi(page, { lots: LOTS })
  await page.goto('/')
  const more = page.getByRole('button', { name: 'Mostrar mais encerrados' })

  await more.focus()
  await page.keyboard.press('Enter')

  await expect(page.locator('.closed-row')).toHaveCount(8)
  await expect(
    page.locator('.closed-row').nth(6).locator('a'),
  ).toBeFocused()
})

test('navegar pelo header move o foco para o título da nova vista', async ({ page }) => {
  await mockApi(page, { lots: LOTS, session: 'AUCTIONEER' })
  await page.goto('/')
  const nav = page.getByRole('navigation', { name: 'Principal' })

  await nav.getByRole('link', { name: 'Meus lotes' }).click()
  await expect(page.getByRole('heading', { name: 'Meus lotes', level: 1 })).toBeFocused()

  await nav.getByRole('link', { name: 'Criar lote' }).click()
  await expect(page.locator('#catalog-title')).toBeFocused()

  await page.goto('/lots/abc')
  await expect(page.locator('h1:visible')).toHaveText('Página não encontrada')
})

test('no celular os rails rolam com o Tab (o foco traz o item para a tela)', async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await mockApi(page, { lots: makeLots({ live: 8 }) })
  await page.goto('/')
  const last = page.locator('.rail-live .rail-link').last()

  await last.focus()

  const visible = await page.evaluate(() => {
    const rail = document.querySelector('.rail-live')!.getBoundingClientRect()
    const rect = document.activeElement!.getBoundingClientRect()
    return rect.left >= rail.left - 2 && rect.right <= rail.right + 2
  })
  expect(visible).toBe(true)
})

// L1 (code review): `.rail` tem `overflow-x: auto`, e o `overflow-y` vira `auto` junto, então o
// contorno de foco (largura + `outline-offset`), desenhado para fora do link, era cortado no
// topo e à esquerda do primeiro item. Não basta conferir a largura do contorno: conferimos que
// ele cabe inteiro dentro da caixa do rail, nas quatro bordas, no primeiro e no último item.
async function ringRoom(page: Page, selector: string) {
  return page.evaluate((sel) => {
    const link = document.querySelector(sel) as HTMLElement
    const style = getComputedStyle(link)
    const ring = parseFloat(style.outlineOffset) + parseFloat(style.outlineWidth)
    const box = link.getBoundingClientRect()
    const rail = (link.closest('.rail') as HTMLElement).getBoundingClientRect()
    return {
      ring,
      left: box.left - ring - rail.left,
      top: box.top - ring - rail.top,
      right: rail.right - (box.right + ring),
      bottom: rail.bottom - (box.bottom + ring),
    }
  }, selector)
}

for (const rail of ['live', 'upcoming']) {
  test(`o contorno de foco do rail "${rail}" não é cortado (primeiro e último item)`, async ({
    page,
  }) => {
    await mockApi(page, { lots: makeLots({ live: 8, scheduled: 8 }) })
    await page.goto('/')
    const links = page.locator(`.rail-${rail} .rail-link`)

    await links.first().focus()
    await expect(links.first()).toBeFocused()
    const first = await ringRoom(page, `.rail-${rail} li:first-child .rail-link`)
    expect(first.ring).toBeGreaterThanOrEqual(6)
    for (const side of ['left', 'top', 'bottom'] as const) {
      expect(first[side], `primeiro, ${side}`).toBeGreaterThanOrEqual(-0.5)
    }

    await links.last().focus()
    await expect(links.last()).toBeFocused()
    // Dá tempo ao `scroll-snap` de assentar antes de medir a borda direita.
    await expect
      .poll(async () => (await ringRoom(page, `.rail-${rail} li:last-child .rail-link`)).right)
      .toBeGreaterThanOrEqual(-0.5)
    const last = await ringRoom(page, `.rail-${rail} li:last-child .rail-link`)
    for (const side of ['top', 'bottom'] as const) {
      expect(last[side], `último, ${side}`).toBeGreaterThanOrEqual(-0.5)
    }
  })
}

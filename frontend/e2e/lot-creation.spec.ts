import { expect, test } from '@playwright/test'
import { makeLot, mockApi } from './support/mockApi'

for (const width of [1440, 768, 375, 320]) {
  test(`criação ${width}: microcopy acessível, validação, revisão e payload preservados`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 1440 ? 900 : 812 })
    await mockApi(page, { session: 'AUCTIONEER' })
    const lot = makeLot(1, 'scheduled')
    const artwork = { ...lot, image_id: '2d484387-2509-5e8e-2c43-22f998197201' }
    await page.route('**/api/catalog/artworks?*', route => route.fulfill({ json: { items: [artwork] } }))
    await page.route(`**/api/catalog/artworks/${lot.external_id}`, route => route.fulfill({ json: artwork }))
    const posts: unknown[] = []
    let release = () => {}
    const gate = new Promise<void>(resolve => { release = resolve })
    await page.route('**/api/lots', async route => {
      if (route.request().method() !== 'POST') return route.fallback()
      const body = route.request().postDataJSON()
      posts.push(body)
      await gate
      await route.fulfill({ status: 201, json: { ...artwork, ...body, starts_at: '2099-01-01T12:00:00Z', created_at: '2099-01-01T12:00:00Z' } })
    })
    await page.goto('/auctioneer/lots/new')
    await page.getByLabel('Termo de busca').fill('Obra')
    await page.getByRole('button', { name: 'Buscar', exact: true }).click()
    await page.getByRole('button', { name: /Obra de teste 1/ }).click()
    await page.getByRole('button', { name: 'Criar lote com esta obra' }).click()
    const fields = [
      ['Lance inicial', 'Valor mínimo aceito para o primeiro lance deste lote.', 'lot-starting-bid'],
      ['Incremento mínimo', 'Valor mínimo que cada novo lance deverá acrescentar ao lance atual.', 'lot-min-increment'],
    ]
    for (const [label, description, id] of fields) {
      const field = page.getByLabel(label, { exact: true })
      await expect(page.getByText(description, { exact: true })).toBeVisible()
      await expect(field).toHaveAttribute('aria-describedby', `${id}-description ${id}-hint`)
      await expect(field).toHaveAccessibleDescription(new RegExp(description))
    }
    await page.getByRole('button', { name: 'Revisar lote' }).click()
    await expect(page.getByLabel('Lance inicial', { exact: true })).toBeFocused()
    await expect(page.getByLabel('Lance inicial', { exact: true })).toHaveAttribute('aria-describedby', 'lot-starting-bid-description lot-starting-bid-hint lot-starting-bid-feedback')
    await page.getByLabel('Lance inicial', { exact: true }).fill('1.250,50')
    await page.getByLabel('Incremento mínimo', { exact: true }).fill('5,50')
    await page.getByLabel('Término', { exact: true }).fill('2099-01-02T12:00')
    const end = await page.getByLabel('Término', { exact: true }).evaluate((input: HTMLInputElement) => new Date(input.value).toISOString())
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    for (const input of await page.locator('.lot-form input:not([type=radio]), .lot-form button').all()) {
      const rect = await input.boundingBox()
      expect(rect!.x).toBeGreaterThanOrEqual(0)
      expect(rect!.x + rect!.width).toBeLessThanOrEqual(width + 1)
    }
    await page.getByRole('button', { name: 'Revisar lote' }).click()
    await expect(page.getByRole('heading', { name: 'Revise o lote' })).toBeFocused()
    await expect(page.locator('.lot-terms')).toContainText('1.250,50')
    await page.getByRole('button', { name: 'Publicar lote', exact: true }).evaluate((node: HTMLButtonElement) => { node.click(); node.click() })
    await expect(page.getByRole('button', { name: 'Publicando…' })).toBeDisabled()
    expect(posts).toEqual([{ external_id: lot.external_id, starting_bid_cents: 125050, min_increment_cents: 550, starts_at: null, ends_at: end }])
    release()
    await expect(page.getByRole('heading', { name: 'Lote criado' })).toBeVisible()
  })
}

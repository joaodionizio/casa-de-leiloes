import assert from 'node:assert/strict'
import { test } from 'node:test'
import { documentTitle, PRODUCT_NAME, PRODUCT_TAGLINE } from './brand.ts'

test('o nome do produto é ÁTRIO e o descritor é Leilões de Arte', () => {
  assert.equal(PRODUCT_NAME, 'ÁTRIO')
  assert.equal(PRODUCT_TAGLINE, 'Leilões de Arte')
})

test('documentTitle junta a página e o produto com travessão', () => {
  assert.equal(documentTitle('Vitrine'), 'Vitrine — ÁTRIO')
  assert.equal(documentTitle('Cliff Walk at Pourville'), 'Cliff Walk at Pourville — ÁTRIO')
  assert.equal(documentTitle('Meus lotes'), 'Meus lotes — ÁTRIO')
})

test('documentTitle não duplica o nome quando a página já é o produto', () => {
  assert.equal(documentTitle('ÁTRIO'), 'ÁTRIO')
})

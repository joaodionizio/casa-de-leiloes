// Nome visível do produto (identidade ÁTRIO, 25/10/2026). Só a interface muda de nome:
// repositório, banco, módulos e URLs técnicas continuam como estão (AD-30).
export const PRODUCT_NAME = 'ÁTRIO'
export const PRODUCT_TAGLINE = 'Leilões de Arte'

// Título da aba: "{página} — ÁTRIO". Se a página já é o nome do produto, não repete.
export function documentTitle(page: string): string {
  return page === PRODUCT_NAME ? PRODUCT_NAME : `${page} — ${PRODUCT_NAME}`
}

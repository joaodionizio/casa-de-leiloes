// Mesmo contrato do Python: code points e categorias Unicode Ll/Lu/Nd/P/S.
// Espaços contam no comprimento e não formam um grupo; não normalizamos a senha.
export const PASSWORD_RULE = 'Use de 8 a 1024 caracteres e pelo menos 3 grupos: minúsculas, maiúsculas, números e símbolos.'
export function passwordStrength(password: string) {
  const length = Array.from(password).length
  const groups = [
    { label: 'Minúsculas', met: /\p{Ll}/u.test(password) },
    { label: 'Maiúsculas', met: /\p{Lu}/u.test(password) },
    { label: 'Números', met: /\p{Nd}/u.test(password) },
    { label: 'Símbolos', met: /[\p{P}\p{S}]/u.test(password) },
  ]
  const groupCount = groups.filter(group => group.met).length
  return { length, groups, groupCount, valid: length >= 8 && length <= 1024 && groupCount >= 3 }
}
export function confirmationError(password: string, confirmation: string): string | undefined {
  if (confirmation.length === 0) return 'Confirme sua senha.'
  if (confirmation !== password) return 'As senhas não coincidem.'
  return undefined
}

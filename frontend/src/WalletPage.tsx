import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { fetchWallet } from './api/wallet'
import type { WalletReadFailure, WalletResponse } from './api/wallet'
import MoneyField from './MoneyField'
import { formatCents, moneyErrorMessage, parseReaisToCents } from './money'
import { pendingDepositOf, startDeposit, type DepositOutcome } from './walletDeposit'
import {
  depositFailureNotice,
  depositSuccessText,
  failureBelongsToField,
  rereadNotice,
  type WalletNotice,
} from './walletFeedback'

type ReadState =
  | { status: 'loading' }
  | { status: 'ready'; wallet: WalletResponse }
  | { status: 'failed'; failure: WalletReadFailure }

interface WalletPageProps {
  // A conta da sessão (e-mail): o depósito em andamento é dela, e só dela.
  owner: string
  focusHeading: boolean
  onSessionExpired: () => void
}

const NOTICE_SYMBOL = { success: '✓ ', error: '✕ ', uncertain: '! ' } as const

// Carteira do licitante (Story 3.1, DESIGN §10, EXPERIENCE §8): três números, com o
// disponível em destaque, e o depósito simulado. Os valores vêm sempre do servidor
// (a resposta do `POST` ou de um `GET`), nunca de uma soma no front. Monta a cada
// navegação, então sempre relê o servidor.
//
// Envio (P8): o botão e o campo ficam bloqueados enquanto o `POST` está pendente e
// nunca há um segundo `POST` automático. Um erro ambíguo (rede, 5xx) faz uma única
// releitura de `GET /api/wallet`; a tela só mostra o saldo que o servidor devolver e
// nunca afirma que o depósito entrou sem essa confirmação. O depósito pendente vive em
// `walletDeposit.ts`, fora desta página: voltar à carteira durante o envio (outro
// clique em "Carteira", Back/Forward) mantém o bloqueio e mostra o resultado.
function WalletPage({ owner, focusHeading, onSessionExpired }: WalletPageProps) {
  const [read, setRead] = useState<ReadState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [amountText, setAmountText] = useState('')
  const [fieldError, setFieldError] = useState<string | undefined>(undefined)
  const [notice, setNotice] = useState<WalletNotice | null>(null)
  const [pending, setPending] = useState(() => pendingDepositOf(owner) !== null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const amountRef = useRef<HTMLInputElement>(null)
  const mountedRef = useRef(true)
  // Sobe a cada saldo vindo de um depósito: uma leitura iniciada antes dele é mais
  // velha e não pode sobrescrevê-lo.
  const walletVersionRef = useRef(0)
  // O pai recria `onSessionExpired` a cada renderização; a referência evita que isso
  // dispare uma nova busca.
  const expiredRef = useRef(onSessionExpired)

  useEffect(() => {
    expiredRef.current = onSessionExpired
  }, [onSessionExpired])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (focusHeading) headingRef.current?.focus()
  }, [focusHeading])

  useEffect(() => {
    const controller = new AbortController()
    const version = walletVersionRef.current
    fetchWallet(controller.signal).then((result) => {
      if (controller.signal.aborted) return
      if (result.ok) {
        if (walletVersionRef.current === version) {
          setRead({ status: 'ready', wallet: result.wallet })
        }
      } else if (result.failure === 'unauthorized') {
        expiredRef.current()
      } else if (walletVersionRef.current === version) {
        setRead({ status: 'failed', failure: result.failure })
      }
    })
    return () => controller.abort()
  }, [attempt])

  // Mostra o resultado de um depósito desta conta. Quem chama confere antes se esta
  // montagem ainda vale.
  const showOutcome = useCallback(
    (outcome: DepositOutcome, amountCents: number) => {
      setPending(false)

      if (outcome.kind === 'confirmed') {
        walletVersionRef.current += 1
        setRead({ status: 'ready', wallet: outcome.wallet })
        setAmountText('')
        setNotice({ kind: 'success', text: depositSuccessText(amountCents) })
        return
      }
      if (outcome.kind === 'uncertain') {
        const { reread } = outcome
        if (reread.ok) {
          walletVersionRef.current += 1
          setRead({ status: 'ready', wallet: reread.wallet })
        } else if (reread.failure === 'unauthorized') {
          expiredRef.current()
          return
        }
        setNotice(rereadNotice(reread))
        return
      }
      if (outcome.failure === 'unauthorized') {
        expiredRef.current()
        return
      }
      const refusal = depositFailureNotice(outcome.failure)
      if (failureBelongsToField(outcome.failure)) {
        setFieldError(refusal.text)
        amountRef.current?.focus()
      } else {
        setNotice(refusal)
      }
    },
    [],
  )

  // Ao montar com um depósito desta conta ainda pendente (a página remontou durante o
  // envio): `pending` já nasce verdadeiro, e a página espera o mesmo resultado, sem
  // novo `POST`.
  useEffect(() => {
    const entry = pendingDepositOf(owner)
    if (entry === null) return
    let active = true
    entry.outcome.then((outcome) => {
      if (active) showOutcome(outcome, entry.amountCents)
    })
    return () => {
      active = false
    }
  }, [owner, showOutcome])

  function retry() {
    setRead({ status: 'loading' })
    setAttempt((count) => count + 1)
  }

  function handleAmountChange(value: string) {
    setAmountText(value)
    setFieldError(undefined)
    // Um "confirmado" antigo ao lado de um valor novo, ainda não enviado, engana. O
    // aviso de resultado incerto fica: ele é justamente o que ler antes de repetir.
    setNotice((current) => (current?.kind === 'success' ? null : current))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pendingDepositOf(owner) !== null) return
    const parsed = parseReaisToCents(amountText)
    if (!parsed.ok) {
      setNotice(null)
      setFieldError(moneyErrorMessage(parsed.error, amountText))
      amountRef.current?.focus()
      return
    }
    const entry = startDeposit(owner, parsed.cents)
    if (entry === null) return
    setPending(true)
    setNotice(null)
    setFieldError(undefined)
    entry.outcome.then((outcome) => {
      if (mountedRef.current) showOutcome(outcome, entry.amountCents)
    })
  }

  // O aviso de sucesso e o de resultado incerto vão para uma região `status` sempre
  // montada (o leitor de tela anuncia a mudança de conteúdo); o erro, para um `alert`.
  const statusNotice = notice !== null && notice.kind !== 'error' ? notice : null
  const errorNotice = notice !== null && notice.kind === 'error' ? notice : null

  return (
    <section className="wallet" aria-labelledby="wallet-title">
      <h1 id="wallet-title" ref={headingRef} tabIndex={-1}>
        Carteira
      </h1>

      {read.status === 'loading' && (
        <p role="status" className="muted">
          Carregando carteira…
        </p>
      )}

      {read.status === 'failed' && (
        <div className="catalog-failure">
          <p role="alert" className="form-error">
            {read.failure === 'forbidden'
              ? 'Esta área é só para a conta de licitante.'
              : 'Não foi possível carregar a carteira.'}
          </p>
          {read.failure !== 'forbidden' && (
            <button type="button" className="button button-secondary" onClick={retry}>
              Tentar novamente
            </button>
          )}
        </div>
      )}

      {read.status === 'ready' && (
        <>
          <dl className="wallet-balances">
            <div className="wallet-available">
              <dt>Disponível para lances</dt>
              <dd>{formatCents(read.wallet.available_balance_cents)}</dd>
            </div>
            <div className="wallet-balance">
              <dt>Saldo total</dt>
              <dd>{formatCents(read.wallet.total_balance_cents)}</dd>
            </div>
            <div className="wallet-balance">
              <dt>Comprometido em lances</dt>
              <dd>{formatCents(read.wallet.committed_balance_cents)}</dd>
              <dd className="wallet-note muted">Reservado nos lotes em que você lidera.</dd>
            </div>
          </dl>

          <form
            className="wallet-deposit"
            aria-labelledby="wallet-deposit-title"
            aria-busy={pending}
            onSubmit={handleSubmit}
            noValidate
          >
            <h2 id="wallet-deposit-title">Depósito simulado</h2>
            <p className="muted wallet-deposit-note">Valor fictício, sem dinheiro real.</p>
            <MoneyField
              id="deposit-amount"
              label="Valor do depósito"
              value={amountText}
              error={fieldError}
              inputRef={amountRef}
              onChange={handleAmountChange}
              readOnly={pending}
            />
            <button type="submit" className="button button-primary" disabled={pending}>
              {pending ? 'Depositando…' : 'Depositar'}
            </button>
            {errorNotice !== null && (
              <p className="wallet-notice wallet-notice-error" role="alert">
                <span aria-hidden="true">{NOTICE_SYMBOL.error}</span>
                {errorNotice.text}
              </p>
            )}
            <p
              className={
                statusNotice === null
                  ? 'wallet-notice'
                  : `wallet-notice wallet-notice-${statusNotice.kind}`
              }
              role="status"
            >
              {statusNotice !== null && (
                <>
                  <span aria-hidden="true">{NOTICE_SYMBOL[statusNotice.kind]}</span>
                  {statusNotice.text}
                </>
              )}
            </p>
          </form>
        </>
      )}
    </section>
  )
}

export default WalletPage

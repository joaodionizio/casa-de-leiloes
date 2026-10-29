import { useState } from 'react'

const PLACEHOLDER_SRC = '/artwork-placeholder.svg'

interface ArtworkImageProps {
  src: string
  alt: string
  variant: 'thumb' | 'card' | 'large'
}

// Imagem da obra (AD-22). `src` é a URL same-origin do nosso proxy de mídia
// (`/api/catalog/images/{image_id}`): o navegador não consegue pedir o IIIF da AIC
// direto (403 do Cloudflare, teste manual de 24/10/2026). A caixa tem dimensões fixas
// antes da carga, então carregar ou falhar não muda o layout. Se a imagem falhar,
// troca pelo placeholder local; título e metadados continuam na tela. Use `key={src}` ao
// renderizar, para o estado de falha reiniciar quando a obra muda. Só `span`: a
// miniatura vive dentro de um `button`. Na miniatura a falha é só visual (placeholder
// com `alt=""`): um aviso oculto aqui viria antes do título no nome acessível do
// botão, e o título é o que o botão deve anunciar primeiro. A variante `card` (Story
// 2.5, D17) é a miniatura dos rails da vitrine: `lazy`, proporção reservada de 4:3,
// sem cortar a obra, e a falha também só visual (vive dentro de um link cujo nome vem
// do título). `large` (destaque e página do lote) carrega de imediato.
function ArtworkImage({ src, alt, variant }: ArtworkImageProps) {
  const [failed, setFailed] = useState(false)
  const [landscape, setLandscape] = useState(false)
  const large = variant === 'large'

  return (
    <>
      <span className={`artwork-image artwork-image-${variant}`} data-failed={failed} data-landscape={landscape}>
        <img
          src={failed ? PLACEHOLDER_SRC : src}
          alt={failed ? '' : alt}
          width={variant === 'thumb' ? 72 : 843}
          height={variant === 'thumb' ? 72 : 632}
          decoding="async"
          loading={large ? 'eager' : 'lazy'}
          referrerPolicy="no-referrer"
          onLoad={(event) => setLandscape(event.currentTarget.naturalWidth > event.currentTarget.naturalHeight * 1.1)}
          onError={() => setFailed(true)}
        />
      </span>
      {/* A linha da legenda é reservada, para a falha não empurrar o layout. */}
      {large && (
        <span className="artwork-image-caption muted">
          {failed ? 'Imagem indisponível' : ' '}
        </span>
      )}
    </>
  )
}

export default ArtworkImage

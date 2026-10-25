import ArtworkImage from './ArtworkImage'

// O que a obra precisa mostrar; `ArtworkDetail` e `LotResponse` satisfazem.
export interface LotArtworkInfo {
  external_id: number
  title: string | null
  artist_display: string | null
  date_display: string | null
  image_url: string
}

interface LotArtworkProps {
  artwork: LotArtworkInfo
  // `large`: imagem e ficha antes dos campos; `compact`: miniatura ao lado do texto.
  size: 'large' | 'compact'
}

// A obra é a protagonista também no formulário, na revisão e na confirmação
// (DESIGN §5): imagem e ficha vêm antes dos campos. Só leitura.
function LotArtwork({ artwork, size }: LotArtworkProps) {
  return (
    <div className={`lot-artwork lot-artwork-${size}`}>
      <ArtworkImage
        key={artwork.image_url}
        src={artwork.image_url}
        alt={size === 'large' ? (artwork.title ?? 'Obra sem título') : ''}
        variant={size === 'large' ? 'large' : 'thumb'}
      />
      <div className="lot-artwork-text">
        {artwork.title !== null ? (
          <p className="lot-artwork-title" title={artwork.title}>
            {artwork.title}
          </p>
        ) : (
          <p className="lot-artwork-title untitled">Sem título</p>
        )}
        {artwork.artist_display !== null && (
          <p className="lot-artwork-artist">{artwork.artist_display}</p>
        )}
        {artwork.date_display !== null && (
          <p className="muted lot-artwork-meta">{artwork.date_display}</p>
        )}
        <p className="muted lot-artwork-meta">Nº no acervo {artwork.external_id}</p>
      </div>
    </div>
  )
}

export default LotArtwork

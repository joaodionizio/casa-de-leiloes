interface AtrioMarkProps {
  // Altura em px; a largura segue a proporção do símbolo (28 × 38).
  size?: number
}

// Símbolo ÁTRIO: uma entrada alta, de topo pontudo (portal gótico), em duas faces. A
// face esquerda é lilás e a direita, violeta intenso, separadas pela vertical que sai do
// ápice. O vazio interno é assimétrico: parede esquerda vertical, topo arredondado e lado
// direito em diagonal. Geometria própria, só `path`, sem raster, sem gradiente e sem
// dependência; legível em 16 px.
// É decorativo: o nome acessível da marca vem do `aria-label` do link, então o SVG fica
// fora da árvore de acessibilidade para o leitor de tela não repetir a marca.
// A mesma geometria está em `public/favicon.svg`; se mudar aqui, mude lá.
const ATRIO_LEFT_FACE =
  'M16 1C10.5 4.5 2 9.5 2 17V39H7.6V21C7.6 16.3 10.8 14.1 15.2 14.1H16Z'
const ATRIO_RIGHT_FACE =
  'M16 1V14.1C17.1 14.2 17.4 14.7 17.7 15.8L23.5 39H30V20C30 12 24 5 16 1Z'
const ATRIO_LEFT_COLOR = '#a77bf6'
const ATRIO_RIGHT_COLOR = '#6c35e6'

function AtrioMark({ size = 32 }: AtrioMarkProps) {
  return (
    <svg
      className="atrio-mark"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="2 1 28 38"
      width={(size * 28) / 38}
      height={size}
      aria-hidden="true"
      focusable="false"
    >
      <path fill={ATRIO_LEFT_COLOR} d={ATRIO_LEFT_FACE} />
      <path fill={ATRIO_RIGHT_COLOR} d={ATRIO_RIGHT_FACE} />
    </svg>
  )
}

export default AtrioMark

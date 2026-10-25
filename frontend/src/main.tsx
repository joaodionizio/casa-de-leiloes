import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// A rolagem e o foco ao voltar são decididos pela vitrine (D11): o navegador não
// restaura a posição sozinho, porque o conteúdo chega depois, de forma assíncrona.
window.history.scrollRestoration = 'manual'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

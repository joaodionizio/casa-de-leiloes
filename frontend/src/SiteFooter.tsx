import AtrioMark from './AtrioMark'

export default function SiteFooter({ healthText }: { healthText: string }) {
  return <footer className="site-footer">
    <div className="page-container">
      <div className="site-footer-top">
        <div className="site-footer-about">
          <div className="site-footer-brand"><AtrioMark /><span className="site-footer-name">ÁTRIO</span></div>
          <p>Leilões de arte em domínio público, em tempo real.</p>
        </div>
        <section aria-labelledby="footer-project-title">
          <h2 id="footer-project-title">O projeto</h2>
          <p>ÁTRIO — Leilões de Arte</p>
          <p>Projeto demonstrativo desenvolvido para o Desafio Elite Dev — Verzel.</p>
        </section>
        <nav aria-label="Recursos" className="site-footer-resources">
          <h2>Recursos</h2>
          <a href="https://github.com/joaodionizio/casa-de-leiloes" target="_blank" rel="noopener noreferrer">Código-fonte</a>
          <a href="https://www.artic.edu/collection" target="_blank" rel="noopener noreferrer">Acervo artístico — Art Institute of Chicago</a>
        </nav>
      </div>
      <p className="site-footer-disclaimer">Leilões, saldos, depósitos e transações são simulados — este é um projeto de demonstração, não uma plataforma comercial em operação.</p>
      <div className="site-footer-bottom">
        <p>© 2026 ÁTRIO — Leilões de Arte</p>
        <p>Desenvolvido por João Luís Dionízio — Desafio Elite Dev — Verzel</p>
        <p role="status">{healthText}</p>
      </div>
    </div>
  </footer>
}

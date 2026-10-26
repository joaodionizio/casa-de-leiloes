/* Comprovante de arremate (documento público e compartilhável).
   Cenários: ?c=ok|adulterado &obra=… &imagens=quebradas. Rota e hash são fictícios. */
(function () {
  'use strict';
  var A = window.ATRIO;
  var esc = A.esc, fmt = A.fmt;
  var a = A.art(A.q('obra', 'seurat'));
  var c = A.q('c', 'ok');
  A.setTitle('Comprovante de arremate');
  var n = A.n('n', 14);
  var finalCents = 1650000;
  var hist = A.bids({ n: n, start: 1000000, inc: 50000, pos: 'neutro' });
  var last = hist.list[0];
  var ok = c !== 'adulterado';
  var verdict = ok
    ? '<div class="verdict verdict--ok"><span class="sym" aria-hidden="true">✓</span><div><h2>Integridade verificada</h2><p>O histórico de lances confere com a assinatura registrada no encerramento.</p></div></div>'
    : '<div class="verdict verdict--bad" role="alert"><span class="sym" aria-hidden="true">✕</span><div><h2>Integridade não confirmada</h2><p>A verificação encontrou divergência no histórico deste lote. Não use este comprovante como prova até a auditoria ser revisada.</p></div></div>';

  A.mount('<div class="page-container page"><div class="no-print receipt-actions">' +
    '<button class="btn btn-sm copy-link" type="button">Copiar link</button><button class="btn btn-sm" type="button" id="print">Imprimir</button><span class="copy-msg" role="status"></span></div>' +
    '<article class="receipt" aria-labelledby="rc-t">' +
    '<header class="receipt-head"><div class="receipt-brand"><svg viewBox="2 1 28 38" width="22" height="30" aria-hidden="true" focusable="false"><path fill="var(--mark-face-light)" d="M16 1C10.5 4.5 2 9.5 2 17V39H7.6V21C7.6 16.3 10.8 14.1 15.2 14.1H16Z"/><path fill="var(--mark-face-strong)" d="M16 1V14.1C17.1 14.2 17.4 14.7 17.7 15.8L23.5 39H30V20C30 12 24 5 16 1Z"/></svg>' +
    '<span class="site-brand-name">ÁTRIO</span><span class="muted">Leilões de Arte</span></div>' +
    '<p class="eyebrow">Documento digital</p><h1 id="rc-t">Comprovante de arremate</h1></header>' +
    '<div class="receipt-work">' + A.artworkHtml(a, { fit: 'contain', ratio: Math.min(1.3, Math.max(0.8, a.w / a.h)).toFixed(3) + ' / 1', index: 0, eager: true }) +
    '<div><h2 class="art-h">' + esc(a.title) + '</h2><p class="room-artist">' + esc(a.artist) + '<span class="muted"> · ' + esc(a.artistInfo) + '</span></p>' +
    '<p class="muted">' + esc(a.date) + ' · ' + esc(a.medium) + '</p></div></div>' +
    '<div class="receipt-value"><span class="label">Valor do arremate</span><span class="money money--xl">' + fmt(finalCents) + '</span></div>' +
    '<dl class="ficha"><div><dt>Arrematante</dt><dd>' + esc(A.ALIASES[0]) + '</dd></div>' +
    '<div><dt>Encerramento</dt><dd>26 out 2026, 14:45</dd></div>' +
    '<div><dt>Lances registrados</dt><dd>' + n + '</dd></div>' +
    '<div><dt>Hash final</dt><dd class="hash">' + last.hash + '</dd></div></dl>' +
    verdict +
    '<p class="receipt-foot">O arrematante é identificado apenas por pseudônimo, único neste lote. Nenhum dado pessoal consta neste documento. ' +
    '<a href="' + A.href('auditoria.html', { obra: a.key, n: n, c: ok ? 'integro' : 'adulterado' }) + '">Ver a auditoria completa deste lote</a>.</p>' +
    '</article></div>');

  document.getElementById('print').addEventListener('click', function () { window.print(); });
  document.querySelector('.copy-link').addEventListener('click', function () {
    var msg = document.querySelector('.copy-msg');
    function done(ok2) { msg.textContent = ok2 ? 'Link copiado' : 'Não foi possível copiar. Copie o endereço da página manualmente.'; }
    try {
      if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(window.location.href).then(function () { done(true); }, function () { done(false); }); return; }
      var t = document.createElement('textarea'); t.value = window.location.href; document.body.appendChild(t); t.select();
      var r = document.execCommand('copy'); document.body.removeChild(t); done(r);
    } catch (e) { done(false); }
  });
})();

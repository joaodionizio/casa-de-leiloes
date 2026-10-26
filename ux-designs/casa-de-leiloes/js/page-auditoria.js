/* Auditoria pública (sem login). Cenários: ?c=integro|adulterado &n=0|14|120 &obra=…
   Pseudônimos e hashes são fictícios. Não inventa o ponto da divergência: o contrato da auditoria
   ainda não define esse detalhe. */
(function () {
  'use strict';
  var A = window.ATRIO;
  var esc = A.esc, fmt = A.fmt;
  var a = A.art(A.q('obra', 'seurat'));
  var n = A.n('n', 14);
  var ok = A.q('c', 'integro') !== 'adulterado';
  A.setTitle('Auditoria do lote');
  var hist = A.bids({ n: n, start: 1000000, inc: 50000, pos: 'neutro', stepSec: n > 40 ? 181 : 197 });
  var list = hist.list.slice().reverse(); // ordem cronológica: #1 primeiro
  var last = hist.list[0];

  var verdict = ok
    ? '<div class="verdict verdict--ok"><span class="sym" aria-hidden="true">✓</span><div><h2>Histórico íntegro</h2><p>' + (n === 0
        ? 'Nenhum lance foi registrado neste lote até agora.'
        : 'A cadeia de hashes e a âncora conferem com os ' + n + ' lances registrados. Nenhuma alteração, inserção ou remoção foi detectada.') + '</p></div></div>'
    : '<div class="verdict verdict--bad" role="alert"><span class="sym" aria-hidden="true">✕</span><div><h2>Histórico adulterado</h2><p>A verificação encontrou divergência entre os lances exibidos e os dados de integridade do lote. Este histórico não pode ser considerado confiável.</p></div></div>';

  var rows = list.map(function (b) {
    return '<tr><td class="a-seq" data-label="Lance">#' + b.seq + '</td><td class="a-who" data-label="Licitante">' + esc(b.alias) + '</td>' +
      '<td class="a-val" data-label="Valor"><span class="money">' + fmt(b.cents) + '</span></td><td class="a-time" data-label="Registrado em">' + b.date + ', ' + b.time + '</td>' +
      '<td class="a-det"><details><summary>Hashes<span class="visually-hidden"> do lance ' + b.seq + '</span></summary><p class="label">Hash anterior</p><p class="hash">' + b.prev + '</p><p class="label">Hash deste lance</p><p class="hash">' + b.hash + '</p></details></td></tr>';
  }).join('');

  var table = n === 0
    ? '<p class="muted">Este lote ainda não recebeu lances.</p>'
    : '<table class="audit-table"><caption class="visually-hidden">Histórico completo de lances, do primeiro ao último</caption>' +
      '<thead><tr><th scope="col">Lance</th><th scope="col">Licitante</th><th scope="col">Valor</th><th scope="col">Registrado em</th><th scope="col"><span class="visually-hidden">Detalhes técnicos</span></th></tr></thead><tbody>' + rows + '</tbody></table>';

  A.mount('<div class="page-container page audit"><p class="eyebrow">Auditoria pública</p><h1>Histórico de lances</h1>' +
    '<div class="audit-lot">' + A.artworkHtml(a, { thumb: true, decorative: true, index: 0 }) +
    '<div><p class="lot-title-sm">' + esc(a.title) + '</p><p class="lot-artist">' + esc(a.artist) + '</p><p><a href="' + A.roomHref(a.key, 'vencedor') + '">Abrir a sala do lote</a></p></div></div>' +
    verdict +
    '<dl class="audit-summary"><div><dt class="label">Lances registrados</dt><dd class="money money--display">' + n + '</dd></div>' +
    (n > 0 ? '<div><dt class="label">Último lance</dt><dd class="money money--display">' + fmt(last.cents) + '</dd></div>' : '') + '</dl>' +
    '<details class="anchor"><summary>Dados técnicos da âncora</summary><dl class="ficha"><div><dt>Quantidade de lances</dt><dd>' + n + '</dd></div>' +
    '<div><dt>Hash final</dt><dd class="hash">' + (n > 0 ? last.hash : new Array(65).join('0')) + '</dd></div>' +
    '<div><dt>Assinatura (HMAC)</dt><dd class="hash">' + A.fakeHash('ancora:' + n) + '</dd></div></dl></details>' +
    '<section aria-labelledby="lances-t"><div class="section-head section-head--small"><h2 id="lances-t">Lances</h2></div>' + table + '</section>' +
    '<p class="muted audit-foot">Os licitantes aparecem apenas por pseudônimo, diferente em cada lote.</p></div>');
})();

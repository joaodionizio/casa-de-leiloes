/* Meus arremates. Cenários: ?n=20|0 (0 = vazio) */
(function () {
  'use strict';
  var A = window.ATRIO;
  var esc = A.esc, fmt = A.fmt;
  A.setTitle('Meus arremates');
  var n = A.n('n', 20);
  if (n === 0) {
    A.mount('<div class="page-container page"><h1>Meus arremates</h1><div class="empty-state"><h2>Você ainda não deu lances</h2>' +
      '<p>Os lotes em que você participa e os que você arrematar aparecem aqui, com o comprovante.</p>' +
      '<a class="btn btn-primary" href="' + A.href('vitrine.html') + '">Ver lotes ao vivo</a></div></div>');
    return;
  }
  var items = [];
  for (var i = 0; i < n; i++) {
    var a = A.ARTWORKS[(i * 3 + 1) % A.ARTWORKS.length];
    var kind = i < 2 ? (i === 0 ? 'leading' : 'outbid') : i < 4 ? 'pending' : i < Math.round(n * 0.4) ? 'won' : 'lost';
    items.push({ art: a, kind: kind, my: 800000 + i * 217000, final: 800000 + i * 217000 + (kind === 'lost' ? 150000 : 0), day: 25 - Math.floor(i / 2) });
  }
  var groups = [
    ['Em disputa', ['leading', 'outbid']], ['Apurando resultado', ['pending']], ['Arrematados', ['won']], ['Não arrematados', ['lost']]
  ];
  function row(it, idx) {
    var fase = { leading: 'aovivo', outbid: 'aovivo', pending: 'apurando', won: 'vencedor', lost: 'vencedor' }[it.kind];
    var pos = { leading: 'ganhando', outbid: 'superado', pending: 'neutro', won: 'ganhando', lost: 'superado' }[it.kind];
    var state, detail, actions;
    var roomLink = A.roomHref(it.art.key, fase, { papel: 'licitante', pos: pos });
    if (it.kind === 'leading') { state = A.stateHtml('leading'); detail = 'Seu último lance: <span class="money">' + fmt(it.my) + '</span>'; }
    else if (it.kind === 'outbid') { state = A.stateHtml('outbid'); detail = 'Seu último lance: <span class="money">' + fmt(it.my) + '</span>'; }
    else if (it.kind === 'pending') { state = A.stateHtml('pending'); detail = 'Seu último lance: <span class="money">' + fmt(it.my) + '</span>'; }
    else if (it.kind === 'won') { state = A.stateHtml('won', 'Arrematado'); detail = 'Valor do arremate: <span class="money">' + fmt(it.my) + '</span> · ' + it.day + ' out'; }
    else { state = '<span class="lot-state lot-state--ended"><span>Encerrado, não arrematado</span></span>'; detail = 'Seu último lance: <span class="money">' + fmt(it.my) + '</span> · ' + it.day + ' out'; }
    actions = '<a href="' + roomLink + '">Abrir sala</a>';
    if (it.kind === 'won') {
      var cmp = A.href('comprovante.html', { obra: it.art.key });
      actions = '<a class="btn btn-sm" href="' + cmp + '">Ver comprovante</a><button class="btn btn-sm copy-link" type="button" data-href="' + cmp + '">Copiar link</button>' + actions;
    }
    return '<li class="win-row">' + A.artworkHtml(it.art, { thumb: true, decorative: true, index: idx }) +
      '<div class="win-main"><h3 class="lot-title-sm" title="' + esc(it.art.title) + '">' + esc(it.art.title) + '</h3><p class="lot-artist">' + esc(it.art.artist) + '</p>' +
      '<p class="win-state">' + state + '</p><p class="win-detail">' + detail + '</p></div>' +
      '<div class="win-actions">' + actions + '<span class="copy-msg" role="status"></span></div></li>';
  }
  var html = '<div class="page-container page"><h1>Meus arremates</h1><p class="muted">' + n + ' lotes em que você deu lance.</p>';
  groups.forEach(function (g) {
    var rows = items.map(function (it, idx) { return g[1].indexOf(it.kind) >= 0 ? row(it, idx) : ''; }).join('');
    if (!rows) return;
    var count = items.filter(function (it) { return g[1].indexOf(it.kind) >= 0; }).length;
    html += '<section class="win-group"><div class="section-head section-head--small"><h2>' + g[0] + '<span class="section-count">' + count + '</span></h2></div><ul class="win-list">' + rows + '</ul></section>';
  });
  A.mount(html + '</div>');

  document.querySelectorAll('.copy-link').forEach(function (b) {
    b.addEventListener('click', function () {
      var url = new URL(b.getAttribute('data-href'), window.location.href).href;
      var msg = b.parentNode.querySelector('.copy-msg');
      function done(ok) { msg.textContent = ok ? 'Link copiado' : 'Não foi possível copiar. Copie o endereço do comprovante manualmente.'; }
      try {
        if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(url).then(function () { done(true); }, function () { done(false); }); return; }
        var t = document.createElement('textarea'); t.value = url; document.body.appendChild(t); t.select();
        var ok = document.execCommand('copy'); document.body.removeChild(t); done(ok);
      } catch (e) { done(false); }
    });
  });
})();

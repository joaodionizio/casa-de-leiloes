/* Vitrine pública. Cenários: ?vivo=0|1|5|12 &prox=0|3|20 &enc=0|8|50
   &variante=normal|carregando|erro|longos &imagens=ok|algumas|quebradas &papel=… */
(function () {
  'use strict';
  var A = window.ATRIO;
  var esc = A.esc;
  var fmt = A.fmt;
  var role = A.currentRole;
  A.setTitle('Vitrine');

  var variante = A.q('variante', 'normal');
  var nLive = A.n('vivo', 5);
  var nNext = A.n('prox', 8);
  var nClosed = A.n('enc', 12);
  var CLOSED_RENDERED = 10; // quantidade prevista pela composição (D4: sem "Ver arquivo")

  if (variante === 'carregando') return renderLoading();
  if (variante === 'erro') return renderError();

  var live = A.liveLots(nLive);
  var next = A.upcomingLots(nNext);
  var closed = A.closedLots(nClosed);

  var html = '<h1 class="visually-hidden">Vitrine de lotes</h1>';
  html += heroHtml();
  if (nLive >= 2 || nLive === 0) html += liveSection();
  html += nextSection();
  html += closedSection();
  A.mount(html);

  function heroHtml() {
    if (nLive >= 1) {
      var l = live[0];
      return hero({ art: l.art, title: l.title, state: 'live', label: 'Lance atual', value: l.current,
        timeLabel: 'Termina em', time: l.ends, cta: 'Entrar na sala', href: A.roomHref(l.art.key, 'aovivo') });
    }
    if (nNext >= 1) {
      var u = next[0];
      return hero({ art: u.art, title: u.title, state: 'scheduled', label: 'Lance inicial', value: u.start,
        timeLabel: 'Começa em', time: u.in, cta: 'Ver o lote', href: A.roomHref(u.art.key, 'agendado') });
    }
    var cta = role === 'leiloeiro' ? '<a class="btn btn-primary" href="' + A.href('criar-lote.html') + '">Criar lote</a>' : '';
    return '<section class="hero hero--empty"><div class="page-container"><div class="empty-state">' +
      '<h2>Nenhum lote em exibição</h2>' +
      '<p>Quando houver lotes ao vivo ou agendados, a obra em destaque aparece aqui. Os lotes encerrados continuam consultáveis abaixo.</p>' +
      cta + '</div></div></section>';
  }

  function hero(o) {
    return '<section class="hero" aria-labelledby="hero-title"><div class="page-container hero-grid">' +
      '<div class="hero-art">' + A.artworkHtml(o.art, { eager: true, index: 0 }) + '</div>' +
      '<div class="hero-info">' +
      A.stateHtml(o.state) +
      '<h2 class="hero-title" id="hero-title" title="' + esc(o.title) + '">' + esc(o.title) + '</h2>' +
      '<p class="hero-artist">' + esc(o.art.artist) + '<span class="muted"> · ' + esc(o.art.artistInfo) + '</span></p>' +
      '<dl class="hero-figures">' +
      '<div><dt class="label">' + o.label + '</dt><dd class="money money--xl">' + fmt(o.value) + '</dd></div>' +
      (o.time ? '<div><dt class="label">' + o.timeLabel + '</dt><dd class="countdown countdown--display">' + esc(o.time) + '</dd></div>' : '') +
      '</dl>' +
      '<a class="btn btn-primary hero-cta" href="' + o.href + '">' + o.cta + '</a>' +
      '</div></div></section>';
  }

  function head(id, title, count, controls) {
    return '<div class="section-head"><h2 id="' + id + '">' + title +
      (count ? '<span class="section-count">' + count + '</span>' : '') + '</h2>' + (controls || '') + '</div>';
  }

  function plural(n, one, many) {
    return n + ' ' + (n === 1 ? one : many);
  }

  function liveSection() {
    if (nLive === 0) {
      var when = nNext >= 1 ? ' O próximo começa ' + esc(next[0].when.replace(' · ', ', às ')) + '.' : '';
      return '<section class="section" aria-labelledby="ao-vivo"><div class="page-container">' +
        head('ao-vivo', 'Ao vivo') +
        '<div class="empty-state"><h3>Nenhum lote ao vivo agora</h3><p>Os leilões em andamento aparecem aqui.' + when + '</p></div>' +
        '</div></section>';
    }
    var items = live.slice(1).map(function (l, i) { return liveItem(l, i + 1); }).join('');
    return '<section class="section" aria-labelledby="ao-vivo" data-rail><div class="page-container">' +
      head('ao-vivo', 'Ao vivo', plural(nLive, 'lote', 'lotes'), A.railControls('Lotes ao vivo')) +
      '<div class="rail rail--live" tabindex="0" role="region" aria-label="Lotes ao vivo, rolagem horizontal">' + items + '</div>' +
      '</div></section>';
  }

  function liveItem(l, i) {
    return '<article class="lot-item lot-item--live">' +
      A.artworkHtml(l.art, { index: i }) +
      '<div class="lot-item-meta">' + A.stateHtml('live') + '<span class="countdown">' + esc(l.ends) + '</span></div>' +
      '<h3 class="lot-title" title="' + esc(l.title) + '"><a href="' + A.roomHref(l.art.key, 'aovivo') + '">' + esc(l.title) + '</a></h3>' +
      '<p class="lot-artist">' + esc(l.art.artist) + '</p>' +
      '<p class="bid-line"><span class="label">Lance atual</span><span class="money">' + fmt(l.current) + '</span></p>' +
      '</article>';
  }

  function nextSection() {
    var inner;
    if (nNext === 0) {
      inner = head('proximos', 'Próximos lotes') +
        '<div class="empty-state"><h3>Nenhum lote agendado</h3><p>Os próximos leilões aparecem aqui assim que o leiloeiro os publicar.</p></div>';
    } else {
      inner = head('proximos', 'Próximos lotes', plural(nNext, 'lote', 'lotes'), A.railControls('Próximos lotes')) +
        '<div class="rail rail--upcoming" tabindex="0" role="region" aria-label="Próximos lotes, rolagem horizontal">' +
        next.map(upcomingItem).join('') + '</div>';
    }
    return '<section class="section" aria-labelledby="proximos"' + (nNext ? ' data-rail' : '') + '><div class="page-container">' + inner + '</div></section>';
  }

  function upcomingItem(u, i) {
    return '<article class="lot-item lot-item--upcoming">' +
      A.artworkHtml(u.art, { ratio: '4 / 3', index: i + 3 }) +
      '<div class="when-block">' + A.stateHtml('scheduled') + '<span class="when">' + esc(u.when) + '</span></div>' +
      '<h3 class="lot-title" title="' + esc(u.title) + '"><a href="' + A.roomHref(u.art.key, 'agendado') + '">' + esc(u.title) + '</a></h3>' +
      '<p class="lot-artist">' + esc(u.art.artist) + '</p>' +
      '<p class="bid-line"><span class="label">Lance inicial</span><span class="money">' + fmt(u.start) + '</span></p>' +
      '</article>';
  }

  function closedSection() {
    var shown = Math.min(nClosed, CLOSED_RENDERED);
    var inner;
    if (nClosed === 0) {
      inner = head('encerrados', 'Encerrados') +
        '<div class="empty-state"><h3>Ainda não há lotes encerrados</h3><p>Os resultados dos leilões aparecem aqui depois do encerramento.</p></div>';
    } else {
      inner = head('encerrados', 'Encerrados', String(nClosed)) +
        '<ul class="closed-list">' + closed.slice(0, shown).map(closedRow).join('') + '</ul>' +
        '<p class="closed-footnote">' + (nClosed > shown ? 'Mostrando ' + shown + ' de ' + nClosed + ' lotes encerrados' : plural(nClosed, 'lote encerrado', 'lotes encerrados')) + '</p>';
    }
    return '<section class="section section--closed" aria-labelledby="encerrados"><div class="page-container">' + inner + '</div></section>';
  }

  function closedRow(c, i) {
    var fase = c.result === 'won' ? 'vencedor' : c.result === 'none' ? 'sem-lances' : 'apurando';
    var result;
    if (c.result === 'won') result = '<span class="label">Arrematado por</span><span class="money">' + fmt(c.final) + '</span>';
    else if (c.result === 'none') result = '<span class="label">Encerrado sem lances</span>';
    else result = A.stateHtml('pending');
    return '<li class="closed-row">' +
      A.artworkHtml(c.art, { thumb: true, decorative: true, index: i + 6 }) +
      '<div class="closed-info"><h3 class="lot-title" title="' + esc(c.title) + '"><a href="' + A.roomHref(c.art.key, fase) + '">' + esc(c.title) + '</a></h3>' +
      '<p class="lot-artist">' + esc(c.art.artist) + ' · ' + esc(c.when) + '</p></div>' +
      '<div class="closed-result">' + result + '</div></li>';
  }

  function renderLoading() {
    var items = '';
    for (var i = 0; i < 4; i++) {
      items += '<div class="lot-item"><div class="artwork skeleton" style="--ratio:5 / 4"></div><div class="skeleton" style="height:1.1rem;width:70%"></div><div class="skeleton" style="height:.9rem;width:45%"></div></div>';
    }
    A.mount('<h1 class="visually-hidden">Vitrine de lotes</h1>' + A.loadingBlock('Carregando lotes…') +
      '<section class="hero" aria-hidden="true"><div class="page-container hero-grid"><div class="hero-art"><div class="artwork skeleton"></div></div>' +
      '<div class="hero-info"><div class="skeleton" style="height:1rem;width:30%"></div><div class="skeleton" style="height:2.5rem;width:90%"></div><div class="skeleton" style="height:1rem;width:50%"></div></div></div></section>' +
      '<section class="section" aria-hidden="true"><div class="page-container"><div class="section-head"><h2>Ao vivo</h2></div>' +
      '<div class="skeleton-row">' + items + '</div></div></section>');
  }

  function renderError() {
    A.mount('<h1 class="visually-hidden">Vitrine de lotes</h1><section class="section"><div class="page-container"><div class="empty-state">' +
      '<h2>Não foi possível carregar a vitrine agora</h2>' +
      '<p>O ÁTRIO não conseguiu buscar os lotes. Isso não afeta os seus saldos nem os leilões em andamento. Tente novamente em instantes.</p>' +
      '<a class="btn" href="' + A.href('vitrine.html') + '">Tentar novamente</a></div></div></section>');
  }
})();

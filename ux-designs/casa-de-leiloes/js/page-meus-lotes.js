/* Painel do leiloeiro ("Meus lotes"). Cenários: ?n=0|3|30 &c=normal|confirmar &variante=longos */
(function () {
  'use strict';
  var A = window.ATRIO;
  var esc = A.esc;
  var fmt = A.fmt;
  A.setTitle('Meus lotes');
  var n = A.n('n', 30);
  var confirmOpen = A.q('c', 'normal') === 'confirmar';

  if (n === 0) {
    A.mount('<div class="page-container page"><h1>Meus lotes</h1><div class="empty-state"><h2>Você ainda não criou lotes</h2>' +
      '<p>Busque uma obra de domínio público no catálogo do museu e publique o primeiro lote.</p>' +
      '<a class="btn btn-primary" href="' + A.href('criar-lote.html') + '">Criar lote</a></div></div>');
    return;
  }

  var nLive = Math.max(1, Math.ceil(n * 0.15));
  var nSched = Math.max(1, Math.ceil(n * 0.25));
  var lots = [];
  for (var i = 0; i < n; i++) {
    var a = A.ARTWORKS[(i * 3 + 2) % A.ARTWORKS.length];
    var title = a.title;
    if (A.q('variante', 'normal') === 'longos' && i % 2 === 0) title += ' (detail of the complete composition from the collection catalogue, second state)';
    var lot = { art: a, title: title };
    if (i < nLive) {
      lot.group = 'live'; lot.bids = 3 + i * 2; lot.value = 1200000 + i * 350000;
      lot.start = '26 out, 10:00'; lot.end = '26 out, ' + (15 + i) + ':00';
    } else if (i < nLive + nSched) {
      lot.group = 'sched'; lot.bids = 0; lot.value = 600000 + (i % 5) * 150000;
      lot.start = (27 + Math.floor((i - nLive) / 3)) + ' out, 10:00'; lot.end = (27 + Math.floor((i - nLive) / 3)) + ' out, 18:00';
    } else {
      var k = i - nLive - nSched;
      lot.group = 'ended';
      lot.result = k === 0 ? 'pending' : (k % 6 === 4 ? 'none' : 'won');
      lot.bids = lot.result === 'none' ? 0 : 4 + (k * 3) % 17;
      lot.value = 400000 + ((k * 977) % 90) * 100000;
      var day = 25 - Math.floor(k / 2);
      lot.start = (day) + ' out, 10:00'; lot.end = day + ' out, 18:00';
      if (day < 1) { lot.start = (day + 30) + ' set, 10:00'; lot.end = (day + 30) + ' set, 18:00'; }
    }
    lots.push(lot);
  }
  var total = 0;
  lots.forEach(function (l) { if (l.group === 'ended' && l.result === 'won') total += l.value; });
  var counts = { live: nLive, sched: nSched, ended: n - nLive - nSched };

  var firstCancelable = -1;
  lots.forEach(function (l, idx) { if (firstCancelable < 0 && l.group === 'sched') firstCancelable = idx; });

  function stateCell(l) {
    if (l.group === 'live') return A.stateHtml('live');
    if (l.group === 'sched') return A.stateHtml('scheduled');
    if (l.result === 'pending') return A.stateHtml('pending');
    if (l.result === 'none') return '<span class="lot-state lot-state--ended"><span>Encerrado, sem lances</span></span>';
    return A.stateHtml('ended');
  }
  function valueCell(l) {
    if (l.group === 'live') return '<span class="label">Atual</span> <span class="money">' + fmt(l.value) + '</span>';
    if (l.group === 'sched') return '<span class="label">Inicial</span> <span class="money">' + fmt(l.value) + '</span>';
    if (l.result === 'won') return '<span class="label">Arrematado</span> <span class="money">' + fmt(l.value) + '</span>';
    return '<span class="muted">—</span>';
  }
  function actionCell(l, idx) {
    var fase = l.group === 'live' ? 'aovivo' : l.group === 'sched' ? 'agendado' : l.result === 'won' ? 'vencedor' : l.result === 'none' ? 'sem-lances' : 'apurando';
    var room = '<a href="' + A.roomHref(l.art.key, fase, { papel: 'leiloeiro' }) + '">Abrir sala</a>';
    var cancel = '';
    if ((l.group === 'sched' || (l.group === 'live' && l.bids === 0))) {
      cancel = '<button class="btn btn-sm cancel-btn" type="button" aria-expanded="' + (idx === firstCancelable && confirmOpen) + '">Cancelar lote</button>';
    }
    return '<div class="row-actions">' + room + cancel + '</div>' +
      (cancel ? '<div class="cancel-confirm" ' + (idx === firstCancelable && confirmOpen ? '' : 'hidden') + '><p><strong>Cancelar este lote?</strong> Ele sai da vitrine e não poderá ser reativado.</p>' +
        '<div class="row-actions"><button class="btn btn-sm btn-primary confirm-yes" type="button">Confirmar cancelamento</button><button class="btn btn-sm confirm-no" type="button">Voltar</button></div></div>' : '');
  }
  function row(l, idx) {
    return '<tr>' +
      '<td class="c-art"><div class="lot-cell">' + A.artworkHtml(l.art, { thumb: true, decorative: true, index: idx }) +
      '<div class="lot-cell-text"><span class="lot-title-sm" title="' + esc(l.title) + '">' + esc(l.title) + '</span><span class="lot-artist">' + esc(l.art.artist) + '</span></div></div></td>' +
      '<td class="c-state" data-label="Estado">' + stateCell(l) + '</td>' +
      '<td class="c-date" data-label="Início">' + l.start + '</td>' +
      '<td class="c-date" data-label="Fim">' + l.end + '</td>' +
      '<td class="c-value" data-label="Lance">' + valueCell(l) + '</td>' +
      '<td class="c-count" data-label="Lances">' + l.bids + '</td>' +
      '<td class="c-action">' + actionCell(l, idx) + '</td></tr>';
  }

  var groups = [['live', 'Ao vivo'], ['sched', 'Agendados'], ['ended', 'Encerrados']];
  var body = groups.map(function (g) {
    var rows = lots.map(function (l, idx) { return l.group === g[0] ? row(l, idx) : ''; }).join('');
    return '<tbody><tr class="group-row"><th colspan="7" scope="colgroup">' + g[1] + ' <span class="section-count">' + counts[g[0]] + '</span></th></tr>' + rows + '</tbody>';
  }).join('');

  A.mount('<div class="page-container page"><div class="page-head"><div><h1>Meus lotes</h1>' +
    '<p class="muted">' + n + ' lotes · ' + counts.live + ' ao vivo · ' + counts.sched + ' agendados · ' + counts.ended + ' encerrados</p></div>' +
    '<a class="btn btn-primary" href="' + A.href('criar-lote.html') + '">Criar lote</a></div>' +
    '<div class="summary"><span class="label">Total recebido</span><span class="money money--xl">' + fmt(total) + '</span>' +
    '<span class="label">Soma dos lotes encerrados e liquidados com vencedor.</span></div>' +
    '<table class="data-table"><caption class="visually-hidden">Meus lotes por estado</caption>' +
    '<thead><tr><th scope="col">Obra</th><th scope="col">Estado</th><th scope="col">Início</th><th scope="col">Fim</th><th scope="col">Lance</th><th scope="col">Lances</th><th scope="col"><span class="visually-hidden">Ações</span></th></tr></thead>' +
    body + '</table></div>');

  document.querySelectorAll('.cancel-btn').forEach(function (b) {
    b.addEventListener('click', function () {
      var box = b.closest('td').querySelector('.cancel-confirm');
      var open = box.hasAttribute('hidden');
      if (open) box.removeAttribute('hidden'); else box.setAttribute('hidden', '');
      b.setAttribute('aria-expanded', String(open));
    });
  });
  document.querySelectorAll('.confirm-no').forEach(function (b) {
    b.addEventListener('click', function () {
      var td = b.closest('td');
      td.querySelector('.cancel-confirm').setAttribute('hidden', '');
      td.querySelector('.cancel-btn').setAttribute('aria-expanded', 'false');
      td.querySelector('.cancel-btn').focus();
    });
  });
  document.querySelectorAll('.confirm-yes').forEach(function (b) {
    b.addEventListener('click', function () {
      var tr = b.closest('tr');
      tr.querySelector('.c-state').innerHTML = '<span class="lot-state lot-state--ended"><span>Cancelado</span></span>';
      tr.querySelector('.c-action').innerHTML = '<p class="muted" role="status">Lote cancelado.</p>';
    });
  });
})();

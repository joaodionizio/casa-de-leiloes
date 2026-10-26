/* Sala do lote. Papel (visitante|licitante|leiloeiro) e cenário vêm da querystring:
   ?obra=seurat &fase=agendado|aovivo|apurando|vencedor|sem-lances
   &pos=neutro|ganhando|superado &msg=aceito|abaixo|saldo|ja-ganhando|nao-iniciado|encerrado|prorrogado
   &tempo=normal|final|zero|prorrogado &rede=ok|reconectando &lances=14 &valor=normal|alto
   Tudo simulado só para visualizar: o servidor decide estado, vencedor, saldo e fim (AD-6, AD-19). */
(function () {
  'use strict';
  var A = window.ATRIO;
  var esc = A.esc;
  var fmt = A.fmt;
  var role = A.currentRole;
  var a = A.art(A.q('obra', 'seurat'));
  var fase = A.q('fase', 'aovivo');
  var pos = A.q('pos', role === 'licitante' ? 'ganhando' : 'neutro');
  var msg = A.q('msg', 'none');
  var tempo = A.q('tempo', msg === 'prorrogado' ? 'prorrogado' : 'normal');
  var rede = A.q('rede', 'ok');
  var big = A.q('valor', 'normal') === 'alto';
  var isBidder = role === 'licitante';
  A.setTitle(a.title);

  var start = big ? 75000000 : 1000000;
  var inc = big ? 2500000 : 50000;
  var n = (fase === 'agendado' || fase === 'sem-lances') ? 0 : A.n('lances', 14);
  if (n === 0 && (fase === 'aovivo')) n = 0;
  var current = n > 0 ? start + (n - 1) * inc : null;
  var minNext = n > 0 ? current + inc : start;
  if (msg === 'aceito') pos = 'ganhando';
  if (!isBidder) pos = 'neutro';
  var hist = A.bids({ n: n, start: start, inc: inc, pos: pos });
  var myLast = null;
  hist.list.forEach(function (b) { if (b.me && myLast === null) myLast = b.cents; });
  var available = msg === 'saldo' ? (big ? 60000000 : 1230000) : (big ? 900000000 : 8500000);

  var TIMES = { normal: '00:12:48', final: '01:42', zero: '00:00', prorrogado: '03:42' };
  var countdown = TIMES[tempo] || TIMES.normal;
  var live = fase === 'aovivo';

  /* ---------- peças ---------- */
  function statusBlock() {
    var kind = { agendado: 'scheduled', aovivo: 'live', apurando: 'pending', vencedor: 'ended', 'sem-lances': 'ended' }[fase];
    var time = '';
    if (fase === 'aovivo') {
      time = '<div class="room-time"><span class="label">Termina em</span><span class="countdown countdown--display">' + countdown + '</span></div>';
    } else if (fase === 'agendado') {
      time = '<div class="room-time"><span class="label">Começa em</span><span class="countdown countdown--display">3 h 28 min</span></div>';
    }
    return '<div class="room-status">' + A.stateHtml(kind) + time + '</div>' +
      (live && tempo === 'zero' ? '<p class="room-confirming" role="status">Confirmando encerramento com o servidor…</p>' : '');
  }

  function titleBlock() {
    return '<div class="room-title"><h1>' + esc(a.title) + '</h1>' +
      '<p class="room-artist">' + esc(a.artist) + '<span class="muted"> · ' + esc(a.artistInfo) + '</span></p></div>';
  }

  function positionRow() {
    if (!isBidder || !live) return '';
    if (pos === 'ganhando') {
      return '<div class="room-position room-position--leading"><p>' + A.stateHtml('leading') + '</p>' +
        '<p class="room-position-detail">Seu último lance: <strong class="money">' + fmt(myLast) + '</strong></p>' +
        '<p class="room-position-detail">Seus lances neste lote: <strong>' + hist.mine + '</strong></p></div>';
    }
    if (pos === 'superado') {
      return '<div class="room-position room-position--outbid"><p>' + A.stateHtml('outbid') + '</p>' +
        '<p class="room-position-detail">Seu último lance: <strong class="money">' + fmt(myLast) + '</strong></p>' +
        '<p class="room-position-detail">Seus lances neste lote: <strong>' + hist.mine + '</strong></p></div>';
    }
    return '<div class="room-position"><p class="muted">Você ainda não deu lances neste lote.</p></div>';
  }

  function figure() {
    var label, value, big2 = true;
    if (fase === 'agendado' || (fase === 'aovivo' && n === 0)) { label = 'Lance inicial'; value = fmt(start); }
    else if (fase === 'aovivo') { label = 'Lance atual'; value = fmt(current); }
    else if (fase === 'apurando') { label = 'Último lance registrado'; value = fmt(current); big2 = false; }
    else if (fase === 'vencedor') { label = 'Arrematado por'; value = fmt(current); }
    else return '<div class="room-figure-bid"><p class="room-result">Encerrado sem vencedor</p><p class="muted">Este lote não recebeu lances.</p></div>';
    var extra = '';
    if (fase === 'aovivo' && n === 0) extra = '<p class="muted">Nenhum lance ainda.</p>';
    if (fase === 'vencedor') {
      var winnerIsMe = isBidder && pos === 'ganhando';
      extra = winnerIsMe
        ? '<p>' + A.stateHtml('won') + '</p><p><a class="btn btn-primary" href="' + A.href('comprovante.html', { obra: a.key }) + '">Ver comprovante</a></p>'
        : '<p class="room-position-detail">Arrematante: <strong>' + esc(A.ALIASES[1]) + '</strong></p>' +
          (isBidder && pos === 'superado' ? '<p class="muted">Você não arrematou este lote.</p>' : '');
    }
    if (fase === 'apurando') extra = '<p class="notice notice--warning"><strong>Estamos apurando o resultado.</strong> O vencedor e o comprovante aparecem depois da liquidação.</p>';
    return '<div class="room-figure-bid"><span class="label">' + label + '</span>' +
      '<span class="money ' + (big2 ? 'money--xl' : 'money--display') + '">' + value + '</span>' + extra + '</div>';
  }

  function minRow() {
    if (!live) return '';
    return '<div class="kv room-min"><span class="label">Próximo lance mínimo</span><span class="money">' + fmt(minNext) + '</span></div>';
  }

  function balanceRow() {
    if (!isBidder || !live) return '';
    return '<div class="kv room-balance"><span class="label">Seu saldo disponível</span><span class="money">' + fmt(available) + '</span></div>';
  }

  function chips() {
    if (!isBidder || !live) return '';
    return '<div class="chips" role="group" aria-label="Atalhos de valor"><span class="label">Atalhos</span>' +
      '<button class="chip" type="button" data-fill="' + fmt(minNext).replace('R$ ', '') + '">' + fmt(minNext) + '</button>' +
      '<button class="chip" type="button" data-fill="' + fmt(minNext + inc).replace('R$ ', '') + '">' + fmt(minNext + inc) + '</button></div>';
  }

  function feedback() {
    var t = null, cls = 'notice--danger';
    if (msg === 'abaixo') t = ['Lance abaixo do mínimo.', 'O próximo lance deve ser de pelo menos ' + fmt(minNext) + '.'];
    else if (msg === 'saldo') t = ['Saldo insuficiente.', 'Você tem ' + fmt(available) + ' disponíveis e este lance exige ' + fmt(minNext) + '. <a href="' + A.href('carteira.html') + '">Ir para a Carteira</a>'];
    else if (msg === 'ja-ganhando') t = ['Você já está ganhando este lote.', 'Aguarde outro lance para cobrir.'];
    else if (msg === 'nao-iniciado') t = ['Este lote ainda não começou.', 'Os lances abrem em 26 out 2026, 18:00.'];
    else if (msg === 'encerrado') t = ['Este lote já foi encerrado.', 'Não há mais lances.'];
    else if (msg === 'aceito') { t = ['Lance aceito.', 'Você está ganhando com ' + fmt(current) + '.']; cls = 'notice--success'; }
    else if (msg === 'prorrogado') { t = ['O fim do lote foi prorrogado em 2 minutos.', 'Novo horário de encerramento: 14:47.']; cls = 'notice--warning'; }
    return '<div class="room-feedback" role="status" aria-live="polite">' +
      (t ? '<p class="notice ' + cls + '"><strong>' + t[0] + '</strong> ' + t[1] + '</p>' : '') + '</div>';
  }

  function form() {
    if (!isBidder || !live) return '<div class="room-form room-form--none">' + feedback() + '</div>';
    var off = tempo === 'zero';
    return '<form class="room-form" novalidate>' + feedback() +
      '<div class="room-form-row"><div class="field"><label class="field-label" for="lance">Seu lance (R$)</label>' +
      '<div class="input-money"><span class="prefix" aria-hidden="true">R$</span>' +
      '<input class="input" id="lance" inputmode="decimal" autocomplete="off" placeholder="' + fmt(minNext).replace('R$ ', '') + '"' +
      (msg === 'abaixo' ? ' value="' + fmt(minNext - inc).replace('R$ ', '') + '" aria-invalid="true"' : '') + (off ? ' disabled' : '') + '></div></div>' +
      '<button class="btn btn-primary" type="submit"' + (off ? ' disabled' : '') + '>Dar lance</button></div></form>';
  }

  function audience() {
    if (fase === 'apurando' || fase === 'vencedor' || fase === 'sem-lances') return '';
    if (role === 'visitante') {
      return '<p class="room-note">Para dar lances, entre com sua conta de licitante. <a href="' + A.href('login.html') + '">Entrar</a></p>';
    }
    if (role === 'leiloeiro') return '<p class="room-note muted">Você acompanha este lote como leiloeiro.</p>';
    if (fase === 'agendado') return '<p class="room-note muted">Os lances abrem quando o leilão começar.</p>';
    return '';
  }

  function history() {
    var shown = hist.list.slice(0, 8);
    var rows;
    if (fase === 'agendado') rows = '<p class="muted">Os lances aparecem aqui quando o leilão abrir.</p>';
    else if (n === 0) rows = '<p class="muted">' + (fase === 'sem-lances' ? 'Este lote não recebeu lances.' : 'Nenhum lance ainda. O primeiro lance deve ser de pelo menos ' + fmt(start) + '.') + '</p>';
    else {
      rows = '<ol class="bid-list">' + shown.map(function (b, i) {
        var who = b.me ? '<strong class="you">Você</strong> <span class="muted alias">' + esc(b.alias) + '</span>' : '<span class="alias">' + esc(b.alias) + '</span>';
        return '<li class="bid-row' + (i === 0 ? ' bid-row--top' : '') + (b.me ? ' bid-row--me' : '') + '">' +
          '<span class="bid-seq">#' + b.seq + '</span><span class="bid-who">' + who + '</span>' +
          '<span class="bid-time">' + b.time + '</span><span class="money">' + fmt(b.cents) + '</span></li>';
      }).join('') + '</ol>';
    }
    var link = n > 0 ? '<a href="' + A.href('auditoria.html', { obra: a.key, n: n }) + '">Ver auditoria completa</a>' : '';
    var count = n > 0 ? '<span class="section-count">' + (n > shown.length ? 'últimos ' + shown.length + ' de ' + n : n + (n === 1 ? ' lance' : ' lances')) + '</span>' : '';
    return '<section class="room-history" aria-labelledby="hist-t"><div class="section-head section-head--small"><h2 id="hist-t">Histórico de lances' + count + '</h2>' + link + '</div>' + rows + '</section>';
  }

  function ficha() {
    var rows = [
      ['Artista', esc(a.artist) + ' (' + esc(a.artistInfo) + ')'], ['Data', esc(a.date)], ['Técnica', esc(a.medium)], ['Dimensões', esc(a.dims)],
      ['Departamento', esc(a.dept)], ['Crédito', esc(a.credit)],
      ['Início', '26 out 2026, 10:00'], ['Fim', tempo === 'prorrogado' ? '26 out 2026, 14:47' : '26 out 2026, 14:45'],
      ['Lance inicial', fmt(start)], ['Incremento mínimo', fmt(inc)]
    ];
    return '<section class="room-ficha" aria-labelledby="ficha-t"><div class="section-head section-head--small"><h2 id="ficha-t">Sobre a obra e o lote</h2></div><dl class="ficha">' +
      rows.map(function (r) { return '<div><dt>' + r[0] + '</dt><dd>' + r[1] + '</dd></div>'; }).join('') + '</dl>' +
      '<p class="credit"><a href="https://www.artic.edu/artworks/' + a.id + '" rel="noopener">Ver no Art Institute of Chicago</a></p></section>';
  }

  var conn = rede === 'reconectando'
    ? '<div class="page-container"><p class="notice notice--warning room-conn" role="status"><strong>Reconectando…</strong> As atualizações ao vivo voltam quando a conexão for restabelecida. Ao reconectar, o ÁTRIO mostra o estado completo do lote.</p></div>'
    : '';

  var html = conn + '<div class="page-container room-wrap"><a class="back-link" href="' + A.href('vitrine.html') + '">← Vitrine</a>' +
    '<div class="room-grid">' +
    '<div class="room-panel">' + statusBlock() + titleBlock() +
    '<div class="room-bid">' + figure() + positionRow() + minRow() + balanceRow() + chips() + audience() + '</div>' + form() + '</div>' +
    '<figure class="room-figure">' + A.artworkHtml(a, { eager: true, fit: 'contain', index: 0, ratio: Math.min(1.6, Math.max(0.8, a.w / a.h)).toFixed(3) + ' / 1' }) +
    '<figcaption class="credit">' + esc(a.title) + ' — ' + esc(a.artist) + '. ' + esc(a.credit) + '.</figcaption></figure>' +
    history() + ficha() + '</div></div>';
  A.mount(html);

  // Atalhos de valor: preenchem o campo só quando ele está vazio ou foi preenchido por atalho;
  // nunca sobrescrevem um valor digitado.
  var input = document.getElementById('lance');
  document.querySelectorAll('.chip').forEach(function (c) {
    c.addEventListener('click', function () {
      if (!input || input.disabled) return;
      if (input.value === '' || input.getAttribute('data-from-chip') === 'true') {
        input.value = c.getAttribute('data-fill');
        input.setAttribute('data-from-chip', 'true');
      }
    });
  });
  if (input) input.addEventListener('input', function () { input.removeAttribute('data-from-chip'); });
  var f = document.querySelector('form.room-form');
  if (f) f.addEventListener('submit', function (e) { e.preventDefault(); });
})();

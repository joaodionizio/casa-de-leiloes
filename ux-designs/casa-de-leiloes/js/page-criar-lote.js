/* Criar lote em 5 passos: buscar, conferir, condições, revisão, publicado.
   Cenários: ?passo=1..5 &c=inicio|resultados|vazio|erro|carregando (passo 1) | erro (passo 3) &obra=… &variante=longos
   Busca, API do museu e publicação são simuladas só para visualizar o fluxo. */
(function () {
  'use strict';
  var A = window.ATRIO;
  var esc = A.esc;
  var fmt = A.fmt;
  A.setTitle('Criar lote');
  var step = Math.min(5, Math.max(1, A.n('passo', 1)));
  var scenario = A.q('c', 'resultados');
  var obra = A.q('obra', 'monet-placeholder');
  var art = A.art(obra === 'monet-placeholder' ? 'meda' : obra);
  var STEPS = ['Buscar obra', 'Conferir', 'Condições', 'Revisão'];

  function stepper() {
    var items = STEPS.map(function (t, i) {
      var cur = i + 1 === Math.min(step, 4) && step <= 4;
      return '<li' + (cur ? ' aria-current="step"' : '') + ' class="' + (i + 1 < step ? 'is-done' : '') + (cur ? ' is-current' : '') + '"><span class="step-n">' + (i + 1) + '</span><span class="step-t">' + t + '</span></li>';
    }).join('');
    return '<nav aria-label="Passos"><ol class="stepper">' + items + '</ol>' +
      (step <= 4 ? '<p class="stepper-compact">Passo ' + step + ' de 4 — ' + STEPS[step - 1] + '</p>' : '') + '</nav>';
  }

  function step1() {
    var results = '';
    if (scenario === 'carregando') {
      results = '<p role="status" class="muted">Buscando no catálogo do museu…</p><ul class="result-list">' +
        [1, 2, 3, 4].map(function () { return '<li class="result-row"><div class="artwork artwork--thumb skeleton"></div><div class="skeleton" style="height:1.1rem;width:60%"></div></li>'; }).join('') + '</ul>';
    } else if (scenario === 'erro') {
      results = '<p class="notice notice--danger" role="alert"><strong>O catálogo do museu está indisponível agora.</strong> Tente de novo em instantes. O restante do ÁTRIO continua funcionando.</p>' +
        '<p><button class="btn" type="button" data-go="1">Tentar novamente</button></p>';
    } else if (scenario === 'vazio') {
      results = '<div class="empty-state"><h2>Nenhuma obra encontrada para “xyz”</h2><p>Tente outro termo, como o nome do artista ou da obra. Só aparecem obras de domínio público.</p></div>';
    } else if (scenario === 'resultados') {
      var list = A.ARTWORKS.slice(0, 8);
      results = '<p class="muted result-count" role="status">' + list.length + ' obras de domínio público</p><ul class="result-list">' +
        list.map(function (a, i) {
          return '<li class="result-row">' + A.artworkHtml(a, { thumb: true, decorative: true, index: i }) +
            '<div class="result-text"><span class="lot-title-sm">' + esc(a.title) + '</span><span class="lot-artist">' + esc(a.artist) + ' · ' + esc(a.date) + '</span></div>' +
            '<button class="btn btn-sm" type="button" data-pick="' + a.key + '">Escolher<span class="visually-hidden"> ' + esc(a.title) + '</span></button></li>';
        }).join('') + '</ul>';
    }
    return '<h1>Buscar obra</h1><p class="muted">Pesquise no acervo do Art Institute of Chicago. Só obras de domínio público podem virar lote.</p>' +
      '<form class="search-form" role="search"><div class="field"><label class="field-label" for="termo">Obra ou artista</label>' +
      '<div class="search-row"><input class="input" id="termo" type="search" ' + (scenario !== 'inicio' ? 'value="' + (scenario === 'vazio' ? 'xyz' : 'impressionismo') + '"' : '') + '>' +
      '<button class="btn btn-primary" type="submit">Buscar</button></div></div></form>' + results;
  }

  function step2() {
    return '<h1>Conferir a obra</h1><p class="muted">Estes dados serão copiados para o lote. Depois de criado, o lote não depende mais do catálogo do museu.</p>' +
      '<div class="confirm-grid"><div>' + A.artworkHtml(art, { eager: true, fit: 'contain', ratio: Math.min(1.5, Math.max(0.8, art.w / art.h)).toFixed(3) + ' / 1', index: 0 }) +
      '<p class="credit">' + esc(art.credit) + '</p></div>' +
      '<div><h2 class="art-h">' + esc(art.title) + '</h2><dl class="ficha">' + [
        ['Artista', esc(art.artist) + ' (' + esc(art.artistInfo) + ')'], ['Data', esc(art.date)], ['Técnica', esc(art.medium)], ['Dimensões', esc(art.dims)],
        ['Departamento', esc(art.dept)], ['Tipo', 'Pintura'], ['Fonte', '<a href="https://www.artic.edu/artworks/' + art.id + '" rel="noopener">artic.edu/artworks/' + art.id + '</a>']
      ].map(function (r) { return '<div><dt>' + r[0] + '</dt><dd>' + r[1] + '</dd></div>'; }).join('') + '</dl>' +
      '<div class="form-actions"><button class="btn btn-primary" type="button" data-go="3">Usar esta obra</button><button class="btn" type="button" data-go="1">Escolher outra</button></div></div></div>';
  }

  function step3() {
    var bad = scenario === 'erro';
    return '<h1>Condições do lote</h1><p class="muted">Horários no fuso de São Paulo (UTC−3). Os valores são em reais.</p>' +
      '<form class="terms-form" novalidate><div class="terms-grid">' +
      '<div class="field"><label class="field-label" for="inicio">Início</label><input class="input" id="inicio" type="datetime-local" value="2026-10-27T10:00"></div>' +
      '<div class="field"><label class="field-label" for="fim">Fim</label><input class="input" id="fim" type="datetime-local" value="' + (bad ? '2026-10-27T09:00' : '2026-10-27T18:00') + '"' + (bad ? ' aria-invalid="true" aria-describedby="fim-erro"' : '') + '>' +
      (bad ? '<p class="field-error" id="fim-erro">O fim precisa ser depois do início.</p>' : '') + '</div>' +
      '<div class="field"><label class="field-label" for="lance-inicial">Lance inicial</label><div class="input-money"><span class="prefix" aria-hidden="true">R$</span><input class="input" id="lance-inicial" inputmode="decimal" value="10.000,00"></div></div>' +
      '<div class="field"><label class="field-label" for="incremento">Incremento mínimo</label><div class="input-money"><span class="prefix" aria-hidden="true">R$</span><input class="input" id="incremento" inputmode="decimal" value="500,00"></div><p class="field-hint">Cada novo lance precisa superar o atual em pelo menos este valor.</p></div>' +
      '</div><div class="form-actions"><button class="btn btn-primary" type="button" data-go="4">Revisar</button><button class="btn" type="button" data-go="2">Voltar</button></div></form>';
  }

  function step4() {
    return '<h1>Revisão</h1><p class="muted">Confira tudo antes de publicar. Depois de publicado, o lote aparece na vitrine.</p>' +
      '<div class="confirm-grid"><div>' + A.artworkHtml(art, { fit: 'contain', ratio: Math.min(1.5, Math.max(0.8, art.w / art.h)).toFixed(3) + ' / 1', index: 0 }) + '</div>' +
      '<div><h2 class="art-h">' + esc(art.title) + '</h2><p class="room-artist">' + esc(art.artist) + '</p><dl class="ficha">' + [
        ['Início', '27 out 2026, 10:00'], ['Fim', '27 out 2026, 18:00'], ['Lance inicial', fmt(1000000)], ['Incremento mínimo', fmt(50000)]
      ].map(function (r) { return '<div><dt>' + r[0] + '</dt><dd>' + r[1] + '</dd></div>'; }).join('') + '</dl>' +
      '<div class="form-actions"><button class="btn btn-primary" type="button" data-go="5">Publicar lote</button><button class="btn" type="button" data-go="3">Voltar e editar</button></div></div></div>';
  }

  function step5() {
    return '<div class="published"><p class="notice notice--success" role="status"><strong>Lote publicado.</strong> Ele já aparece na vitrine como agendado.</p>' +
      '<h1>' + esc(art.title) + '</h1><p class="room-artist">' + esc(art.artist) + '</p>' +
      '<div class="form-actions"><a class="btn btn-primary" href="' + A.href('meus-lotes.html') + '">Ver meus lotes</a><a class="btn" href="' + A.roomHref(art.key, 'agendado', { papel: 'leiloeiro' }) + '">Abrir a sala do lote</a>' +
      '<button class="btn" type="button" data-go="1">Criar outro lote</button></div></div>';
  }

  function render() {
    var parts = [step1, step2, step3, step4, step5];
    A.mount('<div class="page-container page create">' + stepper() + '<section class="create-body" aria-live="polite">' + parts[step - 1]() + '</section></div>');
    document.querySelectorAll('[data-go]').forEach(function (b) {
      b.addEventListener('click', function () { step = parseInt(b.getAttribute('data-go'), 10); if (step === 1 && scenario !== 'resultados') scenario = 'resultados'; render(); window.scrollTo(0, 0); });
    });
    document.querySelectorAll('[data-pick]').forEach(function (b) {
      b.addEventListener('click', function () { art = A.art(b.getAttribute('data-pick')); step = 2; render(); window.scrollTo(0, 0); });
    });
    var f = document.querySelector('.search-form');
    if (f) f.addEventListener('submit', function (e) { e.preventDefault(); scenario = 'resultados'; render(); });
    var t = document.querySelector('.terms-form');
    if (t) t.addEventListener('submit', function (e) { e.preventDefault(); });
  }
  render();
})();

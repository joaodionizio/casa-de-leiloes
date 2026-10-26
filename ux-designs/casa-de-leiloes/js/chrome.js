/* Moldura comum às telas: cabeçalho por papel, rodapé, menu mobile, fallback de imagem.
   Só navegação e apresentação. Nenhuma API, autenticação, relógio ou WebSocket. */
(function () {
  'use strict';
  var A = window.ATRIO;
  var body = document.body;
  var page = body.getAttribute('data-page') || '';
  var defaultRole = body.getAttribute('data-role') || 'visitante';
  var role = A.role(defaultRole);
  // Telas exclusivas de um papel não fazem sentido para outro.
  var only = body.getAttribute('data-only-role');
  if (only) role = only;
  A.currentRole = role;
  A.page = page;

  var ROLE_LABEL = { licitante: 'Licitante', leiloeiro: 'Leiloeiro' };
  var NAV = {
    visitante: [['Vitrine', 'vitrine.html', 'vitrine']],
    licitante: [['Vitrine', 'vitrine.html', 'vitrine'], ['Carteira', 'carteira.html', 'carteira'], ['Meus arremates', 'meus-arremates.html', 'meus-arremates']],
    leiloeiro: [['Vitrine', 'vitrine.html', 'vitrine'], ['Criar lote', 'criar-lote.html', 'criar-lote'], ['Meus lotes', 'meus-lotes.html', 'meus-lotes']]
  };

  var MARK =
    '<svg class="atrio-mark" xmlns="http://www.w3.org/2000/svg" viewBox="2 1 28 38" width="' + (32 * 28 / 38).toFixed(2) + '" height="32" aria-hidden="true" focusable="false">' +
    '<path fill="var(--mark-face-light)" d="M16 1C10.5 4.5 2 9.5 2 17V39H7.6V21C7.6 16.3 10.8 14.1 15.2 14.1H16Z"/>' +
    '<path fill="var(--mark-face-strong)" d="M16 1V14.1C17.1 14.2 17.4 14.7 17.7 15.8L23.5 39H30V20C30 12 24 5 16 1Z"/></svg>';

  A.setTitle = function (name) {
    document.title = name === 'ÁTRIO' ? 'ÁTRIO' : name + ' — ÁTRIO';
  };

  function renderHeader() {
    var host = document.getElementById('site-header');
    if (!host) return;
    var items = NAV[role].map(function (it) {
      var cur = it[2] === page ? ' aria-current="page"' : '';
      return '<a class="site-nav-item" href="' + A.href(it[1]) + '"' + cur + '>' + it[0] + '</a>';
    }).join('');
    var user;
    if (role === 'visitante') {
      user = '<div class="site-user"><a class="btn btn-sm" href="' + A.href('login.html') + '">Entrar</a></div>';
    } else {
      user = '<div class="site-user"><span class="site-role">' + ROLE_LABEL[role] + '</span>' +
        '<a class="btn btn-sm" href="' + A.href('vitrine.html', { papel: 'visitante' }) + '">Sair</a></div>';
    }
    host.outerHTML =
      '<a class="visually-hidden" href="#main">Pular para o conteúdo</a>' +
      '<header class="site-header"><div class="page-container site-header-inner">' +
      '<a class="site-brand" href="' + A.href('vitrine.html') + '" aria-label="ÁTRIO — Leilões de Arte — ir para a vitrine">' + MARK +
      '<span class="site-brand-text"><span class="site-brand-name">ÁTRIO</span><span class="site-brand-tagline">Leilões de Arte</span></span></a>' +
      '<button class="menu-toggle" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button>' +
      '<nav class="site-nav" id="site-nav" aria-label="Principal">' + items + user + '</nav>' +
      '</div></header>';
    var toggle = document.querySelector('.menu-toggle');
    var nav = document.getElementById('site-nav');
    toggle.addEventListener('click', function () {
      var open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', open ? 'false' : 'true');
      if (open) nav.removeAttribute('data-open'); else nav.setAttribute('data-open', 'true');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
        toggle.setAttribute('aria-expanded', 'false');
        nav.removeAttribute('data-open');
        toggle.focus();
      }
    });
  }

  function renderFooter() {
    var host = document.getElementById('site-footer');
    if (!host) return;
    var tag = A.framed ? '' : '<p class="prototype-tag">Protótipo de UX de referência · dados e cenários simulados · não é o produto</p>';
    host.outerHTML =
      '<footer class="site-footer"><div class="page-container site-footer-inner">' +
      '<span>ÁTRIO — Leilões de Arte</span>' +
      '<span>Imagens das obras: Art Institute of Chicago, domínio público.</span>' +
      '</div></footer>' + tag;
  }

  // Imagem que falha vira placeholder local; o resto da tela segue funcionando (AD-22).
  document.addEventListener('error', function (e) {
    var t = e.target;
    if (t && t.tagName === 'IMG') {
      var box = t.closest('.artwork');
      if (box) box.classList.add('artwork--fallback');
    }
  }, true);

  // Setas dos rails (só navegação).
  A.initRails = function () {
    document.querySelectorAll('[data-rail]').forEach(function (wrap) {
      var rail = wrap.querySelector('.rail');
      var controls = wrap.querySelector('.rail-controls');
      if (!rail || !controls) return;
      function refresh() {
        controls.setAttribute('data-overflow', rail.scrollWidth > rail.clientWidth + 4 ? 'true' : 'false');
      }
      controls.querySelectorAll('button').forEach(function (b) {
        b.addEventListener('click', function () {
          var dir = b.getAttribute('data-dir') === 'next' ? 1 : -1;
          rail.scrollBy({ left: dir * rail.clientWidth * 0.8, behavior: 'smooth' });
        });
      });
      refresh();
      window.addEventListener('resize', refresh);
    });
  };

  A.railControls = function (label) {
    return '<div class="rail-controls" data-overflow="false">' +
      '<button class="btn btn-sm" type="button" data-dir="prev" aria-label="' + label + ': anteriores">←</button>' +
      '<button class="btn btn-sm" type="button" data-dir="next" aria-label="' + label + ': próximos">→</button></div>';
  };

  A.mount = function (html) {
    var main = document.getElementById('main');
    main.innerHTML = html;
  };

  renderHeader();
  renderFooter();

  // Avisa o hub (quando em iframe) qual tela e papel estão abertos.
  window.addEventListener('load', function () {
    if (window.parent !== window) {
      try {
        window.parent.postMessage({ atrio: 'loaded', page: page, role: role, search: window.location.search }, '*');
      } catch (err) { /* sem hub */ }
    }
    if (A.initRails) A.initRails();
  });
})();

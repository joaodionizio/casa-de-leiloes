/* Login. Cenários: ?c=normal|erro|enviando. Navegação demonstrativa: o envio leva à Vitrine como licitante. */
(function () {
  'use strict';
  var A = window.ATRIO;
  var c = A.q('c', 'normal');
  A.setTitle('Entrar');
  var busy = c === 'enviando';
  var plate = A.art('renoir');
  var html = '<div class="login">' +
    '<div class="login-plate" aria-hidden="false"><figure>' +
    A.artworkHtml(plate, { eager: true, fit: 'contain', ratio: '4 / 5', index: 0 }) +
    '<figcaption class="credit">' + A.esc(plate.title) + ' — ' + A.esc(plate.artist) + '. ' + A.esc(plate.credit) + '.</figcaption></figure></div>' +
    '<div class="login-main"><div class="login-form-wrap">' +
    '<p class="eyebrow">ÁTRIO — Leilões de Arte</p><h1>Entrar</h1>' +
    '<p class="muted">Acesse sua conta de licitante ou de leiloeiro.</p>' +
    '<form class="login-form" novalidate' + (busy ? ' aria-busy="true"' : '') + '>' +
    (c === 'erro' ? '<p class="notice notice--danger" role="alert"><strong>E-mail ou senha incorretos.</strong> Confira os dados e tente novamente.</p>' : '') +
    '<div class="field"><label class="field-label" for="email">E-mail</label><input class="input" id="email" type="email" autocomplete="username" ' + (c === 'erro' ? 'value="marina@exemplo.com" ' : '') + (busy ? 'disabled' : '') + '></div>' +
    '<div class="field"><label class="field-label" for="senha">Senha</label><input class="input" id="senha" type="password" autocomplete="current-password" ' + (busy ? 'disabled' : '') + '></div>' +
    '<button class="btn btn-primary login-submit" type="submit"' + (busy ? ' disabled' : '') + '>' + (busy ? 'Entrando…' : 'Entrar') + '</button>' +
    '</form></div></div></div>';
  A.mount(html);
  var f = document.querySelector('.login-form');
  f.addEventListener('submit', function (e) {
    e.preventDefault();
    window.location.href = A.href('vitrine.html', { papel: 'licitante' });
  });
})();

/* Pequenos montadores de HTML compartilhados entre as telas (só apresentação). */
(function () {
  'use strict';
  var A = window.ATRIO;
  var esc = A.esc;

  var STATES = {
    live: ['live', '●', 'Ao vivo'],
    scheduled: ['scheduled', '○', 'Agendado'],
    ended: ['ended', '', 'Encerrado'],
    pending: ['pending', '◐', 'Encerrado, apurando resultado'],
    leading: ['leading', '✓', 'Você está ganhando'],
    outbid: ['outbid', '↑', 'Você foi superado'],
    won: ['won', '✓', 'Você arrematou este lote']
  };

  // Estado sempre em texto, com símbolo; nunca só cor (DESIGN §14).
  A.stateHtml = function (kind, textOverride) {
    var s = STATES[kind];
    var sym = s[1] ? '<span class="sym" aria-hidden="true">' + s[1] + '</span>' : '';
    return '<span class="lot-state lot-state--' + s[0] + '">' + sym + '<span>' + esc(textOverride || s[2]) + '</span></span>';
  };

  A.roomHref = function (obraKey, fase, extra) {
    var e = { obra: obraKey, fase: fase };
    if (extra) for (var k in extra) e[k] = extra[k];
    return A.href('sala.html', e);
  };

  A.loadingBlock = function (label) {
    return '<p class="visually-hidden" role="status">' + esc(label) + '</p>';
  };
})();

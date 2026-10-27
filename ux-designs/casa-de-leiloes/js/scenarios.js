/* Cenários de UX: lê a querystring. Cada cenário é um link (ex.: sala.html?papel=licitante&pos=superado).
   Cenário é apresentação simulada, nunca regra de produção. */
(function () {
  'use strict';
  var ATRIO = window.ATRIO || (window.ATRIO = {});
  var params = new URLSearchParams(window.location.search);

  ATRIO.params = params;
  ATRIO.framed = params.get('frame') === '1';

  ATRIO.q = function (name, def) {
    var v = params.get(name);
    return v === null || v === '' ? def : v;
  };

  ATRIO.n = function (name, def) {
    var v = parseInt(params.get(name), 10);
    return isNaN(v) || v < 0 ? def : v;
  };

  // Papel de interface: visitante | licitante | leiloeiro. O servidor é quem decide o papel real.
  ATRIO.role = function (fallback) {
    var r = params.get('papel');
    if (r === 'visitante' || r === 'licitante' || r === 'leiloeiro') return r;
    return fallback || 'visitante';
  };

  // Link interno que preserva o papel, a moldura e o cenário de imagens.
  ATRIO.href = function (page, extra) {
    var out = new URLSearchParams();
    if (ATRIO.framed) out.set('frame', '1');
    out.set('papel', ATRIO.currentRole || ATRIO.role());
    if (params.get('imagens')) out.set('imagens', params.get('imagens'));
    if (extra) for (var k in extra) if (extra[k] !== null && extra[k] !== undefined) out.set(k, extra[k]);
    return page + '?' + out.toString();
  };
})();

/* Carteira do licitante. Cenários: ?c=normal|vazia|deposito-ok|erro|enviando &valor=alto */
(function () {
  'use strict';
  var A = window.ATRIO;
  var fmt = A.fmt;
  A.setTitle('Carteira');
  var c = A.q('c', 'normal');
  var k = A.q('valor', 'normal') === 'alto' ? 75 : 1;
  var total = 10150000 * k, committed = 1650000 * k;
  if (c === 'vazia') { total = 0; committed = 0; }
  var available = total - committed;
  var feedback = '';
  if (c === 'deposito-ok') feedback = '<p class="notice notice--success" role="status"><strong>Depósito registrado.</strong> Você depositou ' + fmt(50000 * k) + '. Seu total agora é ' + fmt(total) + '.</p>';
  var invalid = c === 'erro';
  var busy = c === 'enviando';

  A.mount('<div class="page-container page wallet">' +
    '<h1>Carteira</h1>' +
    '<section class="wallet-figures" aria-label="Saldos">' +
    '<div class="wallet-main"><span class="label">Disponível para lances</span><span class="money money--xl">' + fmt(available) + '</span>' +
    (c === 'vazia' ? '<p class="muted">Faça um depósito simulado para começar a dar lances.</p>' : '') + '</div>' +
    '<dl class="wallet-side"><div><dt class="label">Saldo total</dt><dd class="money money--display">' + fmt(total) + '</dd></div>' +
    '<div><dt class="label">Comprometido em lotes</dt><dd class="money money--display">' + fmt(committed) + '</dd></div></dl></section>' +
    '<p class="wallet-rule">Disponível = total − comprometido. O valor do lote em que você lidera fica comprometido; se alguém cobrir seu lance, ele volta ao disponível na hora.</p>' +
    '<hr class="divider">' +
    '<section class="deposit" aria-labelledby="dep-t"><h2 id="dep-t">Depositar</h2>' +
    '<p class="muted">Depósito simulado: nenhum dinheiro real é movimentado.</p>' + feedback +
    '<form class="deposit-form" novalidate' + (busy ? ' aria-busy="true"' : '') + '><div class="field"><label class="field-label" for="valor">Valor do depósito</label>' +
    '<div class="input-money"><span class="prefix" aria-hidden="true">R$</span><input class="input" id="valor" inputmode="decimal" autocomplete="off" placeholder="0,00"' +
    (invalid ? ' value="250.5" aria-invalid="true" aria-describedby="valor-erro"' : '') + (busy ? ' disabled' : '') + '></div>' +
    (invalid ? '<p class="field-error" id="valor-erro">Use vírgula para os centavos. Ex.: 250,50.</p>' : '<p class="field-hint">Ex.: 1.250,00</p>') + '</div>' +
    '<button class="btn btn-primary" type="submit"' + (busy ? ' disabled' : '') + '>' + (busy ? 'Depositando…' : 'Depositar') + '</button></form></section></div>');
  document.querySelector('.deposit-form').addEventListener('submit', function (e) { e.preventDefault(); });
})();

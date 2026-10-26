/* Mesa de avaliação: escolhe tela, cenário, papel e moldura. Só navegação do protótipo.
   A coluna "story" é informação de avaliação e NÃO aparece dentro das telas (D5). */
(function () {
  'use strict';

  var ALL_ROLES = ['visitante', 'licitante', 'leiloeiro'];
  var DONE = 'entregue', PLAN = 'prevista', OUT = 'fora do protótipo';

  var SCREENS = [
    { id: 'vitrine', file: 'vitrine.html', title: 'Vitrine pública', roles: ALL_ROLES, role: 'visitante',
      scenarios: [
        { t: 'Padrão: 5 ao vivo, 8 próximos, 12 encerrados', q: {} },
        { t: '1 ao vivo (o destaque basta)', q: { vivo: 1 } },
        { t: '12 ao vivo', q: { vivo: 12 } },
        { t: 'Nenhum ao vivo, 3 próximos (destaque agendado)', q: { vivo: 0, prox: 3 } },
        { t: 'Escala: 12 ao vivo, 20 próximos, 50 encerrados', q: { vivo: 12, prox: 20, enc: 50 } },
        { t: 'Títulos longos e valores grandes', q: { variante: 'longos', vivo: 5, prox: 8, enc: 12 } },
        { t: 'Tudo vazio', q: { vivo: 0, prox: 0, enc: 0 } },
        { t: 'Sem encerrados', q: { enc: 0 } },
        { t: 'Carregando', q: { variante: 'carregando' } },
        { t: 'Erro da API do próprio sistema', q: { variante: 'erro' } },
        { t: 'Leiloeiro (sem nada publicado)', q: { vivo: 0, prox: 0, enc: 0, papel: 'leiloeiro' } }
      ],
      stories: [
        ['Destaque, Ao vivo, Próximos, Encerrados, estado "Encerrado, apurando resultado"', '2.5', DONE],
        ['Resultado final nas linhas encerradas ("Arrematado por R$ …")', '4.3 / 4.4', PLAN],
        ['"Mostrando 10 de N lotes encerrados", sem link (D4)', 'sem story', OUT],
        ['Busca e filtro de lotes', '6.5 (OPT1)', OUT],
        ['Refinamento visual final', '6.2', PLAN]
      ] },
    { id: 'login', file: 'login.html', title: 'Login', roles: ['visitante'], role: 'visitante',
      scenarios: [{ t: 'Normal', q: {} }, { t: 'Credenciais incorretas', q: { c: 'erro' } }, { t: 'Enviando', q: { c: 'enviando' } }],
      stories: [['Entrar e sair, mensagens em português, erro sem revelar se o e-mail existe', '2.2', DONE]] },
    { id: 'meus-lotes', file: 'meus-lotes.html', title: 'Meus lotes (leiloeiro)', roles: ['leiloeiro'], role: 'leiloeiro',
      scenarios: [
        { t: '30 lotes', q: {} }, { t: '3 lotes', q: { n: 3 } }, { t: 'Nenhum lote', q: { n: 0 } },
        { t: 'Confirmando cancelamento', q: { c: 'confirmar' } }, { t: 'Títulos longos', q: { variante: 'longos' } }
      ],
      stories: [
        ['Lista dos meus lotes', '2.4', DONE],
        ['Cancelar lote sem lances', '3.6', PLAN],
        ['Contagem de lances por lote', '3.4', PLAN],
        ['Resultado (arrematado, sem lances, apurando) e total recebido', '4.5', PLAN],
        ['Cancelar lote com lances e estorno', '6.6 (OPT2)', OUT]
      ] },
    { id: 'criar-lote', file: 'criar-lote.html', title: 'Criar lote (busca + revisão)', roles: ['leiloeiro'], role: 'leiloeiro',
      scenarios: [
        { t: '1 · Buscar, antes da busca', q: { passo: 1, c: 'inicio' } }, { t: '1 · Resultados', q: { passo: 1, c: 'resultados' } },
        { t: '1 · Buscando', q: { passo: 1, c: 'carregando' } }, { t: '1 · Nenhum resultado', q: { passo: 1, c: 'vazio' } },
        { t: '1 · Museu indisponível', q: { passo: 1, c: 'erro' } }, { t: '2 · Conferir a obra', q: { passo: 2 } },
        { t: '3 · Condições', q: { passo: 3 } }, { t: '3 · Condições com erro', q: { passo: 3, c: 'erro' } },
        { t: '4 · Revisão', q: { passo: 4 } }, { t: '5 · Publicado', q: { passo: 5 } }
      ],
      stories: [
        ['Busca no catálogo, lista, vazio e museu indisponível', '2.3', DONE],
        ['Conferir snapshot, condições, revisão e publicação', '2.4', DONE]
      ] },
    { id: 'sala', file: 'sala.html', title: 'Sala do lote', roles: ALL_ROLES, role: 'licitante',
      scenarios: [
        { t: 'Licitante · ao vivo, ganhando', q: { papel: 'licitante', pos: 'ganhando' } },
        { t: 'Licitante · foi superado', q: { papel: 'licitante', pos: 'superado' } },
        { t: 'Licitante · sem lances ainda', q: { papel: 'licitante', pos: 'neutro', lances: 6 } },
        { t: 'Visitante · ao vivo', q: { papel: 'visitante' } },
        { t: 'Leiloeiro · ao vivo', q: { papel: 'leiloeiro' } },
        { t: 'Recusa: abaixo do mínimo', q: { papel: 'licitante', pos: 'ganhando', msg: 'abaixo' } },
        { t: 'Recusa: saldo insuficiente', q: { papel: 'licitante', pos: 'superado', msg: 'saldo' } },
        { t: 'Recusa: já está ganhando', q: { papel: 'licitante', pos: 'ganhando', msg: 'ja-ganhando' } },
        { t: 'Recusa: lote ainda não iniciado', q: { papel: 'licitante', pos: 'neutro', msg: 'nao-iniciado' } },
        { t: 'Recusa: lote encerrado', q: { papel: 'licitante', pos: 'superado', msg: 'encerrado' } },
        { t: 'Lance aceito', q: { papel: 'licitante', msg: 'aceito' } },
        { t: 'Prorrogação (novo fim do servidor)', q: { papel: 'licitante', pos: 'ganhando', tempo: 'prorrogado', msg: 'prorrogado' } },
        { t: '00:00 sem confirmação do servidor', q: { papel: 'licitante', pos: 'ganhando', tempo: 'zero' } },
        { t: 'Reconectando', q: { papel: 'licitante', pos: 'ganhando', rede: 'reconectando' } },
        { t: 'Agendado', q: { papel: 'visitante', fase: 'agendado' } },
        { t: 'Encerrado, apurando resultado', q: { papel: 'licitante', pos: 'ganhando', fase: 'apurando' } },
        { t: 'Encerrado · você arrematou', q: { papel: 'licitante', pos: 'ganhando', fase: 'vencedor' } },
        { t: 'Encerrado · você não arrematou', q: { papel: 'licitante', pos: 'superado', fase: 'vencedor' } },
        { t: 'Encerrado sem lances', q: { papel: 'visitante', fase: 'sem-lances' } },
        { t: 'Valores altos, obra alta (El Greco)', q: { papel: 'licitante', pos: 'ganhando', valor: 'alto', obra: 'greco' } },
        { t: 'Obra retrato (Cassatt)', q: { papel: 'licitante', pos: 'superado', obra: 'cassatt' } }
      ],
      stories: [
        ['Ficha da obra, lance inicial, horários, estados (como visitante)', '2.5', DONE],
        ['Regras de aceite do lance (domínio)', '3.2', DONE],
        ['Formulário de lance, recusas com motivo, histórico, saldo, atalhos de valor', '3.5', PLAN],
        ['"Você está ganhando" / "Você foi superado", posição, "Seus lances", "Você" no histórico, sem recarregar', '4.1 (significado exato da posição: decide a story)', PLAN],
        ['Reconectando e snapshot', '4.2', PLAN],
        ['Prorrogação refletindo o novo fim do servidor', '3.4 / 4.1', PLAN],
        ['00:00 aguardando confirmação do servidor (D2)', '4.1 / 4.4', PLAN],
        ['Encerrado, apurando; resultado após liquidação; sem lances', '4.3 / 4.4', PLAN],
        ['Link da auditoria e do comprovante', '5.1 / 5.2', PLAN]
      ] },
    { id: 'carteira', file: 'carteira.html', title: 'Carteira (licitante)', roles: ['licitante'], role: 'licitante',
      scenarios: [
        { t: 'Normal', q: {} }, { t: 'Sem saldo', q: { c: 'vazia' } }, { t: 'Depósito registrado', q: { c: 'deposito-ok' } },
        { t: 'Valor inválido', q: { c: 'erro' } }, { t: 'Depositando', q: { c: 'enviando' } }, { t: 'Valores altos', q: { valor: 'alto' } }
      ],
      stories: [['Saldo total, comprometido, disponível e depósito simulado', '3.1', DONE]] },
    { id: 'meus-arremates', file: 'meus-arremates.html', title: 'Meus arremates', roles: ['licitante'], role: 'licitante',
      scenarios: [{ t: '20 lotes', q: {} }, { t: '6 lotes', q: { n: 6 } }, { t: 'Vazio', q: { n: 0 } }],
      stories: [
        ['Lotes com lance, estado e arrematados', '5.3', PLAN],
        ['Comprovante e copiar link', '5.2', PLAN],
        ['Ganhando / superado em disputa', '4.1', PLAN]
      ] },
    { id: 'comprovante', file: 'comprovante.html', title: 'Comprovante', roles: ALL_ROLES, role: 'visitante',
      scenarios: [
        { t: 'Integridade verificada', q: {} }, { t: 'Integridade não confirmada', q: { c: 'adulterado' } },
        { t: 'Imagem indisponível', q: { imagens: 'quebradas' } }, { t: 'Obra retrato (Cassatt)', q: { obra: 'cassatt' } }
      ],
      stories: [
        ['Comprovante base gerado na liquidação', '4.3', PLAN],
        ['Link público compartilhável (rota fictícia, não vinculante)', '5.2', PLAN],
        ['Estado de integridade', '5.1', PLAN]
      ] },
    { id: 'auditoria', file: 'auditoria.html', title: 'Auditoria pública', roles: ALL_ROLES, role: 'visitante',
      scenarios: [
        { t: 'Íntegro · 14 lances', q: {} }, { t: 'Íntegro · 120 lances', q: { n: 120 } },
        { t: 'Adulterado', q: { c: 'adulterado' } }, { t: 'Sem lances', q: { n: 0 } }
      ],
      stories: [
        ['Histórico completo, veredito íntegro/adulterado', '5.1', PLAN],
        ['Dados gravados em cada lance (pseudônimo, hashes, âncora)', '3.3 / 3.4', PLAN]
      ] }
  ];

  window.ATRIO_HUB = { screens: SCREENS };
  var state = { screen: 0, scn: 0, role: 'visitante', frame: '1280', img: 'ok' };
  var $ = function (s) { return document.querySelector(s); };

  function currentScreen() { return SCREENS[state.screen]; }

  function buildUrl() {
    var sc = currentScreen();
    var scn = sc.scenarios[state.scn];
    var qs = new URLSearchParams();
    qs.set('frame', '1');
    qs.set('papel', (scn.q && scn.q.papel) || state.role);
    if (state.img !== 'ok') qs.set('imagens', state.img);
    for (var k in scn.q) if (k !== 'papel') qs.set(k, scn.q[k]);
    return sc.file + '?' + qs.toString();
  }

  function renderNav() {
    var nav = $('#screen-nav');
    var ol = document.createElement('ol');
    SCREENS.forEach(function (sc, i) {
      var li = document.createElement('li');
      var b = document.createElement('button');
      b.className = 'screen-btn';
      b.type = 'button';
      b.textContent = (i + 1) + '. ' + sc.title;
      if (i === state.screen) b.setAttribute('aria-current', 'true');
      b.addEventListener('click', function () {
        state.screen = i; state.scn = 0; state.role = sc.role; refresh();
      });
      li.appendChild(b);
      if (i === state.screen) {
        var ul = document.createElement('ul');
        ul.className = 'scn-list';
        sc.scenarios.forEach(function (s, j) {
          var li2 = document.createElement('li');
          var b2 = document.createElement('button');
          b2.className = 'scn-btn'; b2.type = 'button'; b2.textContent = s.t;
          if (j === state.scn) b2.setAttribute('aria-current', 'true');
          b2.addEventListener('click', function () {
            state.scn = j;
            if (s.q && s.q.papel) state.role = s.q.papel;
            refresh();
          });
          li2.appendChild(b2); ul.appendChild(li2);
        });
        li.appendChild(ul);
      }
      ol.appendChild(li);
    });
    nav.innerHTML = '';
    nav.appendChild(ol);
  }

  function renderControls() {
    var sc = currentScreen();
    var scn = sc.scenarios[state.scn];
    var lockedByScenario = !!(scn.q && scn.q.papel);
    var roleGroup = $('#role-group');
    var onlyOne = sc.roles.length === 1;
    document.querySelectorAll('input[name=role]').forEach(function (r) {
      r.checked = r.value === (lockedByScenario ? scn.q.papel : state.role);
      r.disabled = sc.roles.indexOf(r.value) < 0 || lockedByScenario || onlyOne;
    });
    roleGroup.title = lockedByScenario ? 'Este cenário já define o papel' : (onlyOne ? 'Esta tela existe para um só papel' : '');
    document.querySelectorAll('input[name=frame]').forEach(function (r) { r.checked = r.value === state.frame; });
    document.querySelectorAll('input[name=img]').forEach(function (r) { r.checked = r.value === state.img; });
    $('#open-direct').href = buildUrl().replace('frame=1&', '');
    $('#now').textContent = sc.title + ' · ' + scn.t;
  }

  function renderStories() {
    var sc = currentScreen();
    $('#story-intro').textContent = 'Quais stories entregam cada elemento de “' + sc.title + '”. As telas simuladas não mostram esta informação.';
    var rows = sc.stories.map(function (s) {
      var cls = s[2] === DONE ? 'tag--done' : s[2] === OUT ? 'tag--out' : '';
      return '<tr><td>' + s[0] + '</td><td>' + s[1] + '</td><td><span class="tag ' + cls + '">' + s[2] + '</span></td></tr>';
    }).join('');
    $('#story-table').innerHTML = '<thead><tr><th scope="col">Elemento</th><th scope="col">Story</th><th scope="col">Situação</th></tr></thead><tbody>' + rows + '</tbody>';
  }

  var FRAME_H = 900;
  function renderStage() {
    var stage = $('#stage');
    stage.innerHTML = '';
    var widths = state.frame === 'all' ? [1280, 820, 390, 320] : [parseInt(state.frame, 10)];
    var url = buildUrl();
    var avail = stage.clientWidth || 900;
    var gap = 16;
    var total = widths.reduce(function (a, b) { return a + b; }, 0) + gap * (widths.length - 1);
    var scale = Math.min(1, (avail - 2) / total);
    var viewportH = Math.max(560, window.innerHeight - 170);
    widths.forEach(function (w) {
      var box = document.createElement('div');
      box.className = 'frame-box';
      var h = Math.round(Math.min(Math.max(viewportH / scale, 700), 2400));
      if (state.frame !== 'all') h = Math.round(Math.max(viewportH / scale, 640));
      var label = document.createElement('p');
      label.className = 'frame-label';
      label.textContent = w + ' px' + (scale < 1 ? ' (exibido a ' + Math.round(scale * 100) + '%)' : '');
      var clip = document.createElement('div');
      clip.className = 'frame-clip';
      clip.style.width = Math.round(w * scale) + 'px';
      clip.style.height = Math.round(h * scale) + 'px';
      var f = document.createElement('iframe');
      f.title = 'Tela do protótipo em ' + w + ' px';
      f.src = url;
      f.width = w; f.height = h;
      f.style.width = w + 'px'; f.style.height = h + 'px';
      f.style.transform = 'scale(' + scale + ')';
      clip.appendChild(f); box.appendChild(label); box.appendChild(clip); stage.appendChild(box);
    });
  }

  function refresh() {
    renderNav(); renderControls(); renderStories(); renderStage();
  }

  document.querySelectorAll('input[name=role]').forEach(function (r) {
    r.addEventListener('change', function () { state.role = r.value; renderControls(); renderStage(); });
  });
  document.querySelectorAll('input[name=frame]').forEach(function (r) {
    r.addEventListener('change', function () { state.frame = r.value; renderControls(); renderStage(); });
  });
  document.querySelectorAll('input[name=img]').forEach(function (r) {
    r.addEventListener('change', function () { state.img = r.value; renderControls(); renderStage(); });
  });
  var resizeTimer;
  window.addEventListener('resize', function () { clearTimeout(resizeTimer); resizeTimer = setTimeout(renderStage, 150); });

  // Sincroniza a lista quando a pessoa navega por links dentro da moldura (só no modo de uma moldura).
  window.addEventListener('message', function (e) {
    var d = e.data;
    if (!d || d.atrio !== 'loaded' || state.frame === 'all') return;
    for (var i = 0; i < SCREENS.length; i++) {
      if (SCREENS[i].id === d.page && i !== state.screen) {
        state.screen = i; state.scn = 0; state.role = d.role;
        renderNav(); renderControls(); renderStories();
        $('#now').textContent = SCREENS[i].title + ' · aberta por link dentro da moldura';
        return;
      }
    }
    if (d.role && d.role !== state.role && SCREENS[state.screen].roles.length > 1) { state.role = d.role; renderControls(); }
  });

  state.role = SCREENS[0].role;
  refresh();
})();

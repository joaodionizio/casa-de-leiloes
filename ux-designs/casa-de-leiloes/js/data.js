/* Dados FICTÍCIOS do protótipo de UX e geradores de volume.
   Só título, artista, data, crédito e imagem das obras são reais (SOURCES.md).
   Lances, valores, horários, pseudônimos e hashes são inventados para ilustrar cenários.
   Nada aqui é regra de produção: o navegador nunca decide estado, vencedor, saldo ou
   fechamento (AD-6, AD-19). */
(function () {
  'use strict';

  var ARTWORKS = [
    { key: 'seurat', file: 'seurat-grande-jatte.jpg', w: 1000, h: 670, id: 27992,
      title: 'A Sunday on La Grande Jatte — 1884', artist: 'Georges Seurat', artistInfo: 'francês, 1859–1891',
      date: '1884–86, borda acrescentada em 1888–89', medium: 'Óleo sobre tela', dims: '207,5 × 308,1 cm',
      dept: 'Painting and Sculpture of Europe', credit: 'Helen Birch Bartlett Memorial Collection' },
    { key: 'cassatt', file: 'cassatt-banho-da-crianca.jpg', w: 843, h: 1279, id: 111442,
      title: "The Child's Bath", artist: 'Mary Cassatt', artistInfo: 'americana, 1844–1926',
      date: '1893', medium: 'Óleo sobre tela', dims: '101,3 × 67,3 cm',
      dept: 'Arts of the Americas', credit: 'Robert A. Waller Fund' },
    { key: 'quarto', file: 'van-gogh-quarto.jpg', w: 1000, h: 783, id: 28560,
      title: 'The Bedroom', artist: 'Vincent van Gogh', artistInfo: 'holandês, 1853–1890',
      date: '1889', medium: 'Óleo sobre tela', dims: '73,6 × 92,3 cm',
      dept: 'Painting and Sculpture of Europe', credit: 'Helen Birch Bartlett Memorial Collection' },
    { key: 'greco', file: 'el-greco-assuncao.jpg', w: 523, h: 1000, id: 87479,
      title: 'The Assumption of the Virgin', artist: 'El Greco', artistInfo: 'grego, ativo na Espanha, 1541–1614',
      date: '1577–79', medium: 'Óleo sobre tela', dims: '403,2 × 211,8 cm',
      dept: 'Painting and Sculpture of Europe', credit: 'Gift of Nancy Atwood Sprague in memory of Albert Arnold Sprague' },
    { key: 'nenufares', file: 'monet-nenufares.jpg', w: 1000, h: 960, id: 16568,
      title: 'Water Lilies', artist: 'Claude Monet', artistInfo: 'francês, 1840–1926',
      date: '1906', medium: 'Óleo sobre tela', dims: '89,9 × 94,1 cm',
      dept: 'Painting and Sculpture of Europe', credit: 'Mr. and Mrs. Martin A. Ryerson Collection' },
    { key: 'caillebotte', file: 'caillebotte-rua-chuvosa.jpg', w: 1000, h: 776, id: 20684,
      title: 'Paris Street; Rainy Day', artist: 'Gustave Caillebotte', artistInfo: 'francês, 1848–1894',
      date: '1877', medium: 'Óleo sobre tela', dims: '212,2 × 276,2 cm',
      dept: 'Painting and Sculpture of Europe', credit: 'Charles H. and Mary F. S. Worcester Collection' },
    { key: 'renoir', file: 'renoir-duas-irmas.jpg', w: 806, h: 1000, id: 14655,
      title: 'Two Sisters (On the Terrace)', artist: 'Pierre-Auguste Renoir', artistInfo: 'francês, 1841–1919',
      date: '1881', medium: 'Óleo sobre tela', dims: '100,4 × 80,9 cm',
      dept: 'Painting and Sculpture of Europe', credit: 'Mr. and Mrs. Lewis Larned Coburn Memorial Collection' },
    { key: 'meda', file: 'monet-meda-de-trigo.jpg', w: 1000, h: 591, id: 64818,
      title: 'Stacks of Wheat (End of Summer)', artist: 'Claude Monet', artistInfo: 'francês, 1840–1926',
      date: '1890–91', medium: 'Óleo sobre tela', dims: '60 × 100,5 cm',
      dept: 'Painting and Sculpture of Europe', credit: 'Gift of Arthur M. Wood, Sr. in memory of Pauline Palmer Wood' },
    { key: 'autorretrato', file: 'van-gogh-autorretrato.jpg', w: 843, h: 1074, id: 80607,
      title: 'Self-Portrait', artist: 'Vincent van Gogh', artistInfo: 'holandês, 1853–1890',
      date: '1887', medium: 'Óleo sobre prancheta de artista, montada em painel', dims: '41 × 32,5 cm',
      dept: 'Painting and Sculpture of Europe', credit: 'Joseph Winterbotham Collection' },
    { key: 'cezanne', file: 'cezanne-baia-de-marselha.jpg', w: 1000, h: 801, id: 16487,
      title: "The Bay of Marseille, Seen from L'Estaque", artist: 'Paul Cézanne', artistInfo: 'francês, 1839–1906',
      date: 'c. 1885', medium: 'Óleo sobre tela', dims: '80,2 × 100,6 cm',
      dept: 'Painting and Sculpture of Europe', credit: 'Mr. and Mrs. Martin A. Ryerson Collection' }
  ];

  var MONTHS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // Mesmo formato de frontend/src/money.ts (formatCents): "R$ 1.234,56".
  function fmt(cents) {
    var padded = String(cents);
    while (padded.length < 3) padded = '0' + padded;
    var whole = padded.slice(0, -2);
    var fraction = padded.slice(-2);
    var grouped = '';
    for (var end = whole.length; end > 0; end -= 3) {
      var chunk = whole.slice(Math.max(0, end - 3), end);
      grouped = grouped === '' ? chunk : chunk + '.' + grouped;
    }
    return 'R$ ' + grouped + ',' + fraction;
  }

  function art(key) {
    for (var i = 0; i < ARTWORKS.length; i++) if (ARTWORKS[i].key === key) return ARTWORKS[i];
    return ARTWORKS[0];
  }

  // Cenário "imagens": 'quebradas' = todas falham; 'algumas' = uma em cada três falha.
  function isBroken(index) {
    var mode = ATRIO.q('imagens', 'ok');
    if (mode === 'quebradas') return true;
    if (mode === 'algumas') return index % 3 === 1;
    return false;
  }

  // Regra de enquadramento só de apresentação: paisagem preenche; retrato nunca é cortado
  // de forma agressiva (VITRINE-BLUEPRINT §11) e ganha passe-partout.
  function fitFor(a) {
    return a.w / a.h >= 1.05 ? 'cover' : 'contain';
  }

  // index: posição do item na lista, usado só para o cenário "imagens".
  function artworkHtml(a, opts) {
    opts = opts || {};
    var ratio = opts.ratio || '5 / 4';
    var src = isBroken(opts.index || 0) ? 'art/_indisponivel.jpg' : 'art/' + a.file;
    var cls = 'artwork' + (opts.thumb ? ' artwork--thumb' : '');
    var alt = opts.decorative ? '' : esc(a.title + ', ' + a.artist);
    var loading = opts.eager ? 'eager' : 'lazy';
    var style = opts.thumb ? '' : ' style="--ratio:' + ratio + '"';
    return '<div class="' + cls + '"' + style + ' data-fit="' + (opts.fit || fitFor(a)) + '" data-fallback="Imagem indisponível">' +
      '<img src="' + src + '" alt="' + alt + '" width="' + a.w + '" height="' + a.h + '" loading="' + loading + '"' +
      (opts.eager ? ' fetchpriority="high"' : '') + '></div>';
  }

  /* ---------- Lotes para a vitrine, o painel e os arremates ---------- */
  var LIVE_BIDS = [1845000, 85000, 7290000, 430000, 125000000, 2610000, 980000, 14250000, 510000, 3300000, 640000, 92000000];
  var LIVE_TIMES = ['01:42', '14:05', '42:18', '02:11:36', '05:20:09', '1 d 04 h', '1 d 22 h', '2 d 03 h', '3 d 08 h', '4 d 11 h', '5 d 02 h', '6 d 17 h'];
  var START_BIDS = [85000, 120000, 450000, 2500000, 90000, 7500000, 300000, 1500000, 60000, 18000000];
  var FINALS = [1845000, 7290000, 430000, 2610000, 980000, 14250000, 510000, 3300000, 640000, 92000000, 125000000, 85000];

  function longen(title, index, base) {
    if (ATRIO.q('variante', 'normal') !== 'longos') return title;
    if (index % 2 === 0) return title + ' (detail of the complete composition from the collection catalogue, second state)';
    return base ? title : title;
  }

  function nextArt(i, step, off) {
    return ARTWORKS[(i * step + off) % ARTWORKS.length];
  }

  function liveLots(n) {
    var out = [];
    for (var i = 0; i < n; i++) {
      var a = nextArt(i, 3, 0);
      out.push({ n: i, art: a, title: longen(a.title, i), current: LIVE_BIDS[i % LIVE_BIDS.length], ends: LIVE_TIMES[i % LIVE_TIMES.length] });
    }
    return out;
  }

  function startText(i) {
    var slots = ['Hoje · 18:00', 'Hoje · 21:30', 'Amanhã · 10:00', 'Amanhã · 14:00'];
    if (i < slots.length) return slots[i];
    var day = 28 + Math.floor((i - 4) / 2);
    var month = 9;
    if (day > 31) { day -= 31; month = 10; }
    return day + ' ' + MONTHS[month] + ' · ' + ((i % 2) ? '16:00' : '11:00');
  }

  function upcomingLots(n) {
    var out = [];
    for (var i = 0; i < n; i++) {
      var a = nextArt(i, 7, 4);
      out.push({ n: i, art: a, title: longen(a.title, i + 1), start: START_BIDS[i % START_BIDS.length], when: startText(i), in: i === 0 ? '3 h 28 min' : null });
    }
    return out;
  }

  // result: 'pending' (apurando), 'won' (arrematado), 'none' (sem lances)
  function closedLots(n) {
    var out = [];
    for (var i = 0; i < n; i++) {
      var a = nextArt(i, 3, 1);
      var result = i === 0 ? 'pending' : (i % 7 === 3 ? 'none' : 'won');
      var day = 26 - Math.floor((i + 2) / 3);
      var month = 9;
      if (day < 1) { day += 30; month = 8; }
      out.push({ n: i, art: a, title: longen(a.title, i + 2), result: result, final: FINALS[i % FINALS.length],
        when: i === 0 ? 'Encerrou há instantes' : 'Encerrado em ' + day + ' ' + MONTHS[month] });
    }
    return out;
  }

  /* ---------- Histórico de lances (pseudônimos fictícios, AD-20) ---------- */
  var ALIASES = ['Licitante-A83F19C2', 'Licitante-4D07B1E9', 'Licitante-9C52E6A0', 'Licitante-17FA3B84', 'Licitante-E2B69D05', 'Licitante-60C4A7F1'];
  var ME = ALIASES[0];

  function fakeHash(seed) {
    var h = 2166136261 >>> 0;
    var s = String(seed);
    var out = '';
    for (var r = 0; r < 8; r++) {
      for (var i = 0; i < s.length; i++) {
        h ^= s.charCodeAt(i) + r;
        h = Math.imul(h, 16777619) >>> 0;
      }
      out += ('00000000' + h.toString(16)).slice(-8);
    }
    return out;
  }

  function two(x) { return (x < 10 ? '0' : '') + x; }

  // Instante em horário de Brasília (UTC-3) a partir de ms UTC.
  function parts(ms) {
    var d = new Date(ms - 3 * 3600 * 1000);
    return { day: d.getUTCDate(), month: MONTHS[d.getUTCMonth()], year: d.getUTCFullYear(),
      time: two(d.getUTCHours()) + ':' + two(d.getUTCMinutes()) + ':' + two(d.getUTCSeconds()) };
  }

  var END_MS = Date.UTC(2026, 9, 26, 17, 31, 7); // 26 out 2026, 14:31:07 (Brasília)

  // Lances do mais novo para o mais antigo. pos: 'neutro' | 'ganhando' | 'superado'.
  function bids(opts) {
    var n = opts.n;
    var step = opts.stepSec || 197;
    var endMs = opts.endMs || END_MS;
    var out = [];
    var mine = 0;
    for (var seq = n; seq >= 1; seq--) {
      var d = n - seq; // 0 = lance mais recente
      var idx;
      if (opts.pos === 'ganhando') idx = d % 3 === 0 ? 0 : 1 + (d % 2);
      else if (opts.pos === 'superado') idx = d >= 1 && (d - 1) % 3 === 0 ? 0 : 1 + (d % 4);
      else idx = 1 + (d % 4);
      var alias = ALIASES[idx];
      var isMe = idx === 0 && opts.pos !== 'neutro';
      if (isMe) mine++;
      var t = parts(endMs - (n - seq) * step * 1000);
      out.push({ seq: seq, alias: alias, me: isMe, cents: opts.start + (seq - 1) * opts.inc,
        time: t.time, date: t.day + ' ' + t.month + ' ' + t.year, hash: fakeHash('lote:' + seq + ':' + alias),
        prev: seq === 1 ? new Array(65).join('0') : fakeHash('lote:' + (seq - 1) + ':' + ALIASES[seq % 3]) });
    }
    return { list: out, mine: mine };
  }

  var ATRIO = window.ATRIO || {};
  ATRIO.ARTWORKS = ARTWORKS;
  ATRIO.ALIASES = ALIASES;
  ATRIO.ME = ME;
  ATRIO.MONTHS = MONTHS;
  ATRIO.esc = esc;
  ATRIO.fmt = fmt;
  ATRIO.art = art;
  ATRIO.artworkHtml = artworkHtml;
  ATRIO.liveLots = liveLots;
  ATRIO.upcomingLots = upcomingLots;
  ATRIO.closedLots = closedLots;
  ATRIO.bids = bids;
  ATRIO.fakeHash = fakeHash;
  ATRIO.parts = parts;
  ATRIO.END_MS = END_MS;
  ATRIO.fitFor = fitFor;
  window.ATRIO = ATRIO;
})();

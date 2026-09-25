/* Gauge product film.
 *
 * Everything on screen is a pure function of the playhead `t` (seconds):
 * render(t) sets every animated property from scratch. That makes scrubbing,
 * chapter jumps, speed changes, and looping exact. Explore mode stops the
 * clock and hands the live UI to the viewer.
 */
(() => {
  'use strict';

  const MAP = window.GAUGE_MAP;
  const $ = (s) => document.querySelector(s);
  const app = $('#app'), stage = $('#stage'), frame = $('#frame'), camera = $('#camera'), viewport = $('#viewport');
  const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const DURATION = 92;
  const SVG = 'http://www.w3.org/2000/svg';

  // ---------- math ----------
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, p) => a + (b - a) * p;
  const seg = (t, a, b) => clamp((t - a) / (b - a));
  const E = {
    linear: (p) => p,
    out: (p) => 1 - Math.pow(1 - p, 3),
    inOut: (p) => (p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    expo: (p) => (p === 1 ? 1 : 1 - Math.pow(2, -10 * p)),
    back: (p) => { const c = 1.70158, c3 = c + 1; return 1 + c3 * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); },
    quint: (p) => 1 - Math.pow(1 - p, 5),
  };
  // Fade in over [a, a+fi], hold, fade out over [b-fo, b].
  const window_ = (t, a, b, fi = .5, fo = .5) => Math.min(seg(t, a, a + fi), 1 - seg(t, b - fo, b));
  const fmtTime = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  const num = (v) => Math.round(v).toLocaleString('en-US');

  // Write a style only when it changes (keeps 60fps with hundreds of nodes).
  const cache = new WeakMap();
  function css(el, prop, value) {
    let c = cache.get(el); if (!c) cache.set(el, (c = {}));
    if (c[prop] !== value) { c[prop] = value; el.style[prop] = value; }
  }
  function attr(el, name, value) {
    let c = cache.get(el); if (!c) cache.set(el, (c = {}));
    const k = '@' + name; if (c[k] !== value) { c[k] = value; el.setAttribute(name, value); }
  }
  function text(el, value) {
    let c = cache.get(el); if (!c) cache.set(el, (c = {}));
    if (c.text !== value) { c.text = value; el.textContent = value; }
  }
  function toggle(el, cls, on) { if (el.classList.contains(cls) !== on) el.classList.toggle(cls, on); }
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const svgEl = (tag, attrs = {}) => { const e = document.createElementNS(SVG, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };

  // ---------- content ----------
  const companies = MAP.companies;
  const aster = companies.find((c) => c.id === 'aster');
  const programsFor = (c) => [
    { name: 'CSIT SBIR/STTR Direct Financial Assistance', state: c.sbir ? 'Strong match' : 'Not a match',
      detail: c.sbir ? 'NJ base and an active SBIR award appear in the snapshot. Confirm the current round.' : 'No qualifying SBIR/STTR signal appears in the snapshot.' },
    { name: 'Angel Investor Tax Credit', state: 'Potential match, verify', detail: 'No material requirement fails. Ask about headcount and qualifying-business criteria.' },
    { name: 'Life Sciences & Healthcare Fund', state: c.lifeScience ? 'Potential match, verify' : 'Not a match',
      detail: c.lifeScience ? 'Sector and round size fit. Ask about employees, co-investors, and timing.' : 'Current sector evidence is not life sciences or healthcare.' },
  ];
  const tone = (s) => (s === 'Strong match' ? 'strong' : s.startsWith('Potential') ? 'potential' : 'none');

  const CHAPTERS = [
    { id: 'open', t: 0, title: 'Cold open', note: 'Start on black. Let the line land: every startup leaves a trace, and most of it is public.' },
    { id: 'brand', t: 6.3, title: 'Gauge', note: 'Introduce Gauge: startup signals for New Jersey, built from public records.' },
    { id: 'desktop', t: 10.8, title: 'Launch', note: 'It runs as a desktop app, and works offline on a frozen snapshot for demos.' },
    { id: 'map', t: 16, title: 'Signals map', note: 'Start with companies that already reported $1M+ sold: the ones a fund likely knows.' },
    { id: 'reveal', t: 26, title: 'All public signals', note: 'The reveal: switch to every public signal. 42 becomes 118 likely startups across 47 towns.' },
    { id: 'search', t: 32.5, title: 'Town search', note: 'Search any town. Princeton surfaces Aster BioSystems. If a town has no signal, Gauge says so, and says why that is not proof of absence.' },
    { id: 'evidence', t: 41, title: 'Evidence card', note: 'Facts cite records. Unknowns stay unknown and become first-call questions. Program matches show their work.' },
    { id: 'programs', t: 53.5, title: 'Programs', note: 'Three NJ programs encoded from official sources, with three honest result states.' },
    { id: 'pipeline', t: 60.5, title: 'Pipeline', note: 'Under the hood: Form D, SBIR, and state announcements are linked, classified, matched, and alerted. Counts are from a real run.' },
    { id: 'alerts', t: 70, title: 'Alerts', note: 'Alerts are automatic only when identity is certain (exact SEC ID). Fuzzy matches wait for a person.' },
    { id: 'measured', t: 76.5, title: 'Evidence, not certainty', note: 'Close on trust: facts, inferences, and unknowns are always labeled.' },
    { id: 'finale', t: 84, title: 'Finale', note: 'One common track for New Jersey\'s startup signals. 1,435 mm is standard railroad gauge.' },
  ];

  const CAPTIONS = [
    [11.8, 15.4, 'Gauge runs on your desktop, even offline.'],
    [17.2, 25.6, 'It reads SEC Form D filings, federal SBIR awards, and state announcements.'],
    [27.6, 32.2, 'Switch from “already funded” to every public signal.'],
    [33.4, 40.6, 'Search any New Jersey town.'],
    [42.4, 47.2, 'Every fact links to the public record it came from.'],
    [47.2, 51.8, 'What the records can’t tell you becomes a first-call question.'],
    [55, 60, 'Three New Jersey programs. Three honest states.'],
    [71, 76, 'Alerts fire automatically only when identity is certain.'],
  ];

  const NOTIFS = [
    { title: 'Lucent Grid Works raised again', body: 'New SEC Form D · $4,000,000 offering · Newark', tag: 'Ready · exact SEC ID', held: false, time: 'now' },
    { title: 'Possible match: Harbor Robotics', body: 'SBIR award name matches, different ZIP. Waiting for a person.', tag: 'Held for review', held: true, time: '2m ago' },
    { title: 'Delta Neuro Devices won Phase II', body: 'NIH SBIR Phase II · New Brunswick', tag: 'Ready · linked record', held: false, time: '9m ago' },
  ];

  const PIPE = {
    sources: [
      { id: 's1', title: 'SEC Form D', sub: 'NJ issuers, quarterly + daily', count: 5948, x: 110, y: 330 },
      { id: 's2', title: 'SBIR / STTR', sub: 'Federal R&D awards', count: 5166, x: 110, y: 520 },
      { id: 's3', title: 'NJEDA · CSIT', sub: 'Award announcements', count: null, x: 110, y: 710 },
    ],
    steps: [
      { id: 'n1', label: '01 · LINK', title: 'Link & dedupe', sub: 'Exact SEC ID and name + ZIP merge; fuzzy matches go to review.', count: 4346, unit: 'companies', x: 520, y: 470 },
      { id: 'n2', label: '02 · CLASSIFY', title: 'Likely startup?', sub: 'Transparent features, hard exclusions, reasons shown.', count: 1185, unit: 'likely startups', x: 880, y: 470 },
      { id: 'n3', label: '03 · MATCH', title: 'NJ programs', sub: 'CSIT, Angel Tax Credit, Life Sciences Fund.', count: 3, unit: 'rule sets', x: 1240, y: 470 },
      { id: 'n4', label: '04 · ALERT', title: 'Alert feed', sub: 'Automatic only on exact identity.', count: 53, unit: 'ready alerts', x: 1600, y: 470 },
    ],
  };

  // ---------- build DOM ----------
  const mapSvg = $('#map');
  mapSvg.setAttribute('viewBox', `0 0 ${MAP.width} ${MAP.height}`);
  mapSvg.innerHTML = `<defs><linearGradient id="nj-fill" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#dce7e3" stop-opacity=".8"/><stop offset="1" stop-color="#9dbab1" stop-opacity=".6"/></linearGradient></defs>`;
  const statePathD = MAP.state;
  const gShadow = svgEl('path', { d: statePathD, class: 'state-shadow' });
  const gFill = svgEl('path', { d: statePathD, class: 'state-fill' });
  const gCounties = svgEl('path', { d: MAP.counties, class: 'county-lines' });
  const gOutline = svgEl('path', { d: statePathD, class: 'state-outline' });
  mapSvg.append(gShadow, gFill, gCounties, gOutline);
  const labels = [['PENNSYLVANIA', 30, 250], ['NEW YORK', 380, 60], ['ATLANTIC OCEAN', 430, 560]].map(([s, x, y]) => {
    const tEl = svgEl('text', { x, y, class: 'place-label' }); tEl.textContent = s; mapSvg.append(tEl); return tEl;
  });
  const markerLayer = svgEl('g'); mapSvg.append(markerLayer);
  const markers = [];
  const addMarker = (xy, funded, company, i) => {
    const g = svgEl('g');
    const ripple = svgEl('circle', { cx: xy[0], cy: xy[1], r: 6, class: 'ripple', opacity: 0 });
    const dot = svgEl('circle', { cx: xy[0], cy: xy[1], r: 7, class: 'marker' + (funded ? ' funded' : '') + (company ? '' : ' extra') });
    g.append(ripple, dot); markerLayer.append(g);
    const m = { g, dot, ripple, xy, funded, company, i, seed: (Math.sin(i * 91.7) + 1) / 2 };
    if (company) g.addEventListener('click', () => explore.openCompany(company));
    markers.push(m); return m;
  };
  companies.forEach((c, i) => addMarker(c.xy, c.funded, c, i));
  MAP.extra.forEach((e, i) => addMarker(e.xy, false, null, i + 20));
  const fundedMarkers = markers.filter((m) => m.company && m.funded);
  const otherMarkers = markers.filter((m) => !(m.company && m.funded));
  const pulse = svgEl('circle', { class: 'pulse', r: 0, cx: aster.xy[0], cy: aster.xy[1], opacity: 0 });
  markerLayer.prepend(pulse);
  const outlineLen = gOutline.getTotalLength();
  gOutline.style.strokeDasharray = `${outlineLen}`;

  // Priority rows
  const rowsEl = $('#rows');
  const funded5 = companies.filter((c) => c.funded).slice(0, 5);
  const all5 = companies.slice(0, 5);
  function buildRows(list) {
    rowsEl.innerHTML = '';
    list.forEach((c, i) => {
      const r = el('button', 'row', `<em>${String(i + 1).padStart(2, '0')}</em><span><strong>${c.name}</strong><small>${c.town} · ${c.sector}</small></span><i class="${c.tier === 'Review first' ? 'review' : ''}">${c.tier}</i>`);
      r.dataset.id = c.id;
      r.addEventListener('click', () => explore.openCompany(c));
      rowsEl.append(r);
    });
  }
  let rowsMode = null;
  function setRows(mode) { if (rowsMode !== mode) { rowsMode = mode; buildRows(mode === 'all' ? all5 : funded5); } }
  setRows('funded');

  // Detail panel
  let detailFor = null;
  function fillDetail(c) {
    if (detailFor === c.id) return; detailFor = c.id;
    text($('#d-mono'), c.name.split(' ').map((w) => w[0]).slice(0, 2).join(''));
    text($('#d-sub'), `${c.town.toUpperCase()}, NEW JERSEY · FOUNDED ${c.year}`);
    text($('#d-name'), c.name); text($('#d-desc'), c.description);
    $('#d-pills').innerHTML = `<span>✓ Likely startup</span><span>High-confidence match</span><span>${c.tier} in ${c.sector}</span>`;
    $('#d-evidence').innerHTML = c.evidence.map((e) => `<div class="ev"><b>✓</b><span>${e}<small>View linked source ↗</small></span></div>`).join('');
    $('#d-unknowns').innerHTML = c.unknowns.map((u) => `<div class="unk">— ${u}</div>`).join('');
    $('#d-programs').innerHTML = programsFor(c).map((p) => `<div class="match ${tone(p.state)}"><span>${p.state}</span><strong>${p.name}</strong><p>${p.detail}</p></div>`).join('');
  }
  fillDetail(aster);

  // Notifications
  const notifsEl = $('#notifs');
  const notifEls = NOTIFS.map((n) => {
    const e = el('div', 'notif', `<span class="brand-mark"><span></span><span></span><i></i><i></i><i></i></span><div><header><span>GAUGE</span><span>${n.time}</span></header><strong>${n.title}</strong><p>${n.body}</p><span class="tag ${n.held ? 'held' : ''}">${n.tag}</span></div>`);
    notifsEl.append(e); return e;
  });

  // Kinetic headlines: split into characters (keeping inline markup like <em>)
  function splitChars(h) {
    const walk = (node) => {
      [...node.childNodes].forEach((ch) => {
        if (ch.nodeType === 3) {
          const frag = document.createDocumentFragment();
          [...ch.textContent].forEach((c) => { const s = el('span', 'ch'); s.textContent = c === ' ' ? ' ' : c; frag.append(s); });
          ch.replaceWith(frag);
        } else walk(ch);
      });
    };
    walk(h); return [...h.querySelectorAll('.ch')];
  }
  const open1 = $('#t-open1'), open2 = $('#t-open2');
  const open1Chars = splitChars(open1), open2Chars = splitChars(open2);

  // Rails ties
  function ties(g, n, x0, x1, y0, y1) {
    for (let i = 0; i < n; i++) { const x = lerp(x0, x1, i / (n - 1)); g.append(svgEl('rect', { x: x - 5, y: y0, width: 10, height: y1 - y0, rx: 3, class: 'tie' })); }
    return [...g.children];
  }
  const heroTies = ties($('#hero-ties'), 12, 50, 550, 30, 90);
  const heroRails = [...document.querySelectorAll('#hero-rails .rail')];
  const finalTies = ties($('#final-ties'), 40, -40, 1960, 50, 150);
  const finalRails = [...document.querySelectorAll('#final-rails .rail')];

  // Pipeline
  const pipeNodes = $('#pipe-nodes'), pipeSvg = $('#pipe-svg');
  const nodeEls = {};
  const allNodes = [...PIPE.sources.map((s) => ({ ...s, src: true })), ...PIPE.steps];
  allNodes.forEach((n) => {
    const e = el('div', 'pnode' + (n.src ? ' src' : ''), n.src
      ? `<small>SOURCE</small><strong>${n.title}</strong><span>${n.sub}</span>${n.count ? `<b data-n="${n.count}">0</b>` : '<b>live</b>'}`
      : `<small>${n.label}</small><strong>${n.title}</strong><span>${n.sub}</span><b data-n="${n.count}">0</b><span>${n.unit}</span>`);
    e.style.left = n.x + 'px'; e.style.top = n.y + 'px'; pipeNodes.append(e); nodeEls[n.id] = e;
  });
  const pipePaths = [];
  const connect = (a, b) => {
    const ax = a.x + (a.src ? 230 : 260), ay = a.y + (a.src ? 70 : 110), bx = b.x, by = b.y + 110;
    const p = svgEl('path', { d: `M${ax},${ay} C${ax + 110},${ay} ${bx - 110},${by} ${bx},${by}` });
    pipeSvg.append(p); const len = p.getTotalLength(); p.style.strokeDasharray = `${len}`;
    const dots = [0, .33, .66].map(() => { const c = svgEl('circle', { r: 5, opacity: 0 }); pipeSvg.append(c); return c; });
    pipePaths.push({ p, len, dots }); return pipePaths.length - 1;
  };
  PIPE.sources.forEach((s) => connect(s, PIPE.steps[0]));
  for (let i = 0; i < PIPE.steps.length - 1; i++) connect(PIPE.steps[i], PIPE.steps[i + 1]);

  // Starfield that condenses into New Jersey's signals.
  const stars = $('#stars'), sctx = stars.getContext('2d');
  stars.width = 1920; stars.height = 1080;
  let rs = 7; const rnd = () => ((rs = (rs * 16807) % 2147483647) / 2147483647);
  const NJ_SCALE = 1.05, NJ_OX = 960 - (MAP.width * NJ_SCALE) / 2, NJ_OY = 540 - (MAP.height * NJ_SCALE) / 2;
  const starPts = markers.map((m) => ({ x: rnd() * 1920, y: rnd() * 1080, tx: NJ_OX + m.xy[0] * NJ_SCALE, ty: NJ_OY + m.xy[1] * NJ_SCALE, v: .2 + rnd() * .6, funded: m.funded }));
  const dust = Array.from({ length: 260 }, () => ({ x: rnd() * 1920, y: rnd() * 1080, r: rnd() * 1.4 + .3, v: rnd() * 8 + 2, a: rnd() * .5 + .1 }));
  function drawStars(t, alpha) {
    sctx.clearRect(0, 0, 1920, 1080);
    if (alpha <= 0) return;
    sctx.globalAlpha = alpha;
    for (const d of dust) { sctx.fillStyle = `rgba(255,255,255,${d.a})`; sctx.beginPath(); sctx.arc((d.x + t * d.v) % 1920, d.y, d.r, 0, 7); sctx.fill(); }
    const gather = E.inOut(seg(t, 3.2, 6.2));
    for (const s of starPts) {
      const x = lerp((s.x + t * 12 * s.v) % 1920, s.tx, gather), y = lerp(s.y, s.ty, gather);
      sctx.fillStyle = s.funded ? `rgba(143,224,191,${.5 + .5 * gather})` : `rgba(255,255,255,${.35 + .4 * gather})`;
      sctx.beginPath(); sctx.arc(x, y, lerp(1.2, s.funded ? 4 : 2.6, gather), 0, 7); sctx.fill();
    }
    sctx.globalAlpha = 1;
  }

  // Chapter ticks & panel
  const ticks = $('#ticks'), chaptersPanel = $('#panel-chapters');
  chaptersPanel.innerHTML = '<h3>Chapters</h3>';
  CHAPTERS.forEach((c, i) => {
    const tick = el('i'); tick.style.left = (c.t / DURATION) * 100 + '%'; ticks.append(tick);
    const b = el('button', '', `${i < 10 ? (i + 1) % 10 + ' · ' : ''}${c.title}<span>${fmtTime(c.t)}</span>`);
    b.addEventListener('click', () => { player.seek(c.t, true); chaptersPanel.classList.remove('open'); });
    chaptersPanel.append(b); c.button = b;
  });

  // ---------- anchors (layout positions in stage coordinates) ----------
  function pos(node) {
    let x = 0, y = 0, e = node;
    while (e && e !== frame) { x += e.offsetLeft; y += e.offsetTop; e = e.offsetParent; }
    return { x, y, w: node.offsetWidth, h: node.offsetHeight, cx: x + node.offsetWidth / 2, cy: y + node.offsetHeight / 2 };
  }
  const A = {};
  function measure() {
    const box = pos($('#map-box')), k = box.w / MAP.width;
    const mp = (xy) => ({ x: box.x + xy[0] * k, y: box.y + xy[1] * k });
    const c = (sel) => { const p = pos($(sel)); return { x: p.cx, y: p.cy }; };
    Object.assign(A, {
      center: { x: 960, y: 540 },
      win: c('#win'), dock: c('#dock-gauge'), map: { x: box.cx, y: box.cy - 20 }, aster: mp(aster.xy),
      search: c('#search'), toggle: c('#seg-all'), toggleFunded: c('#seg-funded'), metrics: c('.metric-row'),
      navPrograms: c('#nav-programs'), panel: c('#detail'), ev: c('#d-evidence-sec'), unk: c('#d-unknown-sec'),
      prog: c('#d-programs-sec'), close: c('#detail-close'), notifs: c('#notifs'),
      pgLeft: c('#program-grid .green'), pgMid: c('#program-grid .amber'), pgRight: c('#program-grid .violet'),
      firstRow: () => c('#rows .row'),
    });
    // Segmented thumb geometry
    const f = $('#seg-funded'), a = $('#seg-all');
    A.segF = { left: f.offsetLeft, width: f.offsetWidth }; A.segA = { left: a.offsetLeft, width: a.offsetWidth };
  }

  // ---------- camera & cursor tracks ----------
  // Each key: [time, anchor or {x,y}, scale, blur?]. Values ease between keys.
  const CAM = () => [
    [0, 'center', 1], [10.8, 'center', 1.14], [12.8, 'center', 1], [14.6, 'center', 1],
    [16.4, 'win', 1.12], [18.4, 'map', 1.42], [25.6, 'map', 1.58],
    [27.4, 'win', 1.06], [31.2, 'win', 1.1],
    [33.2, 'search', 1.7], [35.8, 'search', 1.78], [38, 'aster', 3.1], [39.4, 'aster', 3.25],
    [40.8, 'win', 1.05], [42.4, 'panel', 1.32], [44, 'ev', 1.95], [46.6, 'ev', 2.05], [47.8, 'unk', 1.95], [49.6, 'prog', 1.72], [51.2, 'prog', 1.78],
    [52.8, 'win', 1.04], [54.4, 'win', 1.04], [55.6, 'pgLeft', 1.42], [57.6, 'pgMid', 1.46], [59.6, 'pgRight', 1.42], [60.6, 'win', 1],
    [70, 'win', 1], [71.6, 'notifs', 1.72], [75.2, 'notifs', 1.82], [76.6, 'center', 1], [DURATION, 'center', 1],
  ];
  const CURSOR = () => [
    // [time, anchor, visible]
    [12.2, { x: 1250, y: 720 }, 0], [12.6, { x: 1250, y: 720 }, 1], [13.8, 'dock', 1], [14.6, 'dock', 1], [15.8, { x: 1560, y: 860 }, 1],
    [27, { x: 1560, y: 860 }, 1], [28.4, 'toggle', 1], [32.4, 'toggle', 1], [33.4, 'search', 1], [39.2, 'search', 1],
    [40.6, 'firstRow', 1], [41.2, 'firstRow', 1], [51.8, { x: 1500, y: 700 }, 1], [52.4, 'close', 1], [52.9, 'close', 1],
    [53.8, 'navPrograms', 1], [54.6, 'navPrograms', 1], [55.4, { x: 1700, y: 900 }, 0],
  ];
  const CLICKS = [14.0, 28.6, 33.6, 41.0, 52.6, 54.0];
  let camKeys = [], curKeys = [];
  const resolve = (a) => (typeof a === 'string' ? (typeof A[a] === 'function' ? A[a]() : A[a]) : a);
  function buildTracks() {
    camKeys = CAM().map(([t, a, s, blur = 0]) => ({ t, ...resolve(a), s, blur }));
    curKeys = CURSOR().map(([t, a, v]) => ({ t, ...resolve(a), v }));
  }
  function sample(keys, t, fields, ease = E.inOut) {
    if (t <= keys[0].t) return keys[0];
    for (let i = 0; i < keys.length - 1; i++) {
      const a = keys[i], b = keys[i + 1];
      if (t <= b.t) { const p = ease(seg(t, a.t, b.t)); const out = {}; for (const f of fields) out[f] = lerp(a[f], b[f], p); return out; }
    }
    return keys[keys.length - 1];
  }

  // ---------- render(t) ----------
  const L = { titles: $('#layer-titles'), pipe: $('#layer-pipeline'), measured: $('#layer-measured'), finale: $('#layer-finale') };
  const win = $('#win'), menubar = $('#menubar'), dock = $('#dock'), dockGauge = $('#dock-gauge'), runDot = $('.run-dot');
  const cursor = $('#cursor'), ring = $('#click-ring');
  const views = { signals: $('#view-signals'), programs: $('#view-programs'), proof: $('#view-proof') };
  const navs = { signals: $('#nav-signals'), programs: $('#nav-programs'), proof: $('#nav-proof') };
  const counters = { showing: $('#count-showing'), muni: $('#count-muni'), match: $('#count-match') };
  const searchBox = $('#search'), searchText = $('#search-text'), placeholder = $('#search-placeholder');
  const backdrop = $('#detail-backdrop'), detail = $('#detail');
  const segThumb = $('#seg-thumb'), legendOther = $('#legend-other'), tip = $('#map-tip');
  const captionEl = $('#caption-text');
  const letterbox = [...document.querySelectorAll('.letterbox')];

  function setView(name, fade = 1) {
    for (const k in views) {
      const on = k === name;
      css(views[k], 'opacity', String(on ? fade : 0));
      css(views[k], 'transform', on ? `translateY(${(1 - fade) * 14}px) scale(${lerp(.985, 1, fade)})` : 'none');
      toggle(views[k], 'show', on && fade > .5);
      toggle(navs[k], 'active', on);
    }
  }
  function setSegment(p) {
    const l = lerp(A.segF.left, A.segA.left, p), w = lerp(A.segF.width, A.segA.width, p);
    css(segThumb, 'left', l + 'px'); css(segThumb, 'width', w + 'px');
  }
  function setMarkers(t, funded, others, focus) {
    // funded: [start, end] drop window; others: bloom window; focus: 0..1 dimming for search result
    for (const m of markers) {
      const [a, b] = m.company && m.funded ? funded : others;
      const start = lerp(a, b, m.seed * .85);
      const p = seg(t, start, start + .55);
      const drop = E.back(p);
      css(m.g, 'opacity', String(p > 0 ? Math.min(1, p * 2) * (focus > 0 && m.company !== aster ? lerp(1, .22, focus) : 1) : 0));
      css(m.g, 'transform', `translate(0px, ${(1 - drop) * -26}px)`);
      const rp = seg(t, start + .45, start + 1.3);
      attr(m.ripple, 'r', String(lerp(6, 26, E.out(rp))));
      attr(m.ripple, 'opacity', String(rp > 0 && rp < 1 ? (1 - rp) * .7 : 0));
    }
  }
  function countUp(el_, from, to, t, a, b) { text(el_, num(lerp(from, to, E.out(seg(t, a, b))))); }

  function render(t) {
    // --- story layers ---
    const titlesA = 1 - seg(t, 10.3, 11.3);
    css(L.titles, 'opacity', String(titlesA));
    drawStars(t, titlesA * (1 - seg(t, 6.4, 7.4) * .6));
    const o1out = seg(t, 2.9, 3.5);
    open1Chars.forEach((c, i) => {
      const p = E.out(seg(t, .5 + i * .035, 1.2 + i * .035));
      css(c, 'opacity', String(p * (1 - o1out)));
      css(c, 'transform', `translateY(${(1 - p) * 46 - o1out * 20}px) scale(${lerp(1.08, 1, p)})`);
      css(c, 'filter', `blur(${(1 - p) * 14 + o1out * 10}px)`);
    });
    const o2out = seg(t, 5.8, 6.4);
    open2Chars.forEach((c, i) => {
      const p = E.out(seg(t, 3.5 + i * .04, 4.2 + i * .04));
      css(c, 'opacity', String(p * (1 - o2out)));
      css(c, 'transform', `translateY(${(1 - p) * 46}px) scale(${lerp(1, 1.12, o2out)})`);
      css(c, 'filter', `blur(${(1 - p) * 14 + o2out * 16}px)`);
    });
    css(open1, 'transform', `scale(${lerp(1, 1.05, seg(t, .5, 3.5))})`);
    const brand = window_(t, 6.4, 10.9, .6, .7);
    const hero = $('#brand-hero');
    css(hero, 'opacity', String(brand));
    css(hero, 'transform', `scale(${lerp(1.16, 1, E.expo(seg(t, 6.4, 8.2))) * lerp(1, .94, seg(t, 10.2, 10.9))})`);
    css(hero, 'filter', `blur(${(1 - E.out(seg(t, 6.4, 7.6))) * 18}px)`);
    heroRails.forEach((r, i) => { const len = 560; r.style.strokeDasharray = len; css(r, 'strokeDashoffset', String(len * (1 - E.inOut(seg(t, 6.6 + i * .2, 7.8 + i * .2))))); });
    heroTies.forEach((ti, i) => { const p = E.back(seg(t, 7.2 + i * .06, 7.7 + i * .06)); css(ti, 'opacity', String(p)); css(ti, 'transform', `translateY(${(1 - p) * 20}px)`); });
    css(hero.querySelector('p'), 'opacity', String(E.out(seg(t, 8.2, 9))));
    css(hero.querySelector('.wordmark'), 'letterSpacing', `${lerp(.02, -.07, E.expo(seg(t, 6.6, 8.6)))}em`);

    // --- desktop ---
    const desk = seg(t, 10.3, 11.3);
    css(menubar, 'transform', `translateY(${(1 - E.out(seg(t, 11, 11.7))) * -40}px)`);
    css(dock, 'transform', `translate(-50%, ${(1 - E.back(seg(t, 11.4, 12.3))) * 150}px)`);
    const bounce = seg(t, 14, 14.9);
    css(dockGauge, 'transform', `translateY(${-Math.abs(Math.sin(bounce * Math.PI * 2)) * 28 * (1 - bounce)}px)`);
    css(runDot, 'opacity', t > 14.6 ? '1' : '0');

    // window open (genie-style from the dock) and stays open
    const wo = E.expo(seg(t, 14.6, 15.8));
    css(win, 'opacity', String(t < 14.6 ? 0 : Math.min(1, wo * 1.6)));
    css(win, 'transform', `translateY(${(1 - wo) * 90}px) scale(${lerp(.06, 1, wo)}, ${lerp(.02, 1, wo)})`);
    css(win, 'filter', `blur(${(1 - wo) * 10}px)`);

    // views
    if (t < 53.9 || t >= 60.5) setView('signals', 1);
    else setView('programs', E.out(seg(t, 54.05, 54.6)));
    if (t >= 60.5) setView('signals', 1);

    // map build
    const drawP = E.inOut(seg(t, 16.2, 18.4));
    css(gOutline, 'strokeDashoffset', String(outlineLen * (1 - drawP)));
    css(gFill, 'opacity', String(E.out(seg(t, 17.6, 18.8))));
    css(gShadow, 'opacity', String(E.out(seg(t, 18, 19))));
    css(gCounties, 'opacity', String(E.out(seg(t, 18.4, 19.4))));
    labels.forEach((lb) => css(lb, 'opacity', String(E.out(seg(t, 19, 20)))));
    const searchFocus = E.inOut(seg(t, 36.1, 36.8)) * (1 - seg(t, 52.8, 53.4));
    setMarkers(t, [19, 21], [28.8, 31], searchFocus);
    const showAll = t >= 28.6;
    setSegment(E.inOut(seg(t, 28.6, 29.1)));
    css(legendOther, 'opacity', String(E.out(seg(t, 28.8, 29.4))));
    setRows(showAll ? 'all' : 'funded');
    [...rowsEl.children].forEach((r, i) => {
      const p = E.out(seg(t, (showAll ? 29 : 20) + i * .12, (showAll ? 29.6 : 20.6) + i * .12));
      css(r, 'opacity', String(p)); css(r, 'transform', `translateX(${(1 - p) * 24}px)`);
      toggle(r, 'hot', r.dataset.id === 'aster' && t > 36.4 && t < 53);
    });
    // counters
    if (t < 28.6) {
      countUp(counters.showing, 0, 42, t, 19, 21.4); countUp(counters.muni, 0, 24, t, 19.6, 21.8); countUp(counters.match, 0, 16, t, 20, 22);
    } else {
      countUp(counters.showing, 42, 118, t, 28.8, 31); countUp(counters.muni, 24, 47, t, 28.9, 31.1); countUp(counters.match, 16, 29, t, 29, 31.2);
    }
    // search: focus, typing, result
    const typed = 'Princeton';
    const nChars = Math.floor(clamp((t - 34) / .16, 0, typed.length));
    text(searchText, typed.slice(0, t < 34 ? 0 : nChars));
    css(placeholder, 'display', t >= 34 && t < 53.4 ? 'none' : '');
    if (t >= 53.4) text(searchText, '');
    toggle(searchBox, 'focus', t >= 33.6 && t < 36.4);
    const pulseP = (t - 36.3) % 1.6 / 1.6;
    attr(pulse, 'r', String(t > 36.3 && t < 53 ? lerp(8, 30, E.out(pulseP)) : 0));
    attr(pulse, 'opacity', String(t > 36.3 && t < 53 ? (1 - pulseP) * .9 : 0));
    const tipA = window_(t, 37.2, 41.2, .4, .4);
    css(tip, 'opacity', String(tipA));
    if (tipA > 0) {
      const box = $('#map-box'), k = box.offsetWidth / MAP.width;
      css(tip, 'left', `${box.offsetLeft + aster.xy[0] * k}px`); css(tip, 'top', `${box.offsetTop + aster.xy[1] * k - 8}px`);
      tip.querySelector('strong').textContent = aster.name; tip.querySelector('small').textContent = `${aster.town} · ${aster.signal} · ${aster.raised}`;
    }

    // detail panel
    const dOpen = E.expo(seg(t, 41.2, 42.1)) * (1 - E.inOut(seg(t, 52.6, 53.3)));
    fillDetail(aster);
    css(backdrop, 'opacity', String(dOpen > 0 ? Math.min(1, dOpen * 1.5) : 0));
    css(detail, 'transform', `translateX(${(1 - dOpen) * 110}%)`);
    const secP = (a) => E.out(seg(t, a, a + .6));
    [...$('#d-evidence').children].forEach((e, i) => { const p = secP(43 + i * .7); css(e, 'opacity', String(p)); css(e, 'transform', `translateY(${(1 - p) * 16}px)`); const b = e.querySelector('b'); css(b, 'transform', `scale(${E.back(seg(t, 43.3 + i * .7, 43.8 + i * .7))})`); });
    [...$('#d-unknowns').children].forEach((e, i) => { const p = secP(46.4 + i * .5); css(e, 'opacity', String(p)); css(e, 'transform', `translateX(${(1 - p) * -16}px)`); });
    [...$('#d-programs').children].forEach((e, i) => { const p = E.back(seg(t, 48.4 + i * .6, 49 + i * .6)); css(e, 'opacity', String(clamp(p))); css(e, 'transform', `perspective(800px) rotateX(${(1 - p) * -40}deg)`); });
    // depth of field: soften the rest of the window while zoomed on the panel
    const dof = window_(t, 43.6, 51.6, .8, .8);
    css($('.sidebar'), 'filter', `blur(${dof * 6}px)`); css(views.signals.querySelector('.signal-grid'), 'filter', `blur(${dof * 5}px)`);

    // programs view
    [...$('#program-grid').children].forEach((card, i) => {
      const p = E.back(seg(t, 54.4 + i * .25, 55.3 + i * .25));
      css(card, 'opacity', String(clamp(p * 1.4)));
      css(card, 'transform', `perspective(1400px) rotateX(${(1 - p) * 34}deg) translateY(${(1 - p) * 60}px)`);
      const s = card.querySelector('strong'); countUp(s, 0, +s.dataset.count, t, 55 + i * .25, 56.6 + i * .25);
    });
    const sem = E.out(seg(t, 56.4, 57.2)); css($('#semantics'), 'opacity', String(sem)); css($('#semantics'), 'transform', `translateY(${(1 - sem) * 24}px)`);

    // pipeline layer
    const pipeA = window_(t, 60.5, 70.3, .7, .8);
    css(L.pipe, 'opacity', String(pipeA));
    css($('.pipe-head'), 'transform', `translateY(${(1 - E.out(seg(t, 60.6, 61.6))) * 30}px)`);
    const nodeTimes = { s1: 61.2, s2: 61.45, s3: 61.7, n1: 62.8, n2: 64, n3: 65.2, n4: 66.4 };
    for (const id in nodeEls) {
      const e = nodeEls[id], a = nodeTimes[id], p = E.back(seg(t, a, a + .7));
      css(e, 'opacity', String(clamp(p))); css(e, 'transform', `translateY(${(1 - p) * 30}px) scale(${lerp(.9, 1, clamp(p))})`);
      const b = e.querySelector('b[data-n]'); if (b) countUp(b, 0, +b.dataset.n, t, a + .3, a + 1.8);
      toggle(e, 'lit', t > a + .5);
    }
    const pathTimes = [62.2, 62.35, 62.5, 63.6, 64.8, 66];
    pipePaths.forEach((pp, i) => {
      const dp = E.inOut(seg(t, pathTimes[i], pathTimes[i] + .9));
      css(pp.p, 'strokeDashoffset', String(pp.len * (1 - dp)));
      pp.dots.forEach((d, j) => {
        const on = dp >= 1 && pipeA > 0;
        const f = ((t * .45 + j / 3 + i * .17) % 1);
        if (on) { const pt = pp.p.getPointAtLength(f * pp.len); attr(d, 'cx', pt.x.toFixed(1)); attr(d, 'cy', pt.y.toFixed(1)); }
        attr(d, 'opacity', on ? String(Math.sin(f * Math.PI)) : '0');
      });
    });

    // notifications
    notifEls.forEach((n, i) => {
      const a = 70.8 + i * 1.1;
      const p = E.back(seg(t, a, a + .7)) * (1 - E.inOut(seg(t, 76.2, 76.8)));
      css(n, 'opacity', String(clamp(p * 1.3)));
      css(n, 'transform', `translateY(${(1 - p) * -40}px) scale(${lerp(.94, 1, clamp(p))})`);
    });

    // measured + finale
    const mA = window_(t, 76.5, 84.3, .8, .8);
    css(L.measured, 'opacity', String(mA));
    const mh = E.out(seg(t, 76.8, 78)); css(L.measured.querySelector('h1'), 'transform', `translateY(${(1 - mh) * 40}px)`); css(L.measured.querySelector('h1'), 'filter', `blur(${(1 - mh) * 12}px)`);
    [...$('#m-tiles').children].forEach((d, i) => { const p = E.back(seg(t, 78.4 + i * .35, 79.1 + i * .35)); css(d, 'opacity', String(clamp(p))); css(d, 'transform', `translateY(${(1 - p) * 40}px)`); });
    const fA = seg(t, 83.8, 84.8) * (1 - seg(t, 91.2, DURATION));
    css(L.finale, 'opacity', String(fA));
    finalRails.forEach((r, i) => { const len = 1960; r.style.strokeDasharray = len; css(r, 'strokeDashoffset', String(len * (1 - E.inOut(seg(t, 84.3 + i * .15, 86 + i * .15))))); });
    const slide = (t - 84) * 90;
    finalTies.forEach((ti, i) => { const p = seg(t, 84.8 + i * .02, 85.4 + i * .02); css(ti, 'opacity', String(p)); css(ti, 'transform', `translateX(${-(slide % 51.3)}px)`); });
    const fw = L.finale.querySelector('.wordmark'), tg = L.finale.querySelector('.tagline');
    const wp = E.expo(seg(t, 85.6, 87.4));
    css(fw, 'opacity', String(wp)); css(fw, 'filter', `blur(${(1 - wp) * 20}px)`); css(fw, 'transform', `scale(${lerp(1.12, 1, wp)})`);
    css(tg, 'opacity', String(E.out(seg(t, 87.2, 88.2))));
    css(L.finale.querySelector('.gauge-mm'), 'opacity', String(E.out(seg(t, 88.2, 89))));
    css(L.finale.querySelector('.fine'), 'opacity', String(E.out(seg(t, 89, 89.8)) * .9));
    const lb = E.inOut(seg(t, 84, 85.4)) * (1 - seg(t, 91.2, DURATION));
    letterbox.forEach((b) => css(b, 'height', `${lb * 90}px`));

    // camera
    const cam = sample(camKeys, t, ['x', 'y', 's', 'blur']);
    const drift = REDUCED ? 0 : Math.sin(t * .35) * 4;   // subtle handheld float
    css(camera, 'transform', `translate(${960 - cam.x * cam.s + drift}px, ${540 - cam.y * cam.s + drift * .6}px) scale(${cam.s})`);
    css(camera, 'filter', `brightness(${lerp(.4, 1, desk)})`);

    // cursor
    const cur = sample(curKeys, t, ['x', 'y', 'v'], E.inOut);
    css(cursor, 'opacity', String(t < 12.2 || t > 56 ? 0 : cur.v));
    const press = CLICKS.some((c) => t >= c && t < c + .14);
    css(cursor, 'transform', `translate(${cur.x - 6}px, ${cur.y - 4}px) scale(${press ? .86 : 1})`);
    const lastClick = CLICKS.filter((c) => t >= c).pop();
    const rp = lastClick != null ? seg(t, lastClick, lastClick + .5) : 1;
    css(ring, 'opacity', String(rp < 1 ? 1 - rp : 0)); css(ring, 'transform', `scale(${lerp(.3, 1.4, E.out(rp))})`);

    // captions
    const cap = CAPTIONS.find(([a, b]) => t >= a && t < b);
    if (cap) text(captionEl, cap[2]);
    toggle(captionEl, 'show', !!cap);
  }

  // ---------- explore mode ----------
  const explore = {
    on: false,
    enter() {
      this.on = true; player.pause(); app.classList.add('explore');
      css(camera, 'transform', 'translate(0px, 0px) scale(1)'); css(camera, 'filter', 'none');
      for (const k in L) css(L[k], 'opacity', '0');
      letterbox.forEach((b) => css(b, 'height', '0px'));
      css(win, 'opacity', '1'); css(win, 'transform', 'none'); css(win, 'filter', 'none');
      css(menubar, 'transform', 'none'); css(dock, 'transform', 'translate(-50%, 0)');
      notifEls.forEach((n) => { css(n, 'opacity', '0'); });
      css($('.sidebar'), 'filter', 'none'); css(views.signals.querySelector('.signal-grid'), 'filter', 'none');
      toggle(captionEl, 'show', false);
      this.showAll(true); this.view('signals'); this.closeDetail();
      [gOutline].forEach((p) => css(p, 'strokeDashoffset', '0'));
      [gFill, gShadow, gCounties, ...labels].forEach((p) => css(p, 'opacity', '1'));
      $('#search-input').focus();
    },
    exit() { this.on = false; app.classList.remove('explore'); $('.search-empty')?.remove(); render(player.t); },
    view(name) { setView(name, 1); for (const k in views) toggle(views[k], 'show', k === name); },
    showAll(all) {
      setSegment(all ? 1 : 0); setRows(all ? 'all' : 'funded');
      [...rowsEl.children].forEach((r) => { css(r, 'opacity', '1'); css(r, 'transform', 'none'); toggle(r, 'hot', false); });
      for (const m of markers) { const vis = all || (m.company && m.funded); css(m.g, 'opacity', vis ? '1' : '0'); css(m.g, 'transform', 'none'); attr(m.ripple, 'opacity', '0'); }
      text(counters.showing, all ? '118' : '42'); text(counters.muni, all ? '47' : '24'); text(counters.match, all ? '29' : '16');
      css(legendOther, 'opacity', all ? '1' : '0'); this.all = all;
    },
    openCompany(c) {
      if (!this.on) return;
      detailFor = null; fillDetail(c);
      css(backdrop, 'opacity', '1'); css(detail, 'transform', 'none');
      detail.querySelectorAll('.ev, .unk, .match, .ev b').forEach((e) => { css(e, 'opacity', '1'); css(e, 'transform', 'none'); });
      attr(pulse, 'cx', c.xy[0]); attr(pulse, 'cy', c.xy[1]); attr(pulse, 'r', '18'); attr(pulse, 'opacity', '.9');
    },
    closeDetail() { css(backdrop, 'opacity', '0'); css(detail, 'transform', 'translateX(110%)'); attr(pulse, 'opacity', '0'); attr(pulse, 'cx', aster.xy[0]); attr(pulse, 'cy', aster.xy[1]); },
    search(q) {
      $('.search-empty')?.remove();
      const hit = companies.find((c) => c.town.toLowerCase() === q.trim().toLowerCase());
      if (hit) { if (!this.all && !hit.funded) this.showAll(true); this.openCompany(hit); return; }
      if (q.trim()) searchBox.append(el('div', 'search-empty', `<strong>No federal signal in ${q.trim()}</strong>That does not mean there are no startups there. Public records have real coverage limits.`));
    },
  };
  Object.entries(navs).forEach(([k, b]) => b.addEventListener('click', () => explore.on && explore.view(k)));
  $('#seg-all').addEventListener('click', () => explore.on && explore.showAll(true));
  $('#seg-funded').addEventListener('click', () => explore.on && explore.showAll(false));
  $('#detail-close').addEventListener('click', () => explore.on && explore.closeDetail());
  backdrop.addEventListener('click', (e) => explore.on && e.target === backdrop && explore.closeDetail());
  $('#search-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') explore.search(e.target.value); e.stopPropagation(); });

  // ---------- player ----------
  const player = {
    t: 0, playing: true, speed: 1, loop: true, last: 0,
    play() { if (explore.on) explore.exit(); if (this.t >= DURATION) this.t = 0; this.playing = true; this.last = performance.now(); app.classList.add('playing'); if (sound.on) sound.set(true); ui(); },
    pause() { this.playing = false; app.classList.remove('playing'); if (sound.ctx) sound.master.gain.setTargetAtTime(0, sound.ctx.currentTime, .2); ui(); },
    toggle() { this.playing ? this.pause() : this.play(); },
    seek(t, announce = false) {
      if (explore.on) explore.exit();
      this.t = clamp(t, 0, DURATION); render(this.t); ui();
      if (announce) toast(chapterAt(this.t).title);
    },
  };
  const chapterAt = (t) => [...CHAPTERS].reverse().find((c) => t >= c.t) || CHAPTERS[0];
  let toastTimer;
  function toast(msg) { const tEl = $('#chapter-toast'); tEl.textContent = msg; tEl.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => tEl.classList.remove('show'), 1300); }
  let lastChapter = null;
  function ui() {
    const p = player.t / DURATION;
    $('#progress').style.width = p * 100 + '%'; $('#knob').style.left = p * 100 + '%';
    $('#time').textContent = `${fmtTime(player.t)} / ${fmtTime(DURATION)}`;
    $('#btn-play').textContent = player.playing ? '❚❚' : '▶';
    const ch = chapterAt(player.t);
    if (ch !== lastChapter) {
      lastChapter = ch; $('#notes-text').textContent = ch.note;
      CHAPTERS.forEach((c) => c.button.classList.toggle('current', c === ch));
      if (!location.hash.startsWith('#t=')) history.replaceState(null, '', '#' + ch.id);
    }
  }
  function tick(now) {
    if (player.playing) {
      const dt = Math.min(.1, (now - player.last) / 1000) * player.speed;
      const prev = player.t;
      player.last = now; player.t += dt;
      soundEvents(prev, player.t);
      if (player.t >= DURATION) {
        if (player.loop) { player.t = 0; } else { player.t = DURATION; player.pause(); }
      }
      render(player.t); ui();
    } else player.last = now;
    requestAnimationFrame(tick);
  }

  // controls
  const speeds = [.5, 1, 1.5, 2];
  $('#btn-play').onclick = () => player.toggle();
  $('#btn-restart').onclick = () => { player.seek(0); player.play(); };
  $('#btn-speed').onclick = () => { player.speed = speeds[(speeds.indexOf(player.speed) + 1) % speeds.length]; $('#btn-speed').textContent = player.speed + '×'; };
  $('#btn-cc').onclick = () => { app.classList.toggle('no-cc'); $('#btn-cc').classList.toggle('on', !app.classList.contains('no-cc')); };
  $('#btn-loop').onclick = () => { player.loop = !player.loop; $('#btn-loop').classList.toggle('on', player.loop); };
  $('#btn-explore').onclick = () => { explore.on ? (explore.exit(), $('#btn-explore').classList.remove('on')) : (explore.enter(), $('#btn-explore').classList.add('on')); };
  $('#btn-full').onclick = () => (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.());
  const panels = { chapters: '#panel-chapters', notes: '#panel-notes', help: '#panel-help' };
  const openPanel = (name) => Object.entries(panels).forEach(([k, sel]) => $(sel).classList.toggle('open', k === name && !$(sel).classList.contains('open')));
  $('#btn-chapters').onclick = () => openPanel('chapters');
  $('#btn-notes').onclick = () => { openPanel('notes'); $('#btn-notes').classList.toggle('on', $('#panel-notes').classList.contains('open')); };
  $('#btn-help').onclick = () => openPanel('help');


  // ---------- sound (optional, generated with WebAudio; no files) ----------
  const sound = {
    on: false, ctx: null, pad: null, noise: null,
    init() {
      const ctx = (this.ctx = new (window.AudioContext || window.webkitAudioContext)());
      this.master = ctx.createGain(); this.master.gain.value = 0; this.master.connect(ctx.destination);
      // ambient pad: three detuned voices through a slow low-pass
      this.filter = ctx.createBiquadFilter(); this.filter.type = 'lowpass'; this.filter.frequency.value = 900; this.filter.connect(this.master);
      this.voices = [0, 1, 2].map((i) => {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.type = i === 1 ? 'triangle' : 'sine'; o.detune.value = (i - 1) * 6; g.gain.value = .06;
        o.connect(g).connect(this.filter); o.start(); return o;
      });
      const len = ctx.sampleRate; const buf = ctx.createBuffer(1, len, ctx.sampleRate); const d = buf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
      this.noise = buf;
    },
    chord(t) { // a slow progression that follows the chapters
      const roots = [220, 196, 174.6, 196, 220, 246.9, 220, 196, 164.8, 174.6, 196, 220];
      const idx = CHAPTERS.indexOf(chapterAt(t));
      const r = roots[idx] || 220, ratios = [1, 1.25, 1.5];
      this.voices.forEach((o, i) => o.frequency.setTargetAtTime(r * ratios[i] / 2, this.ctx.currentTime, .8));
      this.filter.frequency.setTargetAtTime(600 + 500 * Math.sin(t / 9) ** 2, this.ctx.currentTime, 1.5);
    },
    burst(kind) {
      const ctx = this.ctx, src = ctx.createBufferSource(), g = ctx.createGain(), f = ctx.createBiquadFilter(), now = ctx.currentTime;
      src.buffer = this.noise; src.connect(f).connect(g).connect(ctx.destination);
      if (kind === 'click') { f.type = 'highpass'; f.frequency.value = 2500; g.gain.setValueAtTime(.35, now); g.gain.exponentialRampToValueAtTime(.001, now + .05); src.start(now, Math.random(), .06); }
      else if (kind === 'key') { f.type = 'bandpass'; f.frequency.value = 3500; g.gain.setValueAtTime(.12, now); g.gain.exponentialRampToValueAtTime(.001, now + .03); src.start(now, Math.random(), .04); }
      else { f.type = 'bandpass'; f.Q.value = .7; f.frequency.setValueAtTime(300, now); f.frequency.exponentialRampToValueAtTime(2400, now + .6); g.gain.setValueAtTime(.001, now); g.gain.exponentialRampToValueAtTime(.12, now + .25); g.gain.exponentialRampToValueAtTime(.001, now + .75); src.start(now, Math.random(), .8); }
    },
    set(on) {
      this.on = on; if (on && !this.ctx) this.init();
      if (this.ctx) { this.ctx.resume(); this.master.gain.setTargetAtTime(on && player.playing ? .5 : 0, this.ctx.currentTime, .3); }
      $('#btn-sound').classList.toggle('on', on);
    },
  };
  const KEY_TIMES = Array.from({ length: 9 }, (_, i) => 34 + i * .16);
  const WHOOSH = [6.4, 14.6, 28.6, 36.2, 41.2, 54.1, 60.5, 70.8, 76.5, 84.2];
  function soundEvents(prev, t) {
    if (!sound.on || !sound.ctx || t < prev || t - prev > .5) return;
    const crossed = (list) => list.some((x) => x > prev && x <= t);
    if (crossed(CLICKS)) sound.burst('click');
    if (crossed(KEY_TIMES)) sound.burst('key');
    if (crossed(WHOOSH)) sound.burst('whoosh');
    sound.chord(t);
  }
  $('#btn-sound').onclick = () => sound.set(!sound.on);

  // share a link to this moment
  $('#btn-share').onclick = async () => {
    const url = `${location.origin}${location.pathname}#t=${player.t.toFixed(1)}`;
    try { await navigator.clipboard.writeText(url); toast('Link to this moment copied'); } catch { toast(url); }
  };
  $('#btn-aspect').onclick = () => setAspect((aspect + 1) % ASPECTS.length);

  // pause when the tab is hidden, resume when it returns
  let hiddenPaused = false;
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && player.playing) { hiddenPaused = true; player.pause(); }
    else if (!document.hidden && hiddenPaused) { hiddenPaused = false; player.play(); }
  });

  // scrubber
  const scrub = $('#scrubber');
  const tAt = (e) => { const r = scrub.getBoundingClientRect(); return clamp((e.clientX - r.left) / r.width) * DURATION; };
  let dragging = false, wasPlaying = false;
  scrub.addEventListener('pointerdown', (e) => { dragging = true; wasPlaying = player.playing; player.pause(); scrub.setPointerCapture(e.pointerId); player.seek(tAt(e)); });
  scrub.addEventListener('pointermove', (e) => {
    const t = tAt(e), tipEl = $('#hover-tip'), r = scrub.getBoundingClientRect();
    tipEl.textContent = `${fmtTime(t)} · ${chapterAt(t).title}`; tipEl.style.left = (e.clientX - r.left) + 'px';
    if (dragging) player.seek(t);
  });
  scrub.addEventListener('pointerup', () => { dragging = false; if (wasPlaying) player.play(); });

  // keyboard
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    const k = e.key;
    const idx = CHAPTERS.indexOf(chapterAt(player.t));
    if (k === ' ') { e.preventDefault(); player.toggle(); }
    else if (k === 'ArrowRight') player.seek(player.t + 5);
    else if (k === 'ArrowLeft') player.seek(player.t - 5);
    else if (k === ']') player.seek(CHAPTERS[Math.min(CHAPTERS.length - 1, idx + 1)].t, true);
    else if (k === '[') player.seek(CHAPTERS[Math.max(0, player.t - CHAPTERS[idx].t > 1.5 ? idx : idx - 1)].t, true);
    else if (/^[0-9]$/.test(k)) { const c = CHAPTERS[k === '0' ? 9 : +k - 1]; if (c) player.seek(c.t, true); }
    else if (k === 's' || k === 'S') $('#btn-speed').click();
    else if (k === 'k' || k === 'K') $('#btn-cc').click();
    else if (k === 'e' || k === 'E') $('#btn-explore').click();
    else if (k === 'l' || k === 'L') $('#btn-loop').click();
    else if (k === 'a' || k === 'A') $('#btn-aspect').click();
    else if (k === 'm' || k === 'M') $('#btn-sound').click();
    else if (k === 'u' || k === 'U') $('#btn-share').click();
    else if (k === 'n' || k === 'N') $('#btn-notes').click();
    else if (k === 'c' || k === 'C') $('#btn-chapters').click();
    else if (k === 'h' || k === 'H') app.classList.toggle('clean');
    else if (k === 'f' || k === 'F') $('#btn-full').click();
    else if (k === 'r' || k === 'R') $('#btn-restart').click();
    else if (k === '?') $('#btn-help').click();
    else if (k === 'Escape') { openPanel(null); if (explore.on) $('#btn-explore').click(); }
  });

  // fit the 1920×1080 stage into the viewport
  const ASPECTS = [['16:9', 1920], ['1:1', 1080], ['9:16', 608]];
  let aspect = 0;
  function fit() {
    const cw = ASPECTS[aspect][1];
    stage.style.setProperty('--clip-w', cw + 'px');
    app.style.setProperty('--layer-k', String(cw / 1920));
    app.classList.toggle('cut', aspect > 0);
    const w = viewport.clientWidth, h = viewport.clientHeight, s = Math.min(w / cw, h / 1080);
    stage.style.transform = `scale(${s})`;
    stage.style.left = (w - cw * s) / 2 + 'px'; stage.style.top = (h - 1080 * s) / 2 + 'px';
  }
  function setAspect(i) { aspect = i; $('#btn-aspect').textContent = ASPECTS[i][0]; fit(); toast(`${ASPECTS[i][0]} cut`); }
  window.addEventListener('resize', fit);
  new ResizeObserver(fit).observe(viewport);

  // deep links: #t=42 or #search
  function fromHash() {
    const h = location.hash.slice(1);
    if (h.startsWith('t=')) return clamp(parseFloat(h.slice(2)) || 0, 0, DURATION);
    const c = CHAPTERS.find((ch) => ch.id === h); return c ? c.t : 0;
  }
  window.addEventListener('hashchange', () => player.seek(fromHash()));
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) player.speed = 1;

  async function start() {
    fit();
    try { await document.fonts.ready; } catch { /* fonts are optional */ }
    measure();
    buildTracks();
    player.t = fromHash();
    const q = new URLSearchParams(location.search);
    if (q.has('paused')) player.pause();
    const cut = ASPECTS.findIndex(([name]) => name === q.get('cut'));
    if (cut > 0) setAspect(cut);
    if (q.has('clean')) app.classList.add('clean');
    render(player.t); ui();
    player.last = performance.now();
    requestAnimationFrame(tick);
    window.GaugeFilm = { player, render, seek: (t) => player.seek(t), chapters: CHAPTERS, duration: DURATION };
  }
  start();
})();

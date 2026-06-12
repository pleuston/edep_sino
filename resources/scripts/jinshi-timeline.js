/* EpiWen — jinshi history timeline (年表)
   Vanilla SVG, no dependencies. Pattern: sites-map.js
   Entry points: chronology page, person/work mini-timelines, attestation strip. */
(function () {
'use strict';

// ── SVG helpers ──────────────────────────────────────────────────────────────

function svgEl(tag, attrs) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    if (attrs) Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, String(v)));
    return el;
}

function svgTitle(text) {
    const t = svgEl('title'); t.textContent = text; return t;
}

function esc(s) {
    return String(s || '').replace(/[&<>"']/g, c =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function yearToX(year, minY, maxY, w) {
    if (maxY === minY) return w / 2;
    return Math.round((year - minY) / (maxY - minY) * w);
}

// Lane-packing: assign each item the lowest lane whose last item ends before this one starts.
function packLanes(items) {
    const ends = [];
    return items.map(item => {
        let lane = ends.findIndex(end => end < item.from - 1);
        if (lane === -1) lane = ends.length;
        ends[lane] = item.to;
        return { ...item, lane };
    });
}

// Floruit hatch pattern definition
function flouritHatchDef(id) {
    const pat = svgEl('pattern', { id, patternUnits: 'userSpaceOnUse',
        width: 6, height: 6, patternTransform: 'rotate(45)' });
    const ln = svgEl('line', { x1: 0, y1: 0, x2: 0, y2: 6, stroke: '#aaa', 'stroke-width': 2 });
    pat.appendChild(ln);
    return pat;
}

// ── Full chronology page ─────────────────────────────────────────────────────

function initChronologyPage() {
    const page = document.querySelector('.chronology-page');
    if (!page) return;

    const app  = page.dataset.app || '';
    const cont = document.getElementById('timeline-main');
    if (!cont) return;

    const showPersons = () => document.getElementById('toggle-persons')?.checked !== false;
    const showWorks   = () => document.getElementById('toggle-works')?.checked !== false;

    function load(params) {
        const url = app + '/api/sino/chronology' + (params ? '?' + params : '');
        cont.innerHTML = '';
        const loading = document.createElement('div');
        loading.className = 'timeline-loading';
        loading.textContent = '…';
        cont.appendChild(loading);
        fetch(url)
            .then(r => r.json())
            .then(data => {
                cont.innerHTML = '';
                buildDynastyButtons(page, data.dynasties || [], load);
                drawFullTimeline(cont, data, app, showPersons(), showWorks());
            })
            .catch(() => {
                cont.innerHTML = '<p class="timeline-error">Timeline data unavailable.</p>';
            });
    }

    document.getElementById('toggle-persons')?.addEventListener('change', () => {
        cont.querySelectorAll('.lane-persons').forEach(el =>
            el.setAttribute('display', showPersons() ? '' : 'none'));
    });
    document.getElementById('toggle-works')?.addEventListener('change', () => {
        cont.querySelectorAll('.lane-works').forEach(el =>
            el.setAttribute('display', showWorks() ? '' : 'none'));
    });

    load('');
}

function buildDynastyButtons(page, dynasties, loadFn) {
    const bar = page.querySelector('.dynasty-buttons');
    if (!bar || bar.childElementCount) return; // build only once

    function makeBtn(label, params, title) {
        const b = document.createElement('button');
        b.className = 'dynasty-btn';
        b.textContent = label;
        if (title) b.title = title;
        b.addEventListener('click', () => {
            bar.querySelectorAll('.dynasty-btn').forEach(x => x.classList.remove('active'));
            b.classList.add('active');
            loadFn(params);
        });
        return b;
    }

    const all = makeBtn('全部', '');
    all.classList.add('active');
    bar.appendChild(all);

    // Jinshi studies record inscriptions from the Han onwards, but the
    // catalogues themselves start around the Song; offer buttons from Tang.
    const shown = dynasties.filter(d => d.to >= 900);
    shown.forEach(d => {
        bar.appendChild(makeBtn(d.label, `dynasty=${encodeURIComponent(d.key)}`, `${d.from}–${d.to}`));
    });
}

function drawFullTimeline(container, data, app, showPersons, showWorks) {
    const dynasties = data.dynasties || [];
    const persons   = data.persons   || [];
    const works     = data.works     || [];

    if (!persons.length && !works.length) {
        container.innerHTML = '<p class="timeline-empty">No datable entries in this range.</p>';
        return;
    }

    const allYears = [
        ...persons.flatMap(p => [p.from, p.to]),
        ...works.map(w => w.when),
        ...dynasties.flatMap(d => [d.from, d.to])
    ].filter(Number.isFinite);
    const minY = Math.min(...allYears) - 10;
    const maxY = Math.max(...allYears) + 10;

    const W        = Math.max(container.offsetWidth || 900, 600);
    const AXIS_H   = 28;
    const BAND_H   = 18;
    const ROW_H    = 16;
    const PAD      = 2;
    const WORK_SEP = 12;

    const packed    = packLanes(persons.map(p => ({ ...p })));
    const nLanes    = packed.length ? Math.max(...packed.map(p => p.lane)) + 1 : 0;
    const WORKS_TOP = AXIS_H + BAND_H + nLanes * (ROW_H + PAD) + WORK_SEP;
    const H         = WORKS_TOP + ROW_H + 30;

    const svg  = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, class: 'timeline-svg' });
    const defs = svgEl('defs');
    defs.appendChild(flouritHatchDef('fh-full'));
    svg.appendChild(defs);

    // Dynasty background bands
    const BAND_COLS = ['#f5f3ee', '#ede9e0'];
    dynasties.forEach((d, i) => {
        const x1 = yearToX(d.from, minY, maxY, W);
        const x2 = yearToX(d.to,   minY, maxY, W);
        if (x2 <= x1) return;
        const g = svgEl('g', { class: 'dynasty-band' });
        g.appendChild(svgEl('rect', { x: x1, y: 0, width: x2 - x1, height: H,
            fill: BAND_COLS[i % 2], opacity: 0.7 }));
        // label only bands wide enough to carry their name; keep the label
        // below the axis so it never collides with the year ticks above it
        if (x2 - x1 >= 30) {
            const lx = x1 + Math.min((x2 - x1) / 2, 50);
            const lbl = svgEl('text', { x: lx, y: AXIS_H + 13, 'text-anchor': 'middle',
                'font-size': 10, fill: '#8a7f70', class: 'dynasty-label zh' });
            lbl.textContent = d.label;
            g.appendChild(lbl);
        }
        svg.appendChild(g);
    });

    // Axis line
    svg.appendChild(svgEl('line', { x1: 0, y1: AXIS_H, x2: W, y2: AXIS_H,
        stroke: '#bbb', 'stroke-width': 1 }));

    // Year ticks
    const span = maxY - minY;
    const step = span > 600 ? 100 : span > 200 ? 50 : 25;
    const first = Math.ceil(minY / step) * step;
    for (let y = first; y <= maxY; y += step) {
        const tx = yearToX(y, minY, maxY, W);
        svg.appendChild(svgEl('line', { x1: tx, y1: AXIS_H - 4, x2: tx, y2: AXIS_H + 4,
            stroke: '#999', 'stroke-width': 1 }));
        const tl = svgEl('text', { x: tx, y: AXIS_H - 6, 'text-anchor': 'middle',
            'font-size': 9, fill: '#555' });
        tl.textContent = y;
        svg.appendChild(tl);
    }

    // Person bars
    const personsG = svgEl('g', { class: 'lane-persons',
        display: showPersons === false ? 'none' : '' });
    packed.forEach(p => {
        const x1 = yearToX(p.from, minY, maxY, W);
        const x2 = yearToX(p.to,   minY, maxY, W);
        const y  = AXIS_H + BAND_H + p.lane * (ROW_H + PAD);
        const bw = Math.max(x2 - x1, 3);
        const fl = p.precision === 'floruit';

        const g = svgEl('g', { class: 'person-bar', 'data-id': p.id,
            tabindex: 0, role: 'link', 'aria-label': p.label });
        g.appendChild(svgTitle(`${p.label} (${p.birth || p.from}–${p.death || p.to})`));
        g.appendChild(svgEl('rect', { x: x1, y, width: bw, height: ROW_H - 2, rx: 2,
            fill: fl ? 'url(#fh-full)' : 'var(--jinks-colors-500, #6a5a4a)',
            stroke: fl ? '#888' : 'none', opacity: fl ? 0.75 : 0.9,
            class: fl ? 'person-floruit' : 'person-lifespan' }));

        if (bw > 36) {
            const lbl = svgEl('text', { x: x1 + 3, y: y + ROW_H - 5,
                'font-size': 9, fill: fl ? '#444' : '#fff', class: 'zh' });
            lbl.textContent = p.label.slice(0, 4);
            g.appendChild(lbl);
        }

        // Transparent wider hit area
        const hit = svgEl('rect', { x: x1, y, width: Math.max(bw, 10), height: ROW_H - 2,
            fill: 'transparent', cursor: 'pointer', class: 'hit-area' });
        hit.addEventListener('click', () => { location.href = `${app}/people/${p.id}`; });
        hit.addEventListener('keydown', e => {
            if (e.key === 'Enter') location.href = `${app}/people/${p.id}`;
        });
        g.appendChild(hit);
        personsG.appendChild(g);
    });
    svg.appendChild(personsG);

    // Work markers (diamonds)
    const worksG = svgEl('g', { class: 'lane-works',
        display: showWorks === false ? 'none' : '' });
    const wy = WORKS_TOP;
    const D  = 7;
    works.forEach(w => {
        const wx = yearToX(w.when, minY, maxY, W);
        const g  = svgEl('g', { class: 'work-marker', 'data-id': w.id,
            tabindex: 0, role: 'link', 'aria-label': w.label });
        g.appendChild(svgTitle(`${w.label} (${w['date-label'] || w.when})`));
        g.appendChild(svgEl('polygon', {
            points: `${wx},${wy - D} ${wx + D},${wy} ${wx},${wy + D} ${wx - D},${wy}`,
            fill: w.precision === 'approx'
                ? 'var(--jinks-colors-400, #8a7a6a)'
                : 'var(--jinks-colors-700, #3a2a1a)',
            opacity: 0.85
        }));
        const hit = svgEl('polygon', {
            points: `${wx},${wy - D - 5} ${wx + D + 5},${wy} ${wx},${wy + D + 5} ${wx - D - 5},${wy}`,
            fill: 'transparent', cursor: 'pointer'
        });
        hit.addEventListener('click', () => { location.href = `${app}/works/${w.id}`; });
        hit.addEventListener('keydown', e => {
            if (e.key === 'Enter') location.href = `${app}/works/${w.id}`;
        });
        g.appendChild(hit);
        worksG.appendChild(g);
    });
    svg.appendChild(worksG);

    container.appendChild(svg);
}

// ── Person page mini-timeline ────────────────────────────────────────────────

function initPersonMini() {
    const el = document.querySelector('.mini-timeline[data-entity-type="person"]');
    if (!el) return;
    const app = el.dataset.app || '';
    const id  = el.dataset.entityId;

    fetch(app + '/api/sino/chronology?type=both')
        .then(r => r.json())
        .then(data => {
            const p = (data.persons || []).find(x => x.id === id);
            if (!p) { el.hidden = true; return; }
            const myWorks = (data.works || []).filter(w => w['author-id'] === id);
            drawPersonMini(el, p, myWorks, app);
        })
        .catch(() => { el.hidden = true; });
}

function drawPersonMini(container, p, works, app) {
    const W   = Math.max(container.offsetWidth || 500, 240);
    const H   = 64;
    const PL  = 24;
    const PR  = 24;
    const uw  = W - PL - PR;
    const allY = [p.from, p.to, ...works.map(w => w.when)];
    const minY = Math.min(...allY) - 5;
    const maxY = Math.max(...allY) + 5;

    const svg  = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, class: 'mini-timeline-svg' });
    const defs = svgEl('defs'); defs.appendChild(flouritHatchDef('fh-mini')); svg.appendChild(defs);

    const fl   = p.precision === 'floruit';
    const x1   = yearToX(p.from, minY, maxY, uw) + PL;
    const x2   = yearToX(p.to,   minY, maxY, uw) + PL;
    const bw   = Math.max(x2 - x1, 3);

    // Person bar
    svg.appendChild(svgEl('rect', { x: x1, y: 24, width: bw, height: 14, rx: 2,
        fill: fl ? 'url(#fh-mini)' : 'var(--jinks-colors-500, #6a5a4a)',
        stroke: fl ? '#888' : 'none', opacity: fl ? 0.7 : 0.85 }));

    // Year labels
    const bLbl = svgEl('text', { x: x1, y: 20, 'text-anchor': 'middle', 'font-size': 9, fill: '#555' });
    bLbl.textContent = p.birth || p.from;
    svg.appendChild(bLbl);
    const dLbl = svgEl('text', { x: x2, y: 20, 'text-anchor': 'middle', 'font-size': 9, fill: '#555' });
    dLbl.textContent = p.death || p.to;
    svg.appendChild(dLbl);

    // Work diamonds
    const D = 5;
    works.forEach(w => {
        const wx = yearToX(w.when, minY, maxY, uw) + PL;
        const g  = svgEl('g', { class: 'work-marker', cursor: 'pointer' });
        g.appendChild(svgTitle(w.label));
        g.appendChild(svgEl('polygon', {
            points: `${wx},${18} ${wx + D},${24} ${wx},${30} ${wx - D},${24}`,
            fill: 'var(--jinks-colors-700, #3a2a1a)', opacity: 0.8
        }));
        g.addEventListener('click', () => { location.href = `${app}/works/${w.id}`; });
        svg.appendChild(g);
    });

    container.appendChild(svg);
}

// ── Work page mini-timeline ──────────────────────────────────────────────────

function initWorkMini() {
    const el = document.querySelector('.mini-timeline[data-entity-type="work"]');
    if (!el) return;
    const app    = el.dataset.app || '';
    const workId = el.dataset.entityId;

    fetch(app + '/api/sino/chronology?type=both')
        .then(r => r.json())
        .then(data => {
            const w = (data.works || []).find(x => x.id === workId);
            if (!w) { el.hidden = true; return; }
            const author = w['author-id']
                ? (data.persons || []).find(p => p.id === w['author-id'])
                : null;
            drawWorkMini(el, w, author, app);
        })
        .catch(() => { el.hidden = true; });
}

function drawWorkMini(container, w, author, app) {
    const W    = Math.max(container.offsetWidth || 500, 240);
    const H    = 64;
    const PL   = 24;
    const PR   = 24;
    const uw   = W - PL - PR;
    const allY = author ? [author.from, author.to, w.when] : [w.when];
    const minY = Math.min(...allY) - 5;
    const maxY = Math.max(...allY) + 5;

    const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, class: 'mini-timeline-svg' });

    // Author bar (background)
    if (author) {
        const ax1 = yearToX(author.from, minY, maxY, uw) + PL;
        const ax2 = yearToX(author.to,   minY, maxY, uw) + PL;
        svg.appendChild(svgEl('rect', { x: ax1, y: 24, width: Math.max(ax2 - ax1, 3), height: 14, rx: 2,
            fill: 'var(--jinks-colors-300, #baa898)', opacity: 0.45 }));
        const albl = svgEl('text', { x: ax1 + 3, y: 34, 'font-size': 9, fill: '#666', class: 'zh' });
        albl.textContent = author.label;
        svg.appendChild(albl);
    }

    // Work diamond
    const wx = yearToX(w.when, minY, maxY, uw) + PL;
    const D  = 7;
    svg.appendChild(svgEl('polygon', {
        points: `${wx},${17} ${wx + D},${24} ${wx},${31} ${wx - D},${24}`,
        fill: 'var(--jinks-colors-700, #3a2a1a)', opacity: 0.9
    }));
    const yl = svgEl('text', { x: wx, y: 44, 'text-anchor': 'middle', 'font-size': 9, fill: '#444' });
    yl.textContent = w['date-label'] || w.when;
    svg.appendChild(yl);

    container.appendChild(svg);
}

// ── Inscription attestation strip ────────────────────────────────────────────

function initAttestationStrip() {
    const strip = document.querySelector('.attestation-strip');
    if (!strip) return;

    const originYear = parseInt(strip.dataset.originYear || '', 10);

    // Collect years from the rendered attestation list in the page
    const items = [];
    document.querySelectorAll('.attestation-list li').forEach(li => {
        const link    = li.querySelector('a.work-title[href]');
        const dateEl  = li.querySelector('.work-date');
        if (!link || !dateEl) return;
        const href    = link.getAttribute('href');
        const idMatch = href.match(/\/works\/(work-[^/?#]+)/);
        if (!idMatch) return;
        const year = parseInt(dateEl.dataset.year || '', 10);
        if (!isFinite(year) || year === 9999) return;
        items.push({ id: idMatch[1], label: link.textContent.trim(), year, href });
    });

    if (!items.length && !isFinite(originYear)) { strip.hidden = true; return; }

    const allY = [...(isFinite(originYear) ? [originYear] : []), ...items.map(i => i.year)];
    const minY = Math.min(...allY) - 40;
    const maxY = Math.max(...allY) + 40;

    const W   = Math.max(strip.offsetWidth || 600, 300);
    const H   = 72;
    const PL  = 30;
    const PR  = 30;
    const uw  = W - PL - PR;

    const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, class: 'attestation-strip-svg' });

    // Base line
    svg.appendChild(svgEl('line', { x1: PL, y1: 36, x2: W - PR, y2: 36,
        stroke: '#ccc', 'stroke-width': 1.5 }));

    // Origin marker (filled circle)
    if (isFinite(originYear)) {
        const ox = yearToX(originYear, minY, maxY, uw) + PL;
        svg.appendChild(svgEl('circle', { cx: ox, cy: 36, r: 6,
            fill: 'var(--jinks-colors-700, #3a2a1a)', opacity: 0.9 }));
        const oy = svgEl('text', { x: ox, y: 55, 'text-anchor': 'middle', 'font-size': 9, fill: '#444' });
        oy.textContent = originYear < 0 ? `${-originYear} BC` : `AD ${originYear}`;
        svg.appendChild(oy);
        const otitle = svgEl('text', { x: ox, y: 25, 'text-anchor': 'middle', 'font-size': 9, fill: '#666' });
        otitle.textContent = strip.dataset.inscriptionName
            ? strip.dataset.inscriptionName.slice(0, 4) : '刊立';
        svg.appendChild(otitle);
    }

    // Attestation markers (small circles)
    items.forEach(item => {
        const ix = yearToX(item.year, minY, maxY, uw) + PL;
        const g  = svgEl('g', { class: 'att-marker', cursor: 'pointer' });
        g.appendChild(svgEl('circle', { cx: ix, cy: 36, r: 5,
            fill: 'var(--jinks-colors-500, #6a5a4a)', opacity: 0.85 }));
        g.appendChild(svgEl('line', { x1: ix, y1: 41, x2: ix, y2: 48,
            stroke: '#aaa', 'stroke-width': 1 }));
        const lbl = svgEl('text', { x: ix, y: 58, 'text-anchor': 'middle',
            'font-size': 8, fill: '#444', class: 'zh' });
        lbl.textContent = item.label.slice(0, 4);
        g.appendChild(lbl);
        const yl2 = svgEl('text', { x: ix, y: 25, 'text-anchor': 'middle', 'font-size': 8, fill: '#666' });
        yl2.textContent = item.year;
        g.appendChild(yl2);
        g.appendChild(svgTitle(`${item.label} (${item.year})`));
        g.addEventListener('click', () => { location.href = item.href; });
        svg.appendChild(g);
    });

    strip.appendChild(svg);
}

// ── Bootstrap ────────────────────────────────────────────────────────────────

function init() {
    initChronologyPage();
    initPersonMini();
    initWorkMini();
    initAttestationStrip();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

})();

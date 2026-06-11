/* EDEp Sino — full-page site map (navigation entry point).
   Uses the leaflet + markercluster builds shipped with pb-components;
   data from /api/sites (find-spots joined with their inscriptions). */
(function () {
    const page = document.querySelector('.sites-map-page');
    if (!page || typeof L === 'undefined') return;
    const app = page.dataset.app || '';
    const panel = document.getElementById('site-panel');

    const map = L.map('sites-map', { scrollWheelZoom: true });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    map.setView([34.5, 110.0], 5);

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function showSite(site) {
        const rows = (site.inscriptions || []).map(i =>
            `<li><a href="${app}/${encodeURIComponent(i.file)}">${esc(i.title) || esc(i.id)}</a>
                 <small>${esc([i.period, i.objtype].filter(Boolean).join(' · '))}</small></li>`
        ).join('');
        panel.classList.remove('empty');
        panel.innerHTML =
            `<h2>${esc(site.name)} <small>${esc(site.pinyin)}</small></h2>
             <p class="site-meta">${esc(site.region)} · ${site.count} <span data-i18n="sites.holdings">inscriptions</span>
                · <a href="${app}/places/${encodeURIComponent(site.id)}" data-i18n="sites.site-page">site page</a></p>
             <ul class="site-inscriptions">${rows || '<li class="none">—</li>'}</ul>`;
    }

    fetch(app + '/api/sites')
        .then(r => r.json())
        .then(data => {
            const cluster = L.markerClusterGroup({ showCoverageOnHover: false });
            const located = [];
            (data.sites || []).forEach(site => {
                const lat = parseFloat(site.lat), lng = parseFloat(site.lng);
                if (!isFinite(lat) || !isFinite(lng)) return;
                const marker = L.marker([lat, lng], {
                    icon: L.divIcon({
                        className: 'site-marker',
                        html: `<span>${site.count}</span>`,
                        iconSize: [30, 30]
                    })
                });
                marker.bindTooltip(site.name);
                marker.on('click', () => showSite(site));
                cluster.addLayer(marker);
                located.push([lat, lng]);
            });
            map.addLayer(cluster);
            if (located.length) map.fitBounds(located, { padding: [40, 40], maxZoom: 8 });
            const first = (data.sites || []).find(s => s.count > 0);
            if (first) showSite(first);
        })
        .catch(() => {
            panel.innerHTML = '<p class="placeholder">Failed to load sites</p>';
        });
})();

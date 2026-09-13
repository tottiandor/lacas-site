/* Laca's Site — front end.
 *
 * The page is completely static. Everything it shows comes from data/news.json,
 * which the GitHub Action regenerates on a schedule. We re-poll that file so a
 * tab left open picks up new stories without a reload.
 */
(function () {
  'use strict';

  var FEED_URL = 'data/news.json';
  var POLL_MS = 90 * 1000;        // how often an open tab re-checks the feed
  var STALE_MS = 60 * 60 * 1000;  // after this, the "live" dot turns amber

  var state = { items: [], sources: [], generatedAt: null, filter: 'all', query: '', seen: {} };

  var el = {
    grid: document.getElementById('grid'),
    chips: document.getElementById('chips'),
    count: document.getElementById('count'),
    empty: document.getElementById('empty'),
    search: document.getElementById('search'),
    statusText: document.getElementById('status-text'),
    pulse: document.getElementById('pulse'),
    refresh: document.getElementById('refresh'),
    sourceList: document.getElementById('source-list')
  };

  // ------------------------------------------------------------- utilities

  var ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) { return ESCAPES[c]; });
  }

  function relativeTime(iso) {
    if (!iso) return '';
    var then = new Date(iso).getTime();
    if (isNaN(then)) return '';
    var mins = Math.round((Date.now() - then) / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return mins + 'm ago';
    var hours = Math.round(mins / 60);
    if (hours < 24) return hours + 'h ago';
    var days = Math.round(hours / 24);
    if (days < 7) return days + 'd ago';
    return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  }

  function remember(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* private mode - ignore */ }
  }

  function recall(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }

  // ---------------------------------------------------------------- render

  function visibleItems() {
    var query = state.query.trim().toLowerCase();
    return state.items.filter(function (item) {
      if (state.filter !== 'all' && item.source !== state.filter) return false;
      if (!query) return true;
      var haystack = item.title + ' ' + (item.summary || '') + ' ' +
                     (item.author || '') + ' ' + item.sourceName;
      return haystack.toLowerCase().indexOf(query) !== -1;
    });
  }

  function cardHtml(item) {
    // If an image 404s or is hotlink-blocked, drop the frame rather than
    // leaving a broken box in the grid.
    var thumb = item.image
      ? '<div class="thumb"><img src="' + escapeHtml(item.image) + '" alt="" loading="lazy" ' +
        'onerror="this.parentNode.remove()"></div>'
      : '';
    var dek = item.summary ? '<p class="dek">' + escapeHtml(item.summary) + '</p>' : '';

    var bits = [];
    if (item.author) bits.push(escapeHtml(item.author));
    if (item.category) bits.push(escapeHtml(item.category));

    var when = relativeTime(item.publishedAt);
    if (when) {
      bits.push(item.datePrecise
        ? escapeHtml(when)
        : '<span title="Approximate: taken from when we first saw this story">' +
          escapeHtml(when) + '*</span>');
    }

    return '<a class="card' + (state.seen[item.id] ? '' : ' is-new') + '"' +
           ' href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener noreferrer"' +
           ' style="--chip:' + escapeHtml(item.accent || '#888') + '">' +
           thumb +
           '<div class="card-body">' +
             '<span class="badge"><span class="dot"></span>' + escapeHtml(item.sourceName) + '</span>' +
             '<h2>' + escapeHtml(item.title) + '</h2>' + dek +
             '<div class="meta">' + bits.join(' <span class="sep">&middot;</span> ') + '</div>' +
           '</div></a>';
  }

  function renderChips() {
    var counts = {};
    state.items.forEach(function (i) { counts[i.source] = (counts[i.source] || 0) + 1; });

    var html = '<button class="chip" type="button" data-source="all" aria-pressed="' +
               (state.filter === 'all') + '">All <span class="n">' + state.items.length +
               '</span></button>';

    state.sources.forEach(function (source) {
      var failed = source.status === 'error';
      html += '<button class="chip' + (failed ? ' failed' : '') + '" type="button"' +
              ' data-source="' + escapeHtml(source.id) + '"' +
              ' aria-pressed="' + (state.filter === source.id) + '"' +
              ' style="--chip:' + escapeHtml(source.accent || '#888') + '"' +
              (failed ? ' title="This source failed on the last run"' : '') + '>' +
              '<span class="dot"></span>' + escapeHtml(source.name) +
              ' <span class="n">' + (counts[source.id] || 0) + '</span></button>';
    });
    el.chips.innerHTML = html;
  }

  function render() {
    var items = visibleItems();
    el.grid.innerHTML = items.map(cardHtml).join('');
    el.empty.hidden = items.length > 0;
    el.count.textContent = items.length
      ? 'Showing ' + items.length + ' ' + (items.length === 1 ? 'story' : 'stories') +
        (state.filter === 'all' ? ' from ' + state.sources.length + ' sources' : '')
      : '';
    items.forEach(function (i) { state.seen[i.id] = true; });
    renderChips();
  }

  function renderStatus() {
    if (!state.generatedAt) return;
    var age = Date.now() - new Date(state.generatedAt).getTime();
    el.pulse.className = 'pulse' + (age > STALE_MS * 6 ? ' dead' : age > STALE_MS ? ' stale' : '');
    el.statusText.textContent = 'Updated ' + relativeTime(state.generatedAt);
  }

  function renderFooter() {
    el.sourceList.innerHTML = 'Sources: ' + state.sources.map(function (s) {
      return '<a href="' + escapeHtml(s.site) + '" target="_blank" rel="noopener noreferrer">' +
             escapeHtml(s.name) + '</a>';
    }).join(' &middot; ');
  }

  // ------------------------------------------------------------------ data

  function load(isManual) {
    if (isManual) el.refresh.disabled = true;

    // Cache-bust so the Pages CDN cannot hand us a stale copy.
    return fetch(FEED_URL + '?t=' + Date.now(), { cache: 'no-store' })
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      })
      .then(function (data) {
        var firstLoad = state.items.length === 0;
        state.items = data.items || [];
        state.sources = data.sources || [];
        state.generatedAt = data.generatedAt;
        // Nothing should flash as "new" on the very first paint.
        if (firstLoad) state.items.forEach(function (i) { state.seen[i.id] = true; });
        render();
        renderStatus();
        renderFooter();
      })
      .catch(function (error) {
        el.pulse.className = 'pulse dead';
        el.statusText.textContent = 'Could not load the feed';
        if (!state.items.length) {
          el.grid.innerHTML = '<p class="empty">No stories yet. If you have just set this up, run the ' +
            '<strong>Collect news</strong> action once to generate <code>data/news.json</code>.</p>';
        }
        console.error('[laca] feed load failed:', error);
      })
      .then(function () { el.refresh.disabled = false; });
  }

  // --------------------------------------------------------------- wire up

  el.chips.addEventListener('click', function (event) {
    var button = event.target.closest('.chip');
    if (!button) return;
    state.filter = button.dataset.source;
    remember('laca:filter', state.filter);
    render();
  });

  var searchTimer;
  el.search.addEventListener('input', function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () { state.query = el.search.value; render(); }, 120);
  });

  el.refresh.addEventListener('click', function () { load(true); });

  state.filter = recall('laca:filter') || 'all';

  load();
  setInterval(function () { if (!document.hidden) load(); }, POLL_MS);
  setInterval(renderStatus, 60 * 1000);  // keep "updated 5m ago" honest
  document.addEventListener('visibilitychange', function () { if (!document.hidden) load(); });
})();

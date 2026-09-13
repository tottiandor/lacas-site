/* Laca's Site — front end.
 *
 * The page is completely static. Everything it shows comes from data/news.json,
 * which the GitHub Action regenerates on a schedule. We re-poll that file so a
 * tab left open picks up new stories without a reload.
 */
(function () {
  'use strict';

  var FEED_URL = 'data/news.json';
  var POLL_MS = 10 * 60 * 1000;   // collection is nightly; a slow poll is plenty
  var STALE_MS = 36 * 60 * 60 * 1000;  // collection is nightly, so allow a long gap
  var NEW_MS = 24 * 60 * 60 * 1000;    // "New" badge window
  var TAGBAR_LIMIT = 14;               // topic chips shown above the feed

  var state = {
    items: [], sources: [], generatedAt: null,
    filter: 'all', tag: null, query: ''
  };

  var el = {};
  ['grid', 'chips', 'tagbar', 'count', 'empty', 'search', 'status-text', 'pulse',
   'refresh', 'source-list', 'modal', 'modal-source', 'modal-title', 'modal-meta',
   'modal-summary', 'modal-tags', 'modal-attrib', 'modal-link'].forEach(function (id) {
    el[id] = document.getElementById(id);
  });

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

  function isNew(item) {
    return Date.now() - new Date(item.firstSeenAt || item.publishedAt).getTime() < NEW_MS;
  }

  // ---------------------------------------------------------------- filtering

  /** Items matching the current source filter, used to build the topic bar. */
  function inSource() {
    return state.items.filter(function (item) {
      return state.filter === 'all' || item.source === state.filter;
    });
  }

  function visibleItems() {
    var query = state.query.trim().toLowerCase();
    return inSource().filter(function (item) {
      if (state.tag && (item.tags || []).indexOf(state.tag) === -1) return false;
      if (!query) return true;
      var haystack = item.title + ' ' + (item.summary || '') + ' ' + (item.author || '') +
                     ' ' + item.sourceName + ' ' + (item.tags || []).join(' ');
      return haystack.toLowerCase().indexOf(query) !== -1;
    });
  }

  // ---------------------------------------------------------------- render

  function cardHtml(item, index) {
    // If an image 404s or is hotlink-blocked, drop the frame rather than
    // leaving a broken box in the grid.
    var thumb = item.image
      ? '<a class="thumb" href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener noreferrer" tabindex="-1">' +
        '<img src="' + escapeHtml(item.image) + '" alt="" loading="lazy" ' +
        'onerror="this.parentNode.remove()"></a>'
      : '';

    var dek = item.summary ? '<p class="dek">' + escapeHtml(item.summary) + '</p>' : '';

    var tags = (item.tags || []).map(function (tag) {
      return '<button class="tag" type="button" data-tag="' + escapeHtml(tag) + '">' +
             escapeHtml(tag) + '</button>';
    }).join('');

    var bits = [];
    if (item.author) bits.push(escapeHtml(item.author));
    var when = relativeTime(item.publishedAt);
    if (when) {
      bits.push(item.datePrecise
        ? escapeHtml(when)
        : '<span title="Approximate: taken from when we first saw this story">' +
          escapeHtml(when) + '*</span>');
    }

    return '<article class="card" style="--chip:' + escapeHtml(item.accent || '#888') + '">' +
      thumb +
      '<div class="card-body">' +
        '<span class="badge"><span class="dot"></span>' + escapeHtml(item.sourceName) +
          (isNew(item) ? '<span class="new-flag">New</span>' : '') + '</span>' +
        '<h2><a href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener noreferrer">' +
          escapeHtml(item.title) + '</a></h2>' +
        dek +
        (tags ? '<div class="tags">' + tags + '</div>' : '') +
        '<div class="meta">' + bits.join(' <span class="sep">&middot;</span> ') + '</div>' +
        '<div class="actions">' +
          '<button class="btn btn-summary" type="button" data-summary="' + index + '">Summary</button>' +
          '<a class="btn btn-read" href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener noreferrer">Read &rarr;</a>' +
        '</div>' +
      '</div></article>';
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

  /** Topic bar: the most common tags within whichever source is selected. */
  function renderTagbar() {
    var counts = {};
    inSource().forEach(function (item) {
      (item.tags || []).forEach(function (tag) { counts[tag] = (counts[tag] || 0) + 1; });
    });

    var ranked = Object.keys(counts).sort(function (a, b) {
      return counts[b] - counts[a] || a.localeCompare(b);
    });

    // Always keep the active tag visible, even if it is rare in this source.
    var shown = ranked.slice(0, TAGBAR_LIMIT);
    if (state.tag && shown.indexOf(state.tag) === -1) shown.unshift(state.tag);

    if (!shown.length) { el.tagbar.innerHTML = ''; return; }

    var html = '<span class="tagbar-label">Topics</span>';
    html += shown.map(function (tag) {
      return '<button class="tag' + (state.tag === tag ? ' on' : '') + '" type="button"' +
             ' data-tag="' + escapeHtml(tag) + '" aria-pressed="' + (state.tag === tag) + '">' +
             escapeHtml(tag) + '<span class="n">' + (counts[tag] || 0) + '</span></button>';
    }).join('');

    if (state.tag) {
      html += '<button class="tag clear" type="button" data-tag-clear="1">Clear topic &times;</button>';
    }
    el.tagbar.innerHTML = html;
  }

  function render() {
    var items = visibleItems();
    window.__visible = items;   // the Summary buttons index into this
    el.grid.innerHTML = items.map(cardHtml).join('');
    el.empty.hidden = items.length > 0;

    var scope = [];
    if (state.filter !== 'all') {
      var source = state.sources.filter(function (s) { return s.id === state.filter; })[0];
      if (source) scope.push('from ' + source.name);
    } else {
      scope.push('from ' + state.sources.length + ' sources');
    }
    if (state.tag) scope.push('tagged ' + state.tag);

    el.count.textContent = items.length
      ? 'Showing ' + items.length + ' ' + (items.length === 1 ? 'story' : 'stories') +
        (scope.length ? ' ' + scope.join(', ') : '')
      : '';

    renderChips();
    renderTagbar();
  }

  function renderStatus() {
    if (!state.generatedAt) return;
    var age = Date.now() - new Date(state.generatedAt).getTime();
    el.pulse.className = 'pulse' + (age > STALE_MS * 3 ? ' dead' : age > STALE_MS ? ' stale' : '');
    el['status-text'].textContent = 'Updated ' + relativeTime(state.generatedAt);
  }

  function renderFooter() {
    el['source-list'].innerHTML = 'Sources: ' + state.sources.map(function (s) {
      return '<a href="' + escapeHtml(s.site) + '" target="_blank" rel="noopener noreferrer">' +
             escapeHtml(s.name) + '</a>';
    }).join(' &middot; ');
  }

  // ----------------------------------------------------------------- modal

  var lastFocused = null;

  function openSummary(item) {
    lastFocused = document.activeElement;

    el['modal-source'].innerHTML = '<span class="dot"></span>' + escapeHtml(item.sourceName);
    el['modal-source'].style.setProperty('--chip', item.accent || '#888');
    el['modal-title'].textContent = item.title;

    var meta = [];
    if (item.author) meta.push(item.author);
    if (item.category) meta.push(item.category);
    var when = relativeTime(item.publishedAt);
    if (when) meta.push(when);
    el['modal-meta'].textContent = meta.join(' · ');

    var text = item.fullSummary || item.summary || '';
    el['modal-summary'].textContent = text ||
      'This publisher does not supply a summary with its feed — the headline is all it sends. ' +
      'Open the article to read it in full.';
    el['modal-summary'].classList.toggle('none', !text);

    el['modal-tags'].innerHTML = (item.tags || []).map(function (tag) {
      return '<button class="tag" type="button" data-tag="' + escapeHtml(tag) + '">' +
             escapeHtml(tag) + '</button>';
    }).join('');

    // Be explicit about whose words these are. Nothing here is written by us.
    el['modal-attrib'].textContent = text
      ? 'Summary published by ' + item.sourceName + '.'
      : '';

    el['modal-link'].href = item.url;
    el.modal.hidden = false;
    document.body.classList.add('modal-open');
    el['modal-link'].focus();
  }

  function closeSummary() {
    el.modal.hidden = true;
    document.body.classList.remove('modal-open');
    if (lastFocused && lastFocused.focus) lastFocused.focus();
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
        // Collection is nightly, so most polls find nothing new. Rebuilding the
        // grid anyway would reload every image and throw away whatever the
        // reader was hovering or mid-click on, so only redraw on a real change.
        var changed = data.generatedAt !== state.generatedAt;
        state.items = data.items || [];
        state.sources = data.sources || [];
        state.generatedAt = data.generatedAt;
        if (changed) {
          render();
          renderFooter();
        }
        renderStatus();
      })
      .catch(function (error) {
        el.pulse.className = 'pulse dead';
        el['status-text'].textContent = 'Could not load the feed';
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
    // A topic that does not exist in the newly chosen source would show nothing.
    if (state.tag && !inSource().some(function (i) { return (i.tags || []).indexOf(state.tag) !== -1; })) {
      state.tag = null;
    }
    remember('laca:filter', state.filter);
    render();
  });

  // Topic clicks come from the topic bar, the cards and the modal alike.
  document.addEventListener('click', function (event) {
    var clear = event.target.closest('[data-tag-clear]');
    if (clear) { state.tag = null; render(); return; }

    var tagButton = event.target.closest('[data-tag]');
    if (tagButton) {
      var tag = tagButton.dataset.tag;
      state.tag = state.tag === tag ? null : tag;
      if (!el.modal.hidden) closeSummary();
      render();
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    var summaryButton = event.target.closest('[data-summary]');
    if (summaryButton) {
      var item = (window.__visible || [])[Number(summaryButton.dataset.summary)];
      if (item) openSummary(item);
      return;
    }

    if (event.target.closest('[data-close]')) closeSummary();
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !el.modal.hidden) closeSummary();
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

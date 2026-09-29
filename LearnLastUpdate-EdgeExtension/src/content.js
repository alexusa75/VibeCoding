(() => {
  const prev = globalThis.__lluContent;
  if (prev && prev.alive()) return;

  const HOST_ID = 'llu-last-update-card';
  const alive = () => {
    try {
      return Boolean(chrome.runtime && chrome.runtime.id);
    } catch {
      return false;
    }
  };
  globalThis.__lluContent = { alive };

  let settings = { ...LLU.DEFAULT_SETTINGS };
  let info = null;
  let lastKey = '';
  let host = null;
  let timer = 0;

  const hiddenKey = () => `llu:hidden:${location.pathname}`;

  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid);
    return el;
  }

  function theme() {
    const c = document.documentElement.classList;
    if (c.contains('theme-high-contrast')) return 'hc';
    if (c.contains('theme-dark')) return 'dark';
    if (c.contains('theme-light')) return 'light';
    return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function initials(s) {
    const parts = (s || '?').replace(/[^A-Za-z0-9 ]/g, ' ').trim().split(/\s+/);
    return ((parts[0] || '?')[0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
  }

  function anchor() {
    const h1 = document.querySelector('main h1, #main h1, h1');
    if (!h1) return null;
    const next = h1.nextElementSibling;
    return next && next.matches('ul.metadata, .page-metadata') ? next : h1;
  }

  function removeCard() {
    document.querySelectorAll(`#${HOST_ID}`).forEach((n) => n.remove());
    host = null;
  }

  function render() {
    removeCard();
    if (!info || !info.hasArticle || !settings.showCard) return;
    if (sessionStorage.getItem(hiddenKey())) return;
    const at = anchor();
    if (!at) return;

    const { value, dateOnly, source } = info.primary;
    const f = LLU.freshness(value);
    const rev = info.republished;
    const login = info.author;
    const repo = LLU.parseGitHub(info.publicSourceUrl) || LLU.parseGitHub(info.sourceUrl);
    const sourceNote =
      source === 'learn' ? 'Date shown by Learn' : source === 'ms.date' ? 'From ms.date' : 'From updated_at';

    // Avatars come from github.com, so they follow the "GitHub lookups" setting like the API calls.
    const avatar = login && settings.githubLookups
      ? h('img', {
          class: 'av',
          alt: '',
          src: LLU.avatarUrl(login, 48),
          referrerpolicy: 'no-referrer',
          onerror: (e) => e.target.replaceWith(h('span', { class: 'initials', text: initials(login) })),
        })
      : h('span', { class: 'initials', text: initials(login || info.msAuthor) });

    const nameEl = login
      ? h('a', { class: 'name', href: LLU.githubProfile(login), target: '_blank', rel: 'noopener', text: login })
      : h('span', { class: 'name', text: info.msAuthor });

    const handles = h(
      'span',
      { class: 'handle' },
      login ? h('b', { text: `@${login}` }) : null,
      info.msAuthor && info.msAuthor !== login ? ` · ${info.msAuthor}` : null
    );

    const card = h(
      'div',
      {
        class: 'card',
        'data-level': f.level,
        'data-theme': theme(),
        role: 'note',
        'aria-label': 'Article last update and writer',
      },
      h('span', { class: 'stamp', title: `${f.label}: ${LLU.daysSince(value)} days since last update`, text: f.label }),
      h(
        'span',
        { class: 'group when' },
        h('span', { class: 'lbl', text: 'Last updated' }),
        h('time', { class: 'date', datetime: value, title: sourceNote, text: LLU.formatDate(value, { dateOnly }) }),
        h('span', { class: 'rel', text: LLU.relative(value) })
      ),
      h(
        'span',
        { class: 'group who' },
        h('span', { class: 'lbl', text: 'Written by' }),
        avatar,
        nameEl,
        login ? handles : null
      ),
      repo
        ? h(
            'span',
            { class: 'links' },
            h('a', { href: repo.historyUrl, target: '_blank', rel: 'noopener', text: 'History', title: 'Commit history on GitHub' })
          )
        : null,
      rev
        ? h(
            'span',
            { class: 'rev', title: LLU.republishedTitle(rev) },
            h('span', { class: 'rev-mark', 'aria-hidden': 'true', text: '↻' }),
            h('b', { text: `Republished ${LLU.formatDate(rev.value)}` }),
            ': content may have changed since the last-updated date'
          )
        : null,
      h('button', {
        class: 'x',
        type: 'button',
        title: 'Hide on this page',
        'aria-label': 'Hide last update card on this page',
        text: '×',
        onclick: () => {
          sessionStorage.setItem(hiddenKey(), '1');
          removeCard();
        },
      })
    );

    host = h('div', { id: HOST_ID, 'data-llu': '1' });
    const root = host.attachShadow({ mode: 'open' });
    root.append(h('style', { text: globalThis.LLU_CARD_CSS }), card);
    at.insertAdjacentElement('afterend', host);

    if (login && settings.githubLookups) {
      chrome.runtime
        .sendMessage({ type: 'githubUser', login })
        .then((res) => {
          const u = res && res.value;
          if (u && u.name && nameEl.isConnected) {
            nameEl.textContent = u.name;
            nameEl.title = `${u.name} (@${u.login}) on GitHub`;
          }
        })
        .catch(() => {});
    }
  }

  function refresh(force) {
    if (!alive()) return teardown();
    const next = LLU.extract(document);
    const key = [location.href, next.primary && next.primary.value, next.updatedAt, next.author, next.msAuthor].join('|');
    const changed = key !== lastKey;
    info = next;
    lastKey = key;
    if (changed || force) {
      chrome.runtime.sendMessage({ type: 'pageInfo', info }).catch(() => {});
      render();
    } else if (info.hasArticle && settings.showCard && !host && !sessionStorage.getItem(hiddenKey())) {
      render();
    }
  }

  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(() => refresh(false), 250);
  }

  function onMessage(msg, _sender, sendResponse) {
    if (msg && msg.type === 'getPageInfo') {
      sendResponse(info || LLU.extract(document));
    } else if (msg && msg.type === 'showCardAgain') {
      sessionStorage.removeItem(hiddenKey());
      render();
      sendResponse(true);
    }
    return false;
  }

  function onStorage(changes, area) {
    if (area === 'sync' && changes.settings) {
      settings = { ...LLU.DEFAULT_SETTINGS, ...(changes.settings.newValue || {}) };
      render();
    }
  }

  const observer = new MutationObserver((records) => {
    for (const r of records) {
      if (r.target === document.documentElement && r.attributeName === 'class') {
        const card = host && host.shadowRoot && host.shadowRoot.querySelector('.card');
        if (card) card.dataset.theme = theme();
        continue;
      }
      schedule();
      return;
    }
  });

  function teardown() {
    observer.disconnect();
    if (host) host.remove();
    host = null;
    window.removeEventListener('popstate', schedule);
  }

  chrome.runtime.onMessage.addListener(onMessage);
  chrome.storage.onChanged.addListener(onStorage);
  window.addEventListener('popstate', schedule);

  chrome.storage.sync
    .get('settings')
    .then((s) => {
      settings = { ...LLU.DEFAULT_SETTINGS, ...(s.settings || {}) };
    })
    .catch(() => {})
    .finally(() => {
      refresh(true);
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
      if (document.head) observer.observe(document.head, { childList: true, subtree: true, attributes: true });
      const main = document.querySelector('main') || document.body;
      if (main) observer.observe(main, { childList: true, subtree: true });
    });
})();

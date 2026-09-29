const $ = (id) => document.getElementById(id);
const sheet = $('sheet');
const ALIAS = /^[a-z0-9][a-z0-9._-]*$/i;
const CONTENT_FILES = ['src/core.js', 'src/card-styles.js', 'src/content.js'];
const ICONS = {
  user: 'M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm0 1.5c-3 0-5.5 1.6-5.5 3.6V14h11v-.9c0-2-2.5-3.6-5.5-3.6Z',
  mail: 'M1.5 3h13c.3 0 .5.2.5.5v9c0 .3-.2.5-.5.5h-13a.5.5 0 0 1-.5-.5v-9c0-.3.2-.5.5-.5Zm.9 1.5L8 8.4l5.6-3.9H2.4Zm11.1 1.3L8.3 9.4a.5.5 0 0 1-.6 0L2.5 5.8v5.7h11V5.8Z',
  chat: 'M2 2.5h12c.3 0 .5.2.5.5v8c0 .3-.2.5-.5.5H7l-3.2 2.4a.3.3 0 0 1-.5-.2v-2.2H2a.5.5 0 0 1-.5-.5V3c0-.3.2-.5.5-.5Z',
};

let settings = { ...LLU.DEFAULT_SETTINGS };
let current = null;
let tabId = null;
let writerDisplay = '';

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

function svg(path) {
  const ns = 'http://www.w3.org/2000/svg';
  const s = document.createElementNS(ns, 'svg');
  s.setAttribute('viewBox', '0 0 16 16');
  s.setAttribute('aria-hidden', 'true');
  const p = document.createElementNS(ns, 'path');
  p.setAttribute('d', path);
  s.append(p);
  return s;
}

function initials(s) {
  const parts = (s || '?').replace(/[^A-Za-z0-9 ]/g, ' ').trim().split(/\s+/);
  return ((parts[0] || '?')[0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
}

function link(href, text, title) {
  return h('a', { href, target: '_blank', rel: 'noopener', title }, text);
}

async function init() {
  try {
    const s = await chrome.storage.sync.get('settings');
    settings = { ...LLU.DEFAULT_SETTINGS, ...(s.settings || {}) };
  } catch {}
  $('optCard').checked = settings.showCard;
  $('optGh').checked = settings.githubLookups;
  $('optCard').addEventListener('change', onToggle);
  $('optGh').addEventListener('change', onToggle);
  $('copyBtn').addEventListener('click', copySummary);

  const tab = await targetTab();
  if (!tab || !LLU.isLearnUrl(tab.url)) return showEmpty();
  tabId = tab.id;

  const info = await getInfo(tab.id);
  if (!info || !info.hasArticle) {
    return showEmpty(
      'No article metadata here',
      "This Learn page doesn't publish an update date or writer. Try an article, module or reference page."
    );
  }
  render(info);
}

// popup.html?tabId=N inspects a specific tab (used when the popup is opened as a page for testing).
async function targetTab() {
  const forced = Number(new URLSearchParams(location.search).get('tabId'));
  if (forced) return chrome.tabs.get(forced).catch(() => null);
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function getInfo(id) {
  try {
    const r = await chrome.tabs.sendMessage(id, { type: 'getPageInfo' });
    if (r) return r;
  } catch {}
  try {
    // Tab was open before the extension was installed or reloaded.
    await chrome.scripting.executeScript({ target: { tabId: id }, files: CONTENT_FILES });
    return await chrome.tabs.sendMessage(id, { type: 'getPageInfo' });
  } catch {
    return null;
  }
}

function showEmpty(title, text) {
  if (title) {
    document.querySelector('.empty-title').textContent = title;
    $('emptyText').textContent = text;
    $('openLearn').hidden = true;
  }
  sheet.dataset.state = 'empty';
}

function render(info) {
  current = info;
  const { value, dateOnly, source } = info.primary;
  const f = LLU.freshness(value);
  const days = LLU.daysSince(value);
  const repo = LLU.parseGitHub(info.publicSourceUrl) || LLU.parseGitHub(info.sourceUrl);
  const privateRepo = LLU.parseGitHub(info.sourceUrl);

  sheet.dataset.level = f.level;
  $('title').textContent = info.title;
  $('title').title = info.title;

  $('bigDate').textContent = LLU.formatDate(value, { dateOnly });
  $('bigDate').setAttribute('datetime', value);
  const sourceNote = { learn: 'as shown on the page', 'ms.date': 'from ms.date', updated_at: 'last published' }[source];
  $('relDate').replaceChildren(`${cap(LLU.relative(value))} · `, h('em', { text: sourceNote }));
  $('stamp').textContent = f.label;
  $('stamp').title = `${days} day${days === 1 ? '' : 's'} since the last update`;
  renderRepublished(LLU.republished(info));

  renderWriter(info);
  renderLedger(info, repo, privateRepo);
  renderLinks(repo, privateRepo);

  $('copyBtn').disabled = false;
  sheet.dataset.state = 'ready';
}

function renderRepublished(rev) {
  const note = $('revNote');
  note.hidden = !rev;
  if (!rev) return note.replaceChildren();
  note.title = LLU.republishedTitle(rev);
  note.replaceChildren(
    h('span', { class: 'rev-mark', 'aria-hidden': 'true', text: '↻' }),
    h(
      'span',
      null,
      h('b', { text: `Republished ${LLU.formatDate(rev.value)}` }),
      `, ${rev.days} days later. Content may have changed since this date.`
    )
  );
}

function renderWriter(info) {
  const login = info.author;
  const alias = info.msAuthor;
  writerDisplay = login || alias;

  const fallback = () => h('span', { class: 'initials', text: initials(writerDisplay) });
  $('avWrap').replaceChildren(
    login && settings.githubLookups
      ? h('img', {
          class: 'av',
          alt: '',
          src: LLU.avatarUrl(login, 96),
          referrerpolicy: 'no-referrer',
          onerror: (e) => e.target.replaceWith(fallback()),
        })
      : fallback()
  );

  const nameEl = $('writerName');
  nameEl.textContent = writerDisplay;
  if (login) nameEl.href = LLU.githubProfile(login);
  else nameEl.removeAttribute('href');

  const handles = [];
  if (login) handles.push(h('span', { title: 'GitHub account (author)' }, h('b', { text: `@${login}` })));
  if (alias && alias !== login) {
    if (handles.length) handles.push(h('span', { class: 'dot', text: '·' }));
    handles.push(h('span', { title: 'Microsoft alias (ms.author)', text: `${alias}` }), h('span', { class: 'muted-note', text: ' ms alias' }));
  } else if (alias) {
    handles.push(h('span', { class: 'muted-note', text: ' · same ms alias' }));
  }
  $('handles').replaceChildren(...handles);

  const chips = [];
  if (login) chips.push(chip(LLU.githubProfile(login), 'GitHub', ICONS.user, 'Open GitHub profile'));
  if (alias && ALIAS.test(alias)) {
    const email = `${alias}@microsoft.com`;
    const subject = `Question about "${info.title}"`;
    chips.push(
      chip(`mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(info.url)}`, 'Email', ICONS.mail, email),
      chip(
        `https://teams.microsoft.com/l/chat/0/0?users=${encodeURIComponent(email)}&message=${encodeURIComponent(`Hi! ${subject}: ${info.url}`)}`,
        'Teams chat',
        ICONS.chat,
        `Chat with ${email} in Teams`
      )
    );
  }
  $('writerActions').replaceChildren(...chips);

  const people = [];
  if (info.manager) people.push(person('Manager', info.manager));
  if (info.reviewers.length) people.push(person(info.reviewers.length > 1 ? 'Reviewers' : 'Reviewer', info.reviewers.join(', ')));
  $('people').replaceChildren(...people);

  if (login && settings.githubLookups) {
    chrome.runtime
      .sendMessage({ type: 'githubUser', login })
      .then((res) => {
        const u = res && res.value;
        if (u && u.name) {
          writerDisplay = u.name;
          nameEl.textContent = u.name;
          nameEl.title = `${u.name}${u.company ? ` · ${u.company}` : ''}`;
        }
      })
      .catch(() => {});
  }
}

function chip(href, text, icon, title) {
  const target = href.startsWith('mailto:') ? null : '_blank';
  return h('a', { class: 'chip', href, target, rel: target ? 'noopener' : null, title }, svg(icon), text);
}

function person(label, value) {
  return h('div', null, h('dt', { text: label }), h('dd', { text: value }));
}

function row(label, tag, valueNode, cls) {
  return h(
    'div',
    { class: 'row' },
    h('dt', null, label, tag ? h('small', { text: tag }) : null),
    h('span', { class: 'dots', 'aria-hidden': 'true' }),
    h('dd', { class: cls || null }, valueNode)
  );
}

function renderLedger(info, repo, privateRepo) {
  const rows = [];
  if (info.shownDate) rows.push(row('Shown on page', null, LLU.formatDate(info.shownDate)));
  if (info.msDate) rows.push(row('Reviewed', 'ms.date', LLU.formatDate(info.msDate, { dateOnly: true })));
  if (info.updatedAt) {
    const rev = LLU.republished(info);
    const published = LLU.formatDate(info.updatedAt, { time: true });
    const r = row('Published', 'updated_at', rev ? [h('span', { class: 'rev-mark', 'aria-hidden': 'true', text: '↻ ' }), published] : published);
    if (rev) r.querySelector('dd').title = LLU.republishedTitle(rev);
    rows.push(r);
  }

  let commitRow = null;
  let commitNote = null;
  const isPrivate = repo && isPrivateRepo(repo);
  const lookup = repo && settings.githubLookups && !isPrivate;
  if (repo) {
    const label = isPrivate ? 'private repo' : settings.githubLookups ? 'checking…' : 'lookups off';
    commitRow = row('Last commit', 'GitHub', label, lookup ? 'pending' : 'dim');
    if (isPrivate) commitRow.querySelector('dd').title = "Source is only in a private MicrosoftDocs repo, which GitHub's public API can't read";
    rows.push(commitRow);
  }
  if (info.commitId) {
    const short = info.commitId.slice(0, 7);
    const node = privateRepo
      ? link(`${privateRepo.repoUrl}/commit/${info.commitId}`, short, 'Build commit in the source repo (may require MicrosoftDocs access)')
      : short;
    rows.push(row('Built from', 'git_commit_id', node, 'mono'));
  }
  $('ledger').replaceChildren(...rows);

  if (lookup) {
    chrome.runtime
      .sendMessage({ type: 'latestCommit', repo })
      .then((res) => {
        const dd = commitRow.querySelector('dd');
        dd.className = '';
        if (res && res.value) {
          const c = res.value;
          dd.replaceChildren(link(c.url, LLU.formatDate(c.date), `${c.sha.slice(0, 7)} · ${LLU.relative(c.date)}`));
          const who = c.authorLogin ? `@${c.authorLogin}` : c.authorName;
          commitNote = h('p', { class: 'row-note', title: c.message, text: `${who ? `${who}: ` : ''}${c.message}` });
          commitRow.after(commitNote);
        } else if (res && res.error === 'rate-limited') {
          dd.className = 'dim';
          dd.textContent = `rate-limited until ${new Date(res.until).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
        } else {
          dd.className = 'dim';
          dd.textContent = res && res.value === null ? 'not found' : 'unavailable';
        }
      })
      .catch(() => {
        const dd = commitRow.querySelector('dd');
        dd.className = 'dim';
        dd.textContent = 'unavailable';
      });
  }
}

function isPrivateRepo(repo) {
  return /-pr$/i.test(repo.repo);
}

function renderLinks(repo, privateRepo) {
  const links = [];
  const ms = () => h('span', { class: 'lock', text: ' (MS)' });
  if (repo) {
    const priv = isPrivateRepo(repo);
    const note = priv ? ' (private repo, requires MicrosoftDocs access)' : '';
    links.push(h('a', { href: repo.historyUrl, target: '_blank', rel: 'noopener', title: `Every change to this article on GitHub${note}` }, 'Commit history', priv ? ms() : null, ' ↗'));
    links.push(h('a', { href: repo.fileUrl, target: '_blank', rel: 'noopener', title: `Markdown source on GitHub${note}` }, 'Source', priv ? ms() : null, ' ↗'));
  }
  if (privateRepo && (!repo || privateRepo.repoUrl !== repo.repoUrl)) {
    links.push(
      h(
        'a',
        { href: privateRepo.historyUrl, target: '_blank', rel: 'noopener', title: 'Private authoring repo (requires MicrosoftDocs access)' },
        'Private repo ',
        h('span', { class: 'lock', text: '(MS)' }),
        ' ↗'
      )
    );
  }
  $('links').replaceChildren(...links);
}

async function onToggle() {
  settings = { showCard: $('optCard').checked, githubLookups: $('optGh').checked };
  await chrome.storage.sync.set({ settings });
  if (settings.showCard && tabId != null) {
    chrome.tabs.sendMessage(tabId, { type: 'showCardAgain' }).catch(() => {});
  }
  if (current) render(current);
}

async function copySummary() {
  if (!current) return;
  const { value, dateOnly } = current.primary;
  const alias = current.msAuthor && current.msAuthor !== current.author ? `, ${current.msAuthor}` : '';
  const handle = current.author ? ` (@${current.author}${alias})` : alias ? ` (${current.msAuthor})` : '';
  const rev = LLU.republished(current);
  const text =
    `${current.title}\n` +
    `Last updated: ${LLU.formatDate(value, { dateOnly })} (${LLU.relative(value)})\n` +
    (rev ? `Republished: ${LLU.formatDate(rev.value)} (content may have changed since the last-updated date)\n` : '') +
    `Writer: ${writerDisplay}${handle}\n` +
    current.url;
  const btn = $('copyBtn');
  try {
    await navigator.clipboard.writeText(text);
    btn.textContent = 'Copied';
    btn.classList.add('done');
  } catch {
    btn.textContent = 'Failed';
  }
  setTimeout(() => {
    btn.textContent = 'Copy';
    btn.classList.remove('done');
  }, 1400);
}

function cap(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

init();

importScripts('core.js');

const USER_TTL = 7 * 86400000;
const MISS_TTL = 86400000;
const COMMIT_TTL = 6 * 3600000;
const inflight = new Map();

chrome.runtime.onInstalled.addListener(pruneCache);
chrome.runtime.onStartup.addListener(pruneCache);

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === 'loading') clearBadge(tabId);
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || typeof msg.type !== 'string') return false;
  switch (msg.type) {
    case 'pageInfo':
      updateBadge(sender.tab && sender.tab.id, msg.info);
      return false;
    case 'githubUser':
      githubUser(msg.login).then(sendResponse);
      return true;
    case 'latestCommit':
      latestCommit(msg.repo).then(sendResponse);
      return true;
    default:
      return false;
  }
});

function clearBadge(tabId) {
  if (tabId == null) return;
  chrome.action.setBadgeText({ tabId, text: '' }).catch(() => {});
  chrome.action.setTitle({ tabId, title: 'Learn Last Update' }).catch(() => {});
}

function updateBadge(tabId, info) {
  if (tabId == null) return;
  if (!info || !info.hasArticle || !info.primary) return clearBadge(tabId);
  const { value, dateOnly } = info.primary;
  const f = LLU.freshness(value);
  const writer = info.author ? `@${info.author}` : info.msAuthor;
  const alias = info.msAuthor && info.msAuthor !== info.author ? ` (${info.msAuthor})` : '';
  const rev = LLU.republished(info);
  const revLine = rev ? `\nRepublished ${LLU.formatDate(rev.value)}: content may have changed since` : '';
  chrome.action.setBadgeText({ tabId, text: LLU.badgeText(value) }).catch(() => {});
  chrome.action.setBadgeBackgroundColor({ tabId, color: f.color }).catch(() => {});
  if (chrome.action.setBadgeTextColor) {
    chrome.action.setBadgeTextColor({ tabId, color: '#FFFFFF' }).catch(() => {});
  }
  chrome.action
    .setTitle({
      tabId,
      title: `Last updated ${LLU.formatDate(value, { dateOnly })} (${LLU.relative(value)})${revLine}\nWriter: ${writer}${alias}`,
    })
    .catch(() => {});
}

async function cached(key, ttl, missTtl, loader) {
  const hit = (await chrome.storage.local.get(key))[key];
  if (hit && Date.now() - hit.at < (hit.miss ? missTtl : ttl)) return { value: hit.value, cached: true };
  if (inflight.has(key)) return inflight.get(key);
  const p = (async () => {
    const res = await loader();
    if (res.value !== undefined) {
      await chrome.storage.local.set({ [key]: { at: Date.now(), value: res.value, miss: res.value === null } });
    }
    return res;
  })().finally(() => inflight.delete(key));
  inflight.set(key, p);
  return p;
}

async function gh(path) {
  const { ghBlockedUntil = 0 } = await chrome.storage.local.get('ghBlockedUntil');
  if (Date.now() < ghBlockedUntil) return { error: 'rate-limited', until: ghBlockedUntil };
  let res;
  try {
    res = await fetch(`https://api.github.com${path}`, {
      headers: { Accept: 'application/vnd.github+json' },
    });
  } catch {
    return { error: 'network' };
  }
  if (res.status === 403 || res.status === 429) {
    if (res.status === 429 || res.headers.get('x-ratelimit-remaining') === '0') {
      const reset = Number(res.headers.get('x-ratelimit-reset')) * 1000;
      const until = reset > Date.now() ? reset : Date.now() + 15 * 60000;
      await chrome.storage.local.set({ ghBlockedUntil: until });
      return { error: 'rate-limited', until };
    }
    return { error: 'forbidden' };
  }
  if (res.status === 404 || res.status === 409) return { status: 404 };
  if (!res.ok) return { error: `http-${res.status}` };
  return { data: await res.json() };
}

async function githubUser(login) {
  if (!/^[A-Za-z0-9-]{1,39}$/.test(login || '')) return { error: 'invalid' };
  return cached(`user:${login.toLowerCase()}`, USER_TTL, MISS_TTL, async () => {
    const r = await gh(`/users/${encodeURIComponent(login)}`);
    if (r.status === 404) return { value: null };
    if (r.error) return r;
    const u = r.data;
    return {
      value: {
        login: u.login,
        name: u.name || '',
        avatar: u.avatar_url || '',
        url: u.html_url,
        company: u.company || '',
        type: u.type || 'User',
      },
    };
  });
}

async function latestCommit(repo) {
  if (!repo || !repo.owner || !repo.repo || !repo.path) return { error: 'invalid' };
  const key = `commit:${repo.owner}/${repo.repo}@${repo.branch}:${repo.path}`.toLowerCase();
  return cached(key, COMMIT_TTL, COMMIT_TTL, async () => {
    const q = new URLSearchParams({ path: repo.path, per_page: '1' });
    if (repo.branch) q.set('sha', repo.branch);
    const r = await gh(`/repos/${encodeURIComponent(repo.owner)}/${encodeURIComponent(repo.repo)}/commits?${q}`);
    if (r.status === 404) return { value: null };
    if (r.error) return r;
    const c = Array.isArray(r.data) ? r.data[0] : null;
    if (!c) return { value: null };
    return {
      value: {
        sha: c.sha,
        url: c.html_url,
        date: (c.commit.committer && c.commit.committer.date) || (c.commit.author && c.commit.author.date),
        authorName: (c.commit.author && c.commit.author.name) || '',
        authorLogin: (c.author && c.author.login) || '',
        message: (c.commit.message || '').split('\n')[0],
      },
    };
  });
}

async function pruneCache() {
  const all = await chrome.storage.local.get(null);
  const now = Date.now();
  const stale = Object.entries(all)
    .filter(([k, v]) => (k.startsWith('user:') || k.startsWith('commit:')) && v && now - v.at > USER_TTL)
    .map(([k]) => k);
  if (stale.length) await chrome.storage.local.remove(stale);
}

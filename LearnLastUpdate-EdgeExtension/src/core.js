// Shared helpers for the content script, popup and service worker.
(function (root) {
  if (root.LLU) return;

  const DAY = 86400000;
  const FRESH_DAYS = 182;
  const AGING_DAYS = 365;
  // Normal review-to-publish lag is about a week; beyond this, a later publish likely carries unflagged edits.
  const REPUBLISH_GAP_DAYS = 14;
  const DEFAULT_SETTINGS = { showCard: true, githubLookups: true };
  const LEARN_URL = /^https:\/\/(review\.)?learn\.microsoft\.com\//i;
  // Learn app pages (search, profile, browse, Q&A, home) carry site-level metadata, not article metadata.
  const NON_ARTICLE_TYPES = new Set(['search', 'profile', 'browse', 'qna', 'docs', 'dashboard']);

  function extract(doc) {
    doc = doc || document;
    const meta = (name) => {
      const el = doc.querySelector(`meta[name="${name}"]`);
      return el && el.content ? el.content.trim() : '';
    };
    const metaAll = (name) =>
      [...doc.querySelectorAll(`meta[name="${name}"]`)]
        .flatMap((m) => (m.content || '').split(','))
        .map((s) => s.trim())
        .filter(Boolean);

    const shown = doc.querySelector(
      '.page-metadata local-time[datetime], #article-metadata-footer local-time[datetime], local-time[data-article-date-source][datetime]'
    );
    const shownDate = shown ? shown.getAttribute('datetime') : '';
    const msDate = meta('ms.date');
    const updatedAt = meta('updated_at');

    let primary = null;
    if (validDate(shownDate)) primary = { value: shownDate, source: 'learn', dateOnly: false };
    else if (validDate(msDate)) primary = { value: msDate, source: 'ms.date', dateOnly: true };
    else if (validDate(updatedAt)) primary = { value: updatedAt, source: 'updated_at', dateOnly: false };

    const h1 = doc.querySelector('main h1, #main h1, h1');
    const ogTitle = doc.querySelector('meta[property="og:title"]');
    const title = (h1 && h1.textContent.trim()) || (ogTitle && ogTitle.content) || doc.title || '';

    const info = {
      url: doc.location ? doc.location.href : '',
      title,
      pageType: meta('page_type'),
      locale: meta('locale'),
      service: meta('ms.service'),
      topic: meta('ms.topic'),
      primary,
      shownDate: validDate(shownDate) ? shownDate : '',
      msDate: validDate(msDate) ? msDate : '',
      updatedAt: validDate(updatedAt) ? updatedAt : '',
      author: meta('author'),
      msAuthor: meta('ms.author'),
      manager: meta('manager'),
      reviewers: [...new Set(metaAll('ms.reviewer'))],
      sourceUrl: meta('original_content_git_url'),
      publicSourceUrl: meta('github_feedback_content_git_url'),
      commitId: meta('git_commit_id'),
    };
    info.hasArticle = Boolean(
      info.primary && (info.author || info.msAuthor) && !NON_ARTICLE_TYPES.has(info.pageType.toLowerCase())
    );
    info.republished = republished(info);
    return info;
  }

  function validDate(v) {
    return Boolean(v) && !Number.isNaN(Date.parse(v));
  }

  // updated_at is stamped on every publish, while writers only bump ms.date for substantial edits,
  // so a publish well after the last-updated date means the text may have changed without a new date.
  function republished(info, gapDays) {
    if (!info || !info.primary || info.primary.source === 'updated_at' || !validDate(info.updatedAt)) return null;
    const days = Math.floor((Date.parse(info.updatedAt) - Date.parse(info.primary.value)) / DAY);
    return days > (gapDays == null ? REPUBLISH_GAP_DAYS : gapDays) ? { value: info.updatedAt, days } : null;
  }

  function republishedTitle(rev) {
    return (
      `Learn republished this page on ${formatDate(rev.value, { time: true })} (updated_at), ` +
      `${rev.days} days after the last-updated date. Writers only change that date for substantial edits, ` +
      'so smaller changes can go live without it.'
    );
  }

  function daysSince(value, now) {
    return Math.max(0, Math.floor(((now || Date.now()) - Date.parse(value)) / DAY));
  }

  function freshness(value, now) {
    const d = daysSince(value, now);
    if (d <= FRESH_DAYS) return { level: 'fresh', label: 'Fresh', color: '#1E7B34' };
    if (d <= AGING_DAYS) return { level: 'aging', label: 'Aging', color: '#A86A00' };
    return { level: 'stale', label: 'Stale', color: '#B7410E' };
  }

  // Date-only values (ms.date) are stored as UTC midnight; formatting them in local
  // time would shift them to the previous day west of UTC.
  function formatDate(value, opts) {
    opts = opts || {};
    if (!validDate(value)) return '';
    const o = { dateStyle: 'medium' };
    if (opts.time) o.timeStyle = 'short';
    if (opts.dateOnly) o.timeZone = 'UTC';
    return new Intl.DateTimeFormat(undefined, o).format(new Date(value));
  }

  function relative(value, now) {
    if (!validDate(value)) return '';
    const diff = Date.parse(value) - (now || Date.now());
    const abs = Math.abs(diff);
    const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
    if (abs < DAY) return 'today';
    if (abs < 7 * DAY) return rtf.format(Math.round(diff / DAY), 'day');
    if (abs < 30 * DAY) return rtf.format(Math.round(diff / (7 * DAY)), 'week');
    if (abs < 365 * DAY) return rtf.format(Math.round(diff / (30.44 * DAY)), 'month');
    const years = diff / (365.25 * DAY);
    return rtf.format(Math.abs(years) < 2 ? Math.round(years * 10) / 10 : Math.round(years), 'year');
  }

  function badgeText(value, now) {
    const d = daysSince(value, now);
    if (d < 1) return 'new';
    if (d < 7) return `${d}d`;
    if (d < 30) return `${Math.round(d / 7)}w`;
    if (d < 365) return `${Math.max(1, Math.round(d / 30.44))}mo`;
    return `${Math.floor(d / 365.25)}y`;
  }

  function parseGitHub(url) {
    const m = /^https:\/\/github\.com\/([^/]+)\/([^/]+)\/blob\/([^/]+)\/(.+)$/i.exec(url || '');
    if (!m) return null;
    const [, owner, repo, branch, path] = m;
    const base = `https://github.com/${owner}/${repo}`;
    return {
      owner,
      repo,
      branch,
      path: decodeURIComponent(path),
      fileUrl: url,
      historyUrl: `${base}/commits/${branch}/${path}`,
      repoUrl: base,
    };
  }

  function isLearnUrl(url) {
    return LEARN_URL.test(url || '');
  }

  function githubProfile(login) {
    return `https://github.com/${encodeURIComponent(login)}`;
  }

  function avatarUrl(login, size) {
    return `https://github.com/${encodeURIComponent(login)}.png?size=${size || 64}`;
  }

  root.LLU = {
    DEFAULT_SETTINGS,
    REPUBLISH_GAP_DAYS,
    extract,
    republished,
    republishedTitle,
    freshness,
    formatDate,
    relative,
    badgeText,
    daysSince,
    parseGitHub,
    isLearnUrl,
    githubProfile,
    avatarUrl,
  };
})(typeof globalThis !== 'undefined' ? globalThis : self);

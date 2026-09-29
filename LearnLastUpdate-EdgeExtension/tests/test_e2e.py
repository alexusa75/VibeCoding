import asyncio
import json
import pathlib
import sys
import tempfile

from playwright.async_api import async_playwright

EXT = str(pathlib.Path(__file__).resolve().parent.parent)
OUT = str(pathlib.Path(__file__).resolve().parent / "output")
pathlib.Path(OUT).mkdir(exist_ok=True)
HOST = "#llu-last-update-card"

PAGES = {
    "conceptual": "https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview",
    "training": "https://learn.microsoft.com/en-us/training/modules/intro-to-azure-fundamentals/",
    "api": "https://learn.microsoft.com/en-us/dotnet/api/system.string?view=net-8.0",
    "localized": "https://learn.microsoft.com/es-es/azure/virtual-machines/overview",
    "stale": "https://learn.microsoft.com/en-us/powershell/module/exchange/get-mailbox?view=exchange-ps",
    "m365": "https://learn.microsoft.com/en-us/microsoft-365/admin/add-users/add-users?view=o365-worldwide",
    "hub": "https://learn.microsoft.com/en-us/intune/",
}
REPUBLISHED = "https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-add-other-agents"
EXPECTED_REV_JS = """() => { const l = document.querySelector('.page-metadata local-time[datetime], #article-metadata-footer local-time[datetime], local-time[data-article-date-source][datetime]');
    const m = (n) => (document.querySelector(`meta[name="${n}"]`) || {}).content || '';
    const p = (l && l.getAttribute('datetime')) || m('ms.date'); const u = m('updated_at');
    if (!p || !u) return false; return Math.floor((Date.parse(u) - Date.parse(p)) / 86400000) > 14; }"""
NON_ARTICLE = "https://learn.microsoft.com/en-us/search/?terms=intune"
NON_LEARN = "https://example.com/"

results = []
errors = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def watch(page, label):
    def on_console(m):
        if m.type == "error":
            txt = m.text
            loc = (m.location or {}).get("url", "")
            if "chrome-extension://" in loc or "chrome-extension://" in txt or label.startswith("popup"):
                errors.append(f"{label}: console error: {txt} @ {loc}")

    page.on("console", on_console)
    page.on("pageerror", lambda e: errors.append(f"{label}: pageerror: {e}") if ("chrome-extension" in str(e.stack or "") or label.startswith("popup")) else None)


async def card_text(page):
    return await page.evaluate(
        f"""() => {{ const h = document.querySelector('{HOST}'); if (!h) return null;
        const c = h.shadowRoot.querySelector('.card');
        return {{ text: c.innerText.replace(/\\s+/g,' ').trim(), level: c.dataset.level, theme: c.dataset.theme,
                 date: c.querySelector('time').textContent, datetime: c.querySelector('time').getAttribute('datetime'),
                 name: (c.querySelector('.name')||{{}}).textContent, rev: (c.querySelector('.rev')||{{}}).textContent || null,
                 prev: h.previousElementSibling && (h.previousElementSibling.tagName + '.' + h.previousElementSibling.className) }}; }}"""
    )


async def tab_id_for(sw, url):
    return await sw.evaluate(
        """async (u) => { const tabs = await chrome.tabs.query({}); const t = tabs.find(t => t.url === u || (t.url||'').startsWith(u)); return t ? t.id : null; }""",
        url,
    )


async def badge(sw, tid):
    return await sw.evaluate(
        """async (id) => ({ text: await chrome.action.getBadgeText({tabId:id}), title: await chrome.action.getTitle({tabId:id}),
                            color: await chrome.action.getBadgeBackgroundColor({tabId:id}) })""",
        tid,
    )


async def open_popup(ctx, ext_id, tid, dark=False, label="popup"):
    pp = await ctx.new_page()
    watch(pp, label)
    await pp.set_viewport_size({"width": 368, "height": 700})
    if dark:
        await pp.emulate_media(color_scheme="dark")
    await pp.goto(f"chrome-extension://{ext_id}/popup/popup.html?tabId={tid}")
    await pp.wait_for_function("() => document.getElementById('sheet').dataset.state !== 'loading'", timeout=15000)
    return pp


async def main(channel):
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            tempfile.mkdtemp(prefix="llu-"),
            channel=channel,
            headless=True,
            args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"],
            viewport={"width": 1280, "height": 900},
        )
        sw = None
        for _ in range(40):
            sw = next((w for w in ctx.service_workers if w.url.endswith("/src/background.js")), None)
            if sw:
                break
            await asyncio.sleep(0.5)
        assert sw, "extension service worker not found: " + str([w.url for w in ctx.service_workers])
        sw.on("console", lambda m: errors.append(f"sw: {m.text}") if m.type == "error" else None)
        ext_id = sw.url.split("/")[2]
        print("channel", channel, "extension id", ext_id)

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        watch(page, "learn")

        # --- A. conceptual article --------------------------------------------------------
        url = PAGES["conceptual"]
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_selector(HOST, state="attached", timeout=20000)
        expected = await page.evaluate("""() => { const l = document.querySelector('local-time[data-article-date-source]');
            return { dt: l && l.getAttribute('datetime'), author: document.querySelector('meta[name=author]').content,
                     fmt: l && new Intl.DateTimeFormat(undefined,{dateStyle:'medium'}).format(new Date(l.getAttribute('datetime'))) }; }""")
        c = await card_text(page)
        check("card: rendered on conceptual article", c is not None, c and c["text"])
        check("card: date equals Learn's displayed date", c and c["datetime"] == expected["dt"] and c["date"] == expected["fmt"], f"{c and c['date']} vs {expected['fmt']}")
        check("card: shows GitHub author", c and f"@{expected['author']}" in c["text"])
        check("card: inserted right after H1", c and c["prev"].startswith("H1"), c and c["prev"])
        await page.wait_for_timeout(2500)
        c2 = await card_text(page)
        check("card: GitHub display name resolved", c2 and c2["name"] and c2["name"] != expected["author"], c2 and c2["name"])

        tid = await tab_id_for(sw, url)
        b = await badge(sw, tid)
        check("badge: age text set", b["text"] and b["text"] != "", json.dumps(b))
        check("badge: tooltip includes writer", expected["author"] in b["title"])

        host = page.locator(HOST)
        await host.scroll_into_view_if_needed()
        await page.screenshot(path=f"{OUT}\\shot-card-light.png", clip=await card_clip(page))

        # dark theme follows Learn's theme class
        await page.evaluate("() => { const c = document.documentElement.classList; c.remove('theme-light'); c.add('theme-dark'); }")
        await page.wait_for_timeout(300)
        c3 = await card_text(page)
        check("card: follows Learn dark theme", c3 and c3["theme"] == "dark", c3 and c3["theme"])
        await page.screenshot(path=f"{OUT}\\shot-card-dark.png", clip=await card_clip(page))
        await page.evaluate("() => { const c = document.documentElement.classList; c.remove('theme-dark'); c.add('theme-light'); }")

        # --- popup for that tab ------------------------------------------------------------
        pp = await open_popup(ctx, ext_id, tid)
        state = await pp.evaluate("document.getElementById('sheet').dataset.state")
        check("popup: ready state", state == "ready", state)
        await pp.wait_for_function("() => !document.querySelector('.row dd.pending')", timeout=15000)
        await pp.wait_for_timeout(600)
        pinfo = await pp.evaluate("""() => ({ big: document.getElementById('bigDate').textContent, stamp: document.getElementById('stamp').textContent,
            name: document.getElementById('writerName').textContent, handles: document.getElementById('handles').innerText,
            chips: [...document.querySelectorAll('#writerActions a')].map(a => a.textContent + ' ' + a.href),
            ledger: [...document.querySelectorAll('#ledger .row')].map(r => r.innerText.replace(/\\s+/g,' ')),
            note: (document.querySelector('.row-note')||{}).textContent || '',
            links: [...document.querySelectorAll('#links a')].map(a => a.textContent + ' ' + a.href) })""")
        print(json.dumps(pinfo, indent=1))
        check("popup: big date matches card", pinfo["big"] == c["date"], pinfo["big"])
        check("popup: writer name resolved", pinfo["name"] == c2["name"], pinfo["name"])
        check("popup: email + Teams chips", any("mailto:" in x for x in pinfo["chips"]) and any("teams.microsoft.com" in x for x in pinfo["chips"]))
        check("popup: ledger has ms.date + updated_at rows", any("ms.date" in r for r in pinfo["ledger"]) and any("updated_at" in r for r in pinfo["ledger"]))
        commit_row = next((r for r in pinfo["ledger"] if "Last commit" in r), "")
        check("popup: latest GitHub commit resolved", commit_row and "checking" not in commit_row and "unavailable" not in commit_row, commit_row)
        check("popup: history link", any("/commits/" in x for x in pinfo["links"]))
        exp_rev = await page.evaluate(EXPECTED_REV_JS)
        rev_shown = await pp.evaluate("!document.getElementById('revNote').hidden")
        check("conceptual: republished hint matches metadata", rev_shown == exp_rev and bool(c["rev"]) == exp_rev, f"expected={exp_rev} popup={rev_shown} card={c['rev']}")
        logic = await pp.evaluate("""() => { const P = (d) => ({ value: d, source: 'ms.date' });
            return [ LLU.republished({ primary: P('2026-05-15T00:00:00Z'), updatedAt: '2026-05-22T07:07:00Z' }),
                     LLU.republished({ primary: P('2026-05-15T00:00:00Z'), updatedAt: '2026-08-27T01:03:00Z' }),
                     LLU.republished({ primary: { value: '2026-08-27T01:03:00Z', source: 'updated_at' }, updatedAt: '2026-08-27T01:03:00Z' }),
                     LLU.republished({ primary: P('2026-05-15T00:00:00Z'), updatedAt: '' }),
                     LLU.republished({ primary: P('2026-08-27T00:00:00Z'), updatedAt: '2026-05-01T00:00:00Z' }) ]; }""")
        check("logic: 7-day publish lag is not flagged", logic[0] is None, str(logic[0]))
        check("logic: 104-day gap is flagged", logic[1] and logic[1]["days"] == 104 and logic[1]["value"] == "2026-08-27T01:03:00Z", str(logic[1]))
        check("logic: no hint when date already comes from updated_at / missing / earlier", logic[2] is None and logic[3] is None and logic[4] is None, str(logic[2:]))
        await pp.screenshot(path=f"{OUT}\\shot-popup-light.png", full_page=True)

        await pp.bring_to_front()
        await pp.click("#copyBtn")
        await pp.wait_for_timeout(150)
        btn = await pp.text_content("#copyBtn")
        check("popup: copy writes to real clipboard", btn == "Copied", btn)
        await pp.wait_for_timeout(1600)
        await pp.evaluate("navigator.clipboard.writeText = (t) => { window.__copied = t; return Promise.resolve(); }")
        await pp.click("#copyBtn")
        clip = await pp.evaluate("window.__copied || ''")
        check("popup: copy summary content", "Last updated:" in clip and "Ken Withee" in clip and url in clip, clip.replace("\n", " | "))

        # toggle card off/on from popup
        await pp.uncheck("#optCard")
        await page.wait_for_timeout(500)
        check("toggle: card hidden when disabled", await page.locator(HOST).count() == 0)
        await pp.check("#optCard")
        await page.wait_for_timeout(500)
        check("toggle: card back when enabled", await page.locator(HOST).count() == 1)

        # dismiss on page, then persist across reload, then restore via toggle
        await page.evaluate(f"() => document.querySelector('{HOST}').shadowRoot.querySelector('.x').click()")
        await page.wait_for_timeout(200)
        check("dismiss: × hides card", await page.locator(HOST).count() == 0)
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
        check("dismiss: stays hidden after reload (session)", await page.locator(HOST).count() == 0)
        await pp.close()
        pp = await open_popup(ctx, ext_id, tid)
        await pp.uncheck("#optCard")
        await pp.check("#optCard")
        await page.wait_for_timeout(600)
        check("dismiss: re-enabled from popup", await page.locator(HOST).count() == 1)

        # GitHub lookups off: no avatar requests to github.com, initials instead
        gh_reqs = []
        page.on("request", lambda r: gh_reqs.append(r.url) if "github.com" in r.url else None)
        await pp.uncheck("#optGh")
        await page.wait_for_timeout(400)
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_selector(HOST, state="attached", timeout=20000)
        await page.wait_for_timeout(2000)
        av = await page.evaluate(f"() => {{ const r = document.querySelector('{HOST}').shadowRoot; return {{ img: !!r.querySelector('img.av'), initials: (r.querySelector('.initials')||{{}}).textContent || '' }}; }}")
        check("lookups off: card shows initials, no avatar", not av["img"] and av["initials"], json.dumps(av))
        check("lookups off: page makes no github.com requests", not gh_reqs, str(gh_reqs[:3]))
        await pp.close()
        pp = await open_popup(ctx, ext_id, tid, label="popup-lookups-off")
        pav = await pp.evaluate("() => ({ img: !!document.querySelector('#avWrap img'), initials: (document.querySelector('#avWrap .initials')||{}).textContent || '', commit: ([...document.querySelectorAll('#ledger .row')].find(r => r.innerText.includes('Last commit'))||{}).innerText || '' })")
        check("lookups off: popup shows initials and 'lookups off'", not pav["img"] and pav["initials"] and "lookups off" in pav["commit"], json.dumps(pav))
        await pp.check("#optGh")
        await page.wait_for_timeout(400)
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_selector(HOST, state="attached", timeout=20000)
        await page.wait_for_function(f"() => {{ const i = document.querySelector('{HOST}').shadowRoot.querySelector('img.av'); return i && i.complete && i.naturalWidth > 0; }}", timeout=15000)
        check("lookups on again: avatar restored", True)
        await pp.close()

        pp = await open_popup(ctx, ext_id, tid, dark=True, label="popup-dark")
        await pp.wait_for_function("() => !document.querySelector('.row dd.pending')", timeout=15000)
        await pp.wait_for_timeout(700)
        await pp.screenshot(path=f"{OUT}\\shot-popup-dark.png", full_page=True)
        await pp.close()

        # --- B..G other page types ---------------------------------------------------------
        for key in ("training", "api", "localized", "stale", "m365", "hub"):
            u = PAGES[key]
            await page.goto(u, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector(HOST, state="attached", timeout=20000)
            except Exception:
                pass
            c = await card_text(page)
            tid2 = await tab_id_for(sw, page.url)
            b = await badge(sw, tid2) if tid2 else {}
            check(f"{key}: card rendered", c is not None, c and f"{c['text']} | level={c['level']} | after={c['prev']}")
            check(f"{key}: badge set", b.get("text"), b.get("text"))
            exp_rev = await page.evaluate(EXPECTED_REV_JS)
            check(f"{key}: republished hint matches metadata", c and bool(c["rev"]) == exp_rev and (("Republished" in b.get("title", "")) == exp_rev), f"expected={exp_rev} card={c and c['rev']}")
            if key in ("training", "stale"):
                await page.screenshot(path=f"{OUT}\\shot-card-{key}.png", clip=await card_clip(page))
            if key == "stale":
                check("stale: freshness level is stale", c and c["level"] == "stale", c and c["level"])
            if key == "training":
                pp = await open_popup(ctx, ext_id, tid2, label="popup-training")
                await pp.wait_for_timeout(1500)
                await pp.screenshot(path=f"{OUT}\\shot-popup-training.png", full_page=True)
                await pp.close()

        # --- republished after the last-updated date (Copilot Studio) ------------------------
        await page.goto(REPUBLISHED, wait_until="domcontentloaded")
        await page.wait_for_selector(HOST, state="attached", timeout=20000)
        c = await card_text(page)
        pub = await page.evaluate("() => new Intl.DateTimeFormat(undefined,{dateStyle:'medium'}).format(new Date(document.querySelector('meta[name=updated_at]').content))")
        check("republished: card shows hint", c and c["rev"] and f"Republished {pub}" in c["rev"] and "may have changed" in c["rev"], c and c["rev"])
        geo = await page.evaluate(f"""() => {{ const r = document.querySelector('{HOST}').shadowRoot; const card = r.querySelector('.card').getBoundingClientRect();
            const rev = r.querySelector('.rev').getBoundingClientRect(); const x = r.querySelector('.x').getBoundingClientRect(); const d = r.querySelector('.date').getBoundingClientRect();
            return {{ revFull: rev.width > card.width * 0.85, revBelow: rev.top >= d.bottom - 1, xTop: x.top - card.top, xOverlapsRev: x.bottom > rev.top }}; }}""")
        check("republished: hint on its own line, × stays top-right", geo["revFull"] and geo["revBelow"] and not geo["xOverlapsRev"], json.dumps(geo))
        await page.locator(HOST).scroll_into_view_if_needed()
        await page.screenshot(path=f"{OUT}\\shot-card-republished.png", clip=await card_clip(page))
        await page.evaluate("() => { const c = document.documentElement.classList; c.remove('theme-light'); c.add('theme-dark'); }")
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{OUT}\\shot-card-republished-dark.png", clip=await card_clip(page))
        await page.evaluate("() => { const c = document.documentElement.classList; c.remove('theme-dark'); c.add('theme-light'); }")
        tid5 = await tab_id_for(sw, REPUBLISHED)
        b = await badge(sw, tid5)
        check("republished: badge tooltip mentions it", f"Republished {pub}" in b["title"], b["title"].replace("\n", " | "))
        for dark in (False, True):
            pp = await open_popup(ctx, ext_id, tid5, dark=dark, label="popup-republished")
            await pp.wait_for_timeout(900)
            r = await pp.evaluate("""() => { const n = document.getElementById('revNote'); const pub = [...document.querySelectorAll('#ledger .row')].find(x => x.innerText.includes('Published'));
                return { hidden: n.hidden, display: getComputedStyle(n).display, text: n.innerText.replace(/\\s+/g,' '), title: n.title,
                         mark: !!(pub && pub.querySelector('.rev-mark')), pubTitle: pub && pub.querySelector('dd').title }; }""")
            if not dark:
                check("republished: popup note visible", not r["hidden"] and r["display"] != "none" and f"Republished {pub}" in r["text"], r["text"])
                check("republished: popup tooltip explains", "updated_at" in r["title"] and "substantial" in r["title"], r["title"])
                check("republished: ledger Published row flagged", r["mark"] and "substantial" in (r["pubTitle"] or ""))
                await pp.evaluate("navigator.clipboard.writeText = (t) => { window.__copied = t; return Promise.resolve(); }")
                await pp.click("#copyBtn")
                clip = await pp.evaluate("window.__copied || ''")
                check("republished: copy summary includes it", f"Republished: {pub}" in clip, clip.replace("\n", " | "))
            await pp.screenshot(path=f"{OUT}\\shot-popup-republished{'-dark' if dark else ''}.png", full_page=True)
            await pp.close()
        await page.goto(NON_ARTICLE, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        check("non-article: no card", await page.locator(HOST).count() == 0)
        tid3 = await tab_id_for(sw, page.url)
        b = await badge(sw, tid3)
        check("non-article: badge cleared", b["text"] == "", json.dumps(b))
        pp = await open_popup(ctx, ext_id, tid3, label="popup-nonarticle")
        t = await pp.evaluate("[document.getElementById('sheet').dataset.state, document.querySelector('.empty-title').textContent]")
        check("non-article: popup explains", t[0] == "empty" and "metadata" in t[1], str(t))
        await pp.close()

        # non-Learn page
        await page.goto(NON_LEARN)
        tid4 = await sw.evaluate("async () => (await chrome.tabs.query({})).find(t => !t.url || !t.url.startsWith('chrome-extension'))?.id")
        pp = await open_popup(ctx, ext_id, tid4, label="popup-nonlearn")
        t = await pp.evaluate("[document.getElementById('sheet').dataset.state, document.querySelector('.empty-title').textContent]")
        check("non-Learn: popup shows empty state", t[0] == "empty" and t[1] == "Not a Learn article", str(t))
        await pp.screenshot(path=f"{OUT}\\shot-popup-empty.png", full_page=True)
        await pp.close()

        await ctx.close()


async def card_clip(page):
    box = await page.locator(HOST).bounding_box()
    h1 = await page.locator("main h1, #main h1, h1").first.bounding_box()
    top = min(box["y"], h1["y"]) - 12
    return {"x": max(0, box["x"] - 16), "y": max(0, top), "width": min(1000, box["width"] + 32), "height": box["y"] + box["height"] - top + 14}


if __name__ == "__main__":
    ch = sys.argv[1] if len(sys.argv) > 1 else "msedge"
    asyncio.run(main(ch))
    print("\n==== SUMMARY")
    fails = [r for r in results if not r[1]]
    print(f"{len(results) - len(fails)}/{len(results)} passed")
    for r in fails:
        print("FAIL", r[0], r[2])
    print("extension console errors:", len(errors))
    for e in errors:
        print("  ", e)
    sys.exit(1 if fails or errors else 0)

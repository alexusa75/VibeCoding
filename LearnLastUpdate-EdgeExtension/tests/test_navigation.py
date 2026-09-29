import asyncio
import pathlib
import sys
import tempfile

from playwright.async_api import async_playwright

EXT = str(pathlib.Path(__file__).resolve().parent.parent)
HOST = "#llu-last-update-card"
errors = []
failed = []


def report(status, *args):
    print(status, *args)
    if status != "PASS":
        failed.append(args[0] if args else "?")


async def find_sw(ctx):
    for _ in range(40):
        sw = next((w for w in ctx.service_workers if w.url.endswith("/src/background.js")), None)
        if sw:
            return sw
        await asyncio.sleep(0.5)
    raise RuntimeError("no sw")


async def card(page):
    return await page.evaluate(f"""() => {{ const h = document.querySelector('{HOST}'); if (!h) return null;
        const c = h.shadowRoot.querySelector('.card'); return c.querySelector('time').textContent + ' | ' + c.querySelector('.handle, .name').textContent; }}""")


async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            tempfile.mkdtemp(prefix="llu2-"), channel="msedge", headless=True,
            args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"], viewport={"width": 1280, "height": 900})
        sw = await find_sw(ctx)
        ext_id = sw.url.split("/")[2]
        page = ctx.pages[0]
        page.on("pageerror", lambda e: errors.append(f"pageerror {e}") if "chrome-extension" in str(e.stack or "") else None)

        # 1) navigate via a TOC link (Learn in-site navigation)
        await page.goto("https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview", wait_until="domcontentloaded")
        await page.wait_for_selector(HOST, state="attached")
        before = await card(page)
        href = await page.evaluate("""() => { const a = [...document.querySelectorAll('main .content p a[href], main .content li a[href]')].find(a => a.href.startsWith('https://learn.microsoft.com/en-us/entra/') && !a.href.includes('#') && a.pathname !== location.pathname && a.offsetParent);
            if (a) a.setAttribute('data-llu-test', '1'); return a && a.href; }""")
        link = page.locator("[data-llu-test='1']").first
        await link.click()
        await page.wait_for_url(lambda u: u.split("?")[0] != "https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview", timeout=20000)
        await page.wait_for_selector(HOST, state="attached", timeout=20000)
        await page.wait_for_timeout(1500)
        after = await card(page)
        shown = await page.evaluate("() => { const l = document.querySelector('local-time[data-article-date-source]'); return l && new Intl.DateTimeFormat(undefined,{dateStyle:'medium'}).format(new Date(l.getAttribute('datetime'))); }")
        count = await page.locator(HOST).count()
        ok = after and after.split(" | ")[0] == shown and count == 1
        report(("PASS" if ok else "FAIL"), "navigation: card reflects new article", f"[{before}] -> [{after}] shown={shown} cards={count} href={href}")

        # 2) extension reload -> orphaned content script; popup must re-inject
        await sw.evaluate("chrome.runtime.reload()")
        await asyncio.sleep(2)
        sw2 = None
        for _ in range(40):
            sw2 = next((w for w in ctx.service_workers if w.url.endswith("/src/background.js") and w != sw), None)
            if sw2:
                break
            await asyncio.sleep(0.5)
        report("PASS" if sw2 else "FAIL", "reload: new service worker")
        tid = await sw2.evaluate("async (u) => (await chrome.tabs.query({})).find(t => t.url === u)?.id", page.url)
        pp = await ctx.new_page()
        pp.on("console", lambda m: errors.append(f"popup {m.text}") if m.type == "error" else None)
        pp.on("pageerror", lambda e: errors.append(f"popup pageerror {e}"))
        await pp.goto(f"chrome-extension://{ext_id}/popup/popup.html?tabId={tid}")
        await pp.wait_for_function("() => document.getElementById('sheet').dataset.state !== 'loading'", timeout=15000)
        state = await pp.evaluate("[document.getElementById('sheet').dataset.state, document.getElementById('bigDate').textContent]")
        report("PASS" if state[0] == "ready" and state[1] == shown else "FAIL", "reload: popup re-injects and reads page", state)
        await page.wait_for_timeout(800)
        cnt = await page.locator(HOST).count()
        report("PASS" if cnt == 1 else "FAIL", "reload: exactly one card after re-injection", cnt)
        b = await sw2.evaluate("async (id) => chrome.action.getBadgeText({tabId:id})", tid)
        report("PASS" if b else "FAIL", "reload: badge restored", b)
        await ctx.close()
    print("extension errors:", errors)


if __name__ == "__main__":
    asyncio.run(main())
    print(f"failed: {len(failed)}")
    sys.exit(1 if failed or errors else 0)

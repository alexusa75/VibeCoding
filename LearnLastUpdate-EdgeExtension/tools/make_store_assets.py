"""Generates the Partner Center listing images in store/:
logo-300.png, tile-small-440x280.png, tile-large-1400x560.png and four 1280x800 screenshots.

Run: python tools/make_store_assets.py   (needs Pillow, Playwright and Microsoft Edge)
Screenshots are taken of the real extension running on live Learn pages.
"""
import asyncio
import base64
import io
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_icons import draw  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "store"
HOST = "#llu-last-update-card"
DPR = 2
HERO = "https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-add-other-agents"
AGING = "https://learn.microsoft.com/en-us/microsoft-365/admin/add-users/add-users?view=o365-worldwide"
STALE = "https://learn.microsoft.com/en-us/powershell/module/exchange/get-mailbox?view=exchange-ps"

BASE_CSS = """
:root {
  --serif: "Sitka Heading", "Sitka Text", Sitka, Georgia, serif;
  --display: "Sitka Display", "Sitka Heading", Sitka, Georgia, serif;
  --label: "Bahnschrift SemiCondensed", Bahnschrift, "Segoe UI", sans-serif;
  --paper: #F8F5EC; --paper-2: #EFE9DA; --ink: #1C2127; --muted: #5C636C; --faint: #8A9099;
  --edge: #E0D8C6; --blue: #0F6CBD; --green: #1E7B34; --rule: rgba(15, 108, 189, 0.09);
}
* { box-sizing: border-box; margin: 0; }
html, body { width: 100%; height: 100%; overflow: hidden; }
body { font: 400 16px/1.4 var(--label); color: var(--ink); -webkit-font-smoothing: antialiased; }
.paper {
  position: relative; width: 100%; height: 100%; overflow: hidden;
  background:
    linear-gradient(var(--blue), var(--blue)) 0 0 / 100% 4px no-repeat,
    linear-gradient(var(--blue), var(--blue)) 0 7px / 100% 1.5px no-repeat,
    repeating-linear-gradient(180deg, transparent 0 27px, var(--rule) 27px 28px),
    var(--paper);
}
.paper::before {
  content: ""; position: absolute; inset: 0; opacity: .05; pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
.kicker { color: var(--blue); font: 700 13px/1 var(--label); letter-spacing: .24em; text-transform: uppercase; }
.stamp {
  display: inline-block; color: var(--green); font: 700 20px/1 var(--label); letter-spacing: .2em; text-transform: uppercase;
  padding: 11px 11px 10px 15px; border: 2.5px solid currentColor; border-radius: 6px;
  box-shadow: inset 0 0 0 2.5px var(--paper), inset 0 0 0 4.5px currentColor; transform: rotate(-7deg); opacity: .9;
}
.sheet { position: absolute; border-radius: 8px; box-shadow: 0 0 0 1px rgba(28,33,39,.10), 0 18px 48px -8px rgba(28,33,39,.38); }
.label {
  position: absolute; left: 28px; bottom: 28px; max-width: 640px; padding: 14px 20px 15px 18px;
  background: var(--paper); border: 1px solid var(--edge); border-left: 4px solid var(--blue); border-radius: 3px 8px 8px 3px;
  box-shadow: 0 14px 36px -12px rgba(28,33,39,.45);
}
.label b { display: block; font: 600 25px/1.15 var(--serif); color: var(--ink); }
.label span { display: block; margin-top: 6px; font: 400 16px/1.35 var(--label); color: var(--muted); }
"""


def uri(data: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(data).decode()


def shrink(data: bytes, size: tuple[int, int], path: Path) -> None:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    if img.size != size:
        img = img.resize(size, Image.LANCZOS)
    img.save(path, optimize=True)
    print(f"wrote {path.name} {img.size[0]}x{img.size[1]}")


async def render(ctx, html: str, size: tuple[int, int], name: str) -> bytes:
    pg = await ctx.new_page()
    await pg.set_viewport_size({"width": size[0], "height": size[1]})
    await pg.set_content(f"<!doctype html><html><head><style>{BASE_CSS}</style></head><body>{html}</body></html>")
    await pg.evaluate("document.fonts.ready")
    await pg.wait_for_timeout(300)
    data = await pg.screenshot()
    await pg.close()
    shrink(data, size, OUT / name)
    return data


async def open_article(ctx, sw, url: str, dark: bool = False):
    page = await ctx.new_page()
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_selector(HOST, state="attached", timeout=30000)
    await page.wait_for_function(
        f"""() => {{ const r = document.querySelector('{HOST}').shadowRoot; const n = r.querySelector('.name');
            const img = r.querySelector('img.av'); const login = (document.querySelector('meta[name=author]') || {{}}).content;
            return (!img || img.complete) && n && n.textContent !== login; }}""",
        timeout=15000,
    )
    await page.evaluate("() => window.scrollTo(0, 0)")
    # Learn's promotional banner (events, notices) changes over time and isn't part of the page.
    await page.add_style_tag(content="#banner-holder { display: none !important; }")
    if dark:
        await page.evaluate("() => { const c = document.documentElement.classList; c.remove('theme-light'); c.add('theme-dark'); }")
    await page.wait_for_timeout(1200)
    tid = await sw.evaluate(
        "async (u) => (await chrome.tabs.query({})).find(t => (t.url || '').startsWith(u.split('?')[0]))?.id", url
    )
    return page, tid


async def popup_shot(ctx, ext_id: str, tid: int, dark: bool) -> bytes:
    pp = await ctx.new_page()
    await pp.set_viewport_size({"width": 368, "height": 760})
    await pp.emulate_media(color_scheme="dark" if dark else "light")
    await pp.goto(f"chrome-extension://{ext_id}/popup/popup.html?tabId={tid}")
    await pp.wait_for_function(
        "() => document.getElementById('sheet').dataset.state === 'ready' && !document.querySelector('.row dd.pending')",
        timeout=15000,
    )
    await pp.wait_for_function("() => { const i = document.querySelector('#avWrap img'); return !i || i.complete; }")
    await pp.wait_for_timeout(1500)
    data = await pp.locator("#sheet").screenshot()
    await pp.close()
    return data


def dims(data: bytes) -> tuple[int, int]:
    w, h = Image.open(io.BytesIO(data)).size
    return w // DPR, h // DPR


def label(title: str, sub: str) -> str:
    return f'<div class="label"><b>{title}</b><span>{sub}</span></div>'


async def main() -> None:
    OUT.mkdir(exist_ok=True)
    draw().resize((300, 300), Image.LANCZOS).save(OUT / "logo-300.png")
    print("wrote logo-300.png 300x300")
    icon = uri((ROOT / "icons" / "icon128.png").read_bytes())
    big_icon = io.BytesIO()
    draw().resize((256, 256), Image.LANCZOS).save(big_icon, "PNG")
    big_icon = uri(big_icon.getvalue())

    profile = tempfile.mkdtemp(prefix="llu-store-")
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            profile,
            channel="msedge",
            headless=True,
            device_scale_factor=DPR,
            viewport={"width": 1280, "height": 800},
            args=[f"--disable-extensions-except={ROOT}", f"--load-extension={ROOT}"],
        )
        sw = None
        for _ in range(40):
            sw = next((w for w in ctx.service_workers if w.url.endswith("/src/background.js")), None)
            if sw:
                break
            await asyncio.sleep(0.5)
        if not sw:
            raise SystemExit("extension service worker not found")
        ext_id = sw.url.split("/")[2]
        for pg in list(ctx.pages):
            await pg.close()

        # 1. article card + popup
        page, tid = await open_article(ctx, sw, HERO)
        bg = await page.screenshot()
        pop_light = await popup_shot(ctx, ext_id, tid, dark=False)
        pop_dark = await popup_shot(ctx, ext_id, tid, dark=True)
        await page.close()
        pw, ph = dims(pop_light)
        await render(
            ctx,
            f"""<div class="paper" style="background:url({uri(bg)}) 0 0 / 1280px 800px">
                  <img class="sheet" src="{uri(pop_light)}" style="right:26px; top:10px; width:{pw}px; height:{ph}px">
                  {label("Last updated and who wrote it, under the title", "One click on the toolbar icon opens the full record")}
                </div>""",
            (1280, 800),
            "screenshot-1-article-and-popup.png",
        )

        # 2. aging article, dark theme, republished hint
        page, _ = await open_article(ctx, sw, AGING, dark=True)
        bg = await page.screenshot()
        await page.close()
        await render(
            ctx,
            f"""<div class="paper" style="background:url({uri(bg)}) 0 0 / 1280px 800px">
                  {label("Freshness at a glance", "Fresh, aging or stale, a hint when Learn republished the page later, and Learn's light, dark and high-contrast themes")}
                </div>""",
            (1280, 800),
            "screenshot-2-dark-theme.png",
        )

        # 3. stale reference page
        page, _ = await open_article(ctx, sw, STALE)
        bg = await page.screenshot()
        await page.close()
        await render(
            ctx,
            f"""<div class="paper" style="background:url({uri(bg)}) 0 0 / 1280px 800px">
                  {label("Old content stands out", "Works on articles, training modules, API and PowerShell reference, in every language")}
                </div>""",
            (1280, 800),
            "screenshot-3-stale-page.png",
        )

        # 4. popup showcase
        dw, dh = dims(pop_dark)
        k = 0.9
        dw, dh, sw_, sh_ = round(dw * k), round(dh * k), round(pw * k), round(ph * k)
        dark_left = 1280 - dw - 48
        light_left = dark_left - sw_ + 28
        feats = [
            ("Last updated", "the date Learn shows, the writer's review date and the last publish time"),
            ("Technical writer", "GitHub profile, Microsoft alias, one-click Email and Teams chat"),
            ("Source", "commit history and the Markdown source on GitHub"),
            ("Copy", "a ready-to-paste summary for a chat or an email"),
        ]
        items = "".join(
            f'<li><b>{t}</b><span>{d}</span></li>' for t, d in feats
        )
        await render(
            ctx,
            f"""<style>
                  .copy {{ position: absolute; left: 64px; top: 92px; width: 452px; }}
                  .copy h1 {{ margin: 18px 0 16px; font: 600 50px/1.04 var(--display); letter-spacing: -.01em; }}
                  .copy p {{ color: var(--muted); font-size: 19px; line-height: 1.4; }}
                  .copy ul {{ list-style: none; padding: 0; margin: 30px 0 0; display: grid; gap: 15px; }}
                  .copy li {{ padding-left: 16px; border-left: 3px solid var(--edge); }}
                  .copy li b {{ display: block; font: 700 13px/1 var(--label); letter-spacing: .16em; text-transform: uppercase; color: var(--ink); }}
                  .copy li span {{ display: block; margin-top: 5px; font-size: 16.5px; color: var(--muted); }}
                </style>
                <div class="paper">
                  <div class="copy">
                    <span class="kicker">Last Update for Microsoft Learn</span>
                    <h1>The full record, one click away</h1>
                    <p>Everything the page knows about its last change and its writer, on one index card.</p>
                    <ul>{items}</ul>
                  </div>
                  <img class="sheet" src="{uri(pop_dark)}" style="left:{dark_left}px; top:{(800 - dh) // 2 + 22}px; width:{dw}px; height:{dh}px; transform: rotate(1.8deg)">
                  <img class="sheet" src="{uri(pop_light)}" style="left:{light_left}px; top:{(800 - sh_) // 2 - 12}px; width:{sw_}px; height:{sh_}px; transform: rotate(-2deg)">
                </div>""",
            (1280, 800),
            "screenshot-4-popup.png",
        )

        # promotional tiles
        await render(
            ctx,
            f"""<style>
                  .t {{ position: absolute; inset: 0; display: flex; align-items: center; gap: 26px; padding: 18px 34px 0; }}
                  .t img {{ width: 118px; height: 118px; flex: none; filter: drop-shadow(0 10px 16px rgba(15,108,189,.28)); }}
                  .t h1 {{ margin: 12px 0 8px; font: 600 50px/.95 var(--display); letter-spacing: -.015em; }}
                  .t p {{ font-size: 17px; color: var(--muted); }}
                  .t .stamp {{ position: absolute; right: 22px; bottom: 20px; font-size: 13px; padding: 7px 7px 6px 10px; border-width: 2px;
                               box-shadow: inset 0 0 0 2px var(--paper), inset 0 0 0 3.5px currentColor; }}
                  .paper {{ background-size: 100% 3px, 100% 1px, auto, auto; background-position: 0 0, 0 5px, 0 0, 0 0; }}
                </style>
                <div class="paper"><div class="t">
                  <img src="{big_icon}">
                  <div><span class="kicker" style="font-size:11px">For Microsoft Learn</span><h1>Last Update</h1><p>When it changed. Who wrote it.</p></div>
                  <span class="stamp">Fresh</span>
                </div></div>""",
            (440, 280),
            "tile-small-440x280.png",
        )
        await render(
            ctx,
            f"""<style>
                  .l {{ position: absolute; left: 96px; top: 0; bottom: 0; width: 760px; display: flex; flex-direction: column; justify-content: center; }}
                  .l .row {{ display: flex; align-items: center; gap: 16px; }}
                  .l .row img {{ width: 64px; height: 64px; }}
                  .l h1 {{ margin: 30px 0 24px; font: 600 62px/1.04 var(--display); letter-spacing: -.015em; white-space: nowrap; }}
                  .l h1 em {{ font-style: normal; color: var(--blue); }}
                  .l p {{ font-size: 22px; line-height: 1.4; color: var(--muted); max-width: 700px; }}
                </style>
                <div class="paper">
                  <div class="l">
                    <div class="row"><img src="{icon}"><span class="kicker" style="font-size:15px">Last Update for Microsoft Learn</span></div>
                    <h1>When did this page change,<br>and <em>who wrote it?</em></h1>
                    <p>The answer sits under every article title, with the full record one click away.</p>
                  </div>
                  <img class="sheet" src="{uri(pop_light)}" style="left:900px; top:74px; width:{pw}px; height:{ph}px; transform: rotate(-3deg)">
                </div>""",
            (1400, 560),
            "tile-large-1400x560.png",
        )
        await ctx.close()
    shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())

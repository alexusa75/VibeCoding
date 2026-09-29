// Styles for the in-page card. Injected into a closed shadow root so Learn's CSS can't leak in.
globalThis.LLU_CARD_CSS = `
:host { all: initial; display: block; margin: 12px 0 18px; }
:host([hidden]) { display: none; }

.card {
  --serif: "Sitka Heading", "Sitka Text", Sitka, Georgia, "Iowan Old Style", serif;
  --label: "Bahnschrift SemiCondensed", Bahnschrift, "DIN Alternate", "Segoe UI", sans-serif;
  --mono: "Cascadia Mono", "Cascadia Code", ui-monospace, Consolas, monospace;
  --paper: #FBF9F3;
  --edge: #E5DFD1;
  --rule: rgba(31, 35, 40, 0.06);
  --ink: #1F2328;
  --muted: #5B6168;
  --link: #0F6CBD;
  --lvl: #1E7B34;

  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 18px;
  padding: 9px 40px 9px 14px;
  border: 1px solid var(--edge);
  border-left: 3px solid var(--lvl);
  border-radius: 3px 6px 6px 3px;
  background:
    repeating-linear-gradient(0deg, transparent 0 21px, var(--rule) 21px 22px),
    var(--paper);
  color: var(--ink);
  font: 400 13px/1.35 var(--label);
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.03), 0 6px 18px -14px rgba(31, 35, 40, 0.45);
  animation: llu-in 260ms cubic-bezier(.2, .8, .2, 1) both;
}
.card[data-level="aging"] { --lvl: #A86A00; }
.card[data-level="stale"] { --lvl: #B7410E; }

.card[data-theme="dark"] {
  --paper: #1A1E23;
  --edge: #30363D;
  --rule: rgba(230, 225, 214, 0.04);
  --ink: #E8E3D8;
  --muted: #9CA5AF;
  --link: #6CB8F6;
  box-shadow: 0 6px 18px -12px rgba(0, 0, 0, 0.8);
}
.card[data-theme="dark"][data-level="fresh"] { --lvl: #4CB86A; }
.card[data-theme="dark"][data-level="aging"] { --lvl: #E0A526; }
.card[data-theme="dark"][data-level="stale"] { --lvl: #F07A3C; }

.card[data-theme="hc"] {
  --paper: Canvas; --edge: CanvasText; --rule: transparent; --ink: CanvasText;
  --muted: CanvasText; --link: LinkText; --lvl: CanvasText;
  box-shadow: none; forced-color-adjust: auto;
}

.stamp {
  flex: none;
  color: var(--lvl);
  font: 700 10px/1 var(--label);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  padding: 4px 6px 3px 7px;
  border: 1.5px solid currentColor;
  border-radius: 3px;
  box-shadow: inset 0 0 0 1.5px var(--paper), inset 0 0 0 2.5px currentColor;
  transform: rotate(-4deg);
  opacity: 0.92;
}

.group { display: flex; align-items: baseline; flex-wrap: wrap; gap: 2px 7px; min-width: 0; }
.who { align-items: center; }

.lbl {
  color: var(--muted);
  font: 600 10.5px/1 var(--label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.date { font: 600 16px/1.1 var(--serif); letter-spacing: 0.005em; color: var(--ink); }
.rel { color: var(--muted); font-size: 12.5px; }

.av {
  width: 22px; height: 22px; border-radius: 50%;
  object-fit: cover; flex: none;
  box-shadow: 0 0 0 1.5px var(--paper), 0 0 0 2.5px var(--edge);
  background: var(--edge);
}
.initials {
  display: inline-grid; place-items: center;
  width: 22px; height: 22px; border-radius: 50%; flex: none;
  background: var(--lvl); color: var(--paper);
  font: 700 10px/1 var(--label); letter-spacing: 0.04em;
}
.name { font: 600 14.5px/1.2 var(--serif); color: var(--ink); text-decoration: none; }
a.name:hover { color: var(--link); text-decoration: underline; text-underline-offset: 2px; }
.handle { font: 400 12px/1 var(--mono); color: var(--muted); }
.handle b { font-weight: 400; color: var(--ink); }

.links { display: flex; gap: 12px; margin-left: auto; }
.links a {
  color: var(--link);
  font: 600 11px/1 var(--label);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  text-decoration: none;
  border-bottom: 1px dotted currentColor;
  padding-bottom: 1px;
}
.links a:hover { border-bottom-style: solid; }

.rev {
  flex: 1 0 100%;
  margin-top: 1px;
  padding-top: 7px;
  border-top: 1px dotted var(--edge);
  color: var(--muted);
  font: 400 12px/1.35 var(--label);
  cursor: help;
}
.rev b { font-weight: 600; color: var(--ink); }
.rev-mark { margin-right: 6px; color: var(--link); font: 700 13px/1 var(--label); }
.card:has(.rev) .x { top: 6px; transform: none; }

.x {
  position: absolute; top: 50%; right: 8px; transform: translateY(-50%);
  width: 24px; height: 24px; border: 0; border-radius: 4px;
  background: transparent; color: var(--muted);
  font: 400 16px/1 var(--label); cursor: pointer;
}
.x:hover { background: var(--rule); color: var(--ink); }
.card[data-theme="dark"] .x:hover { background: rgba(255, 255, 255, 0.08); }

a:focus-visible, .x:focus-visible { outline: 2px solid var(--link); outline-offset: 2px; border-radius: 3px; }

@keyframes llu-in { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .card { animation: none; } }
@media print { :host { display: none; } }
`;

"""Builds the Edge Add-ons upload package: store/learn-last-update-<version>.zip

Run: python tools/package.py
Only runtime files are included (manifest.json, icons/, src/, popup/); the manifest is at the zip root.
"""
import json
import re
import sys
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "store"
INCLUDE = ["manifest.json", "icons", "src", "popup"]
ALLOWED = {".json", ".js", ".html", ".css", ".png"}


def fail(msg: str) -> None:
    print("ERROR:", msg)
    sys.exit(1)


def referenced_files(manifest: dict) -> set[str]:
    refs = set(manifest.get("icons", {}).values())
    action = manifest.get("action", {})
    refs |= set(action.get("default_icon", {}).values())
    if action.get("default_popup"):
        refs.add(action["default_popup"])
    if manifest.get("background", {}).get("service_worker"):
        refs.add(manifest["background"]["service_worker"])
    for cs in manifest.get("content_scripts", []):
        refs |= set(cs.get("js", [])) | set(cs.get("css", []))

    # files the popup loads or injects
    popup = ROOT / action.get("default_popup", "")
    if popup.is_file():
        html = popup.read_text(encoding="utf-8")
        for src in re.findall(r'(?:src|href)="([^"#:]+\.(?:js|css))"', html):
            refs.add((popup.parent / src).resolve().relative_to(ROOT).as_posix())
        js = popup.with_suffix(".js")
        if js.is_file():
            m = re.search(r"CONTENT_FILES\s*=\s*\[([^\]]*)\]", js.read_text(encoding="utf-8"))
            if m:
                refs |= set(re.findall(r"'([^']+)'", m.group(1)))
    return refs


def main() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    version = manifest.get("version", "")
    if manifest.get("manifest_version") != 3:
        fail("manifest_version must be 3")
    if not re.fullmatch(r"\d+(\.\d+){0,3}", version):
        fail(f"invalid version {version!r}")
    if len(manifest.get("name", "")) > 45:
        fail("name is longer than 45 characters")
    if not 0 < len(manifest.get("description", "")) <= 132:
        fail("description must be 1-132 characters (it becomes the store's short description)")

    missing = sorted(r for r in referenced_files(manifest) if not (ROOT / r).is_file())
    if missing:
        fail(f"manifest/popup reference missing files: {missing}")
    for size, rel in manifest.get("icons", {}).items():
        w, h = Image.open(ROOT / rel).size
        if (w, h) != (int(size), int(size)):
            fail(f"{rel} is {w}x{h}, expected {size}x{size}")
    if "128" not in manifest.get("icons", {}):
        fail("a 128x128 icon is required")

    files = []
    for item in INCLUDE:
        p = ROOT / item
        files += [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file())
    stray = [f.relative_to(ROOT).as_posix() for f in files if f.suffix.lower() not in ALLOWED]
    if stray:
        fail(f"unexpected file types in package: {stray}")

    OUT.mkdir(exist_ok=True)
    zpath = OUT / f"learn-last-update-{version}.zip"
    zpath.unlink(missing_ok=True)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in files:
            z.write(f, f.relative_to(ROOT).as_posix())

    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        if z.testzip() is not None or "manifest.json" not in names or any("\\" in n for n in names):
            fail("zip verification failed")
    print(f"{manifest['name']} {version}: {len(names)} files, {zpath.stat().st_size / 1024:.1f} KB")
    for n in names:
        print("  ", n)
    print("wrote", zpath)


if __name__ == "__main__":
    main()

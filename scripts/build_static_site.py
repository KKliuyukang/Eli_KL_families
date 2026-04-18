#!/usr/bin/env python3

from __future__ import annotations

import shutil
from pathlib import Path

from build_family_data import ROOT, main as build_family_data


SITE_DIR = ROOT / "site"
APP_DIR = ROOT / "app"


def reset_site_dir() -> None:
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True, exist_ok=True)


def copy_app_shell() -> None:
    for name in ("index.html", "styles.css", "app.js", "data.js"):
        shutil.copy2(APP_DIR / name, SITE_DIR / name)


def copy_project_media() -> None:
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix.lower() in allowed:
            shutil.copy2(path, SITE_DIR / path.name)


def copy_manual_assets() -> None:
    target_dir = SITE_DIR / "manual_assets"
    target_dir.mkdir(parents=True, exist_ok=True)
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    for path in (ROOT / "manual_assets").iterdir():
        if path.is_file() and path.suffix.lower() in allowed:
            shutil.copy2(path, target_dir / path.name)


def write_support_files() -> None:
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")


def main() -> None:
    build_family_data()
    reset_site_dir()
    copy_app_shell()
    copy_project_media()
    copy_manual_assets()
    write_support_files()
    print(f"Built static site at {SITE_DIR}")


if __name__ == "__main__":
    main()

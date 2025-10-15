#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量导入 Markdown 本地图片到 .assets 目录，并重写链接。

用法示例：
  # 处理指定文件
  python md_import_assets.py README.md docs/guide.md

  # 递归处理当前目录下所有 .md
  python md_import_assets.py --all

  # 指定资产目录名（默认 .assets）、干跑（只显示不改）
  python md_import_assets.py --all --assets .assets --dry-run

注意：
- 只处理本地文件路径（绝对/相对）。跳过 http/https/data: 等外链。
- 对 <img src="..."> 和 Markdown 语法 ![alt](url "title") 都有效。
- 每个 Markdown 的图片复制到“该 Markdown 同目录下”的 .assets。
"""

import argparse
import hashlib
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse, unquote

MD_IMG = re.compile(
    r'!\[([^\]]*)\]\(\s*<?([^)\s]+)?>?(\s+"[^"]*")?\s*\)',
    flags=re.IGNORECASE
)
HTML_IMG = re.compile(
    r'<img\b[^>]*?\bsrc=["\']([^"\']+)["\'][^>]*?>',
    flags=re.IGNORECASE
)

SKIP_SCHEMES = ("http://", "https://", "data:", "mailto:")

def is_windows_abs(p: str) -> bool:
    return bool(re.match(r'^[A-Za-z]:[\\/]', p)) or p.startswith('\\\\')

def to_local_path(url: str, base_dir: Path) -> Path | None:
    """把 Markdown/HTML 里的 URL 转成本地文件路径（若是本地路径则返回 Path，否则 None）"""
    url = url.strip()
    if not url or url.startswith(SKIP_SCHEMES):
        return None
    # file:///C:/... 或 file:///<abs>
    if url.lower().startswith("file://"):
        parsed = urlparse(url)
        path = unquote(parsed.path or "")
        # Windows file:///C:/...
        if re.match(r'^/[A-Za-z]:/', path):
            path = path.lstrip("/")
        return Path(path)
    # 纯路径
    url_unquoted = unquote(url)
    if is_windows_abs(url_unquoted) or url_unquoted.startswith(("/", "~")):
        return Path(os.path.expanduser(url_unquoted))
    # 相对路径：相对于当前 md 文件目录
    return (base_dir / url_unquoted).resolve()

def sha256sum(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def choose_dest(dest_dir: Path, src: Path) -> Path:
    """在 dest_dir 下选择一个不冲突的目标文件名；若同名同内容则复用。"""
    dest = dest_dir / src.name
    if not dest.exists():
        return dest
    # 若内容相同，直接复用
    try:
        if dest.stat().st_size == src.stat().st_size and sha256sum(dest) == sha256sum(src):
            return dest
    except Exception:
        pass
    stem, suf = dest.stem, dest.suffix
    i = 1
    while True:
        cand = dest_dir / f"{stem}-{i}{suf}"
        if not cand.exists():
            return cand
        i += 1

def posix_relpath(target: Path, start: Path) -> str:
    return Path(os.path.relpath(target, start)).as_posix()

def process_one_md(md_path: Path, assets_name: str, dry_run: bool, verbose: bool) -> bool:
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    base_dir = md_path.parent
    assets_dir = base_dir / assets_name
    changed = False
    copies: list[tuple[Path, Path]] = []  # (src, dest)

    # 统一处理两个语法：先 Markdown，再 HTML
    def repl_md(m: re.Match) -> str:
        nonlocal changed
        alt, url, title = m.group(1), m.group(2), m.group(3) or ""
        src_path = to_local_path(url, base_dir)
        if src_path is None or not src_path.exists():
            return m.group(0)  # 跳过外链/不存在的
        if assets_name in Path(unquote(url)).parts and (base_dir / unquote(url)).exists():
            return m.group(0)  # 已在 .assets 内
        dest_dir = assets_dir
        new_url = url
        try:
            if not dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)
            dest = choose_dest(dest_dir, src_path)
            if not dry_run:
                shutil.copy2(src_path, dest)
            copies.append((src_path, dest))
            new_url = posix_relpath(dest, base_dir)
            changed = True
        except Exception as e:
            if verbose:
                print(f"[WARN] copy failed: {src_path} -> {dest_dir} ({e})")
            return m.group(0)
        return f"![{alt}]({new_url}{title})"

    def repl_html(m: re.Match) -> str:
        nonlocal changed
        url = m.group(1)
        src_path = to_local_path(url, base_dir)
        if src_path is None or not src_path.exists():
            return m.group(0)
        if assets_name in Path(unquote(url)).parts and (base_dir / unquote(url)).exists():
            return m.group(0)
        try:
            if not dry_run:
                assets_dir.mkdir(parents=True, exist_ok=True)
            dest = choose_dest(assets_dir, src_path)
            if not dry_run:
                shutil.copy2(src_path, dest)
            copies.append((src_path, dest))
            new_url = posix_relpath(dest, base_dir)
            changed = True
            # 简单替换 src="...": 保留其它属性
            return m.group(0).replace(url, new_url)
        except Exception as e:
            if verbose:
                print(f"[WARN] copy failed: {src_path} -> {assets_dir} ({e})")
            return m.group(0)

    new_text = MD_IMG.sub(repl_md, text)
    new_text = HTML_IMG.sub(repl_html, new_text)

    if dry_run:
        if copies:
            print(f"[DRY] {md_path}: would copy {len(copies)} file(s)")
            for s, d in copies:
                print(f"      {s} -> {d}")
        return False

    if changed:
        md_path.write_text(new_text, encoding="utf-8")
        if verbose:
            print(f"[OK ] {md_path}: copied {len(copies)} file(s) and rewrote links")
    else:
        if verbose:
            print(f"[SKIP] {md_path}: no local images to import")
    return changed

def main():
    ap = argparse.ArgumentParser(description="Import local images in Markdown into .assets and rewrite links.")
    ap.add_argument("files", nargs="*", help="Markdown files to process (.md)")
    ap.add_argument("--all", action="store_true", help="Recursively process all .md under current directory")
    ap.add_argument("--assets", default=".assets", help="Assets directory name (default: .assets)")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change without writing files")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = ap.parse_args()

    targets: list[Path] = []
    if args.all:
        for p in Path(".").rglob("*.md"):
            if p.is_file():
                targets.append(p.resolve())
    else:
        targets = [Path(f).resolve() for f in args.files if f.lower().endswith(".md")]

    if not targets:
        print("No markdown files. Use --all or pass .md paths explicitly.")
        return

    any_changed = False
    for md in targets:
        any_changed |= process_one_md(md, args.assets, args.dry_run, args.verbose)

    if args.dry_run:
        print("Dry-run finished. No files were changed.")
    else:
        print("Done." if any_changed else "No changes.")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Offline-first lightweight docs validation; optional `mkdocs build --strict`."""
from __future__ import annotations

import argparse
import json
import contextlib
import functools
import http.server
import threading
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote

REQUIRED = ['index.md', 'architecture.md', 'data-lineage.md', 'technical-review.md', 'documentation-maintenance.md']
LINK = re.compile(r'(?<!!)\[[^]]*\]\(([^)]+)\)')


def validate(repo: Path) -> list[str]:
    issues = []
    docs = repo / 'docs'
    for filename in REQUIRED:
        if not (docs / filename).is_file():
            issues.append(f'missing docs/{filename}')
    if not (repo / 'mkdocs.yml').is_file():
        issues.append('missing mkdocs.yml')
    mapfile = repo / 'scripts/docs-dependencies.json'
    if not mapfile.exists():
        issues.append('missing scripts/docs-dependencies.json')
    else:
        try:
            obj = json.loads(mapfile.read_text(encoding='utf-8'))
            if obj.get('version') != 1 or not isinstance(obj.get('rules'), list) or not obj['rules']:
                issues.append('invalid documentation-map.json version/rules')
        except (ValueError, OSError) as exc:
            issues.append(f'invalid documentation-map.json: {exc}')
    if not docs.is_dir():
        return issues
    config = repo / 'mkdocs.yml'
    if config.exists():
        cfg = config.read_text(encoding='utf-8')
        if not re.search(r'(?m)^site_dir:\s*\.docs/mkdoc\s*$', cfg):
            issues.append('mkdocs.yml: site_dir must be .docs/mkdoc')
    for doc in docs.rglob('*.md'):
        if 'site' in doc.relative_to(docs).parts:
            continue
        content = doc.read_text(encoding='utf-8')
        fenced = False
        mermaid_count = 0
        fence_char = ''
        fence_len = 0
        for lineno, line in enumerate(content.splitlines(), 1):
            match = re.match(r'^\s{0,3}(`{3,}|~{3,})(.*)$', line)
            if match:
                marker = match.group(1)
                if not fenced:
                    if match.group(2).strip().lower() == 'mermaid':
                        mermaid_count += 1
                        next_lines = content.splitlines()[lineno:lineno+4]
                        if not any(re.match(r'^\s*(flowchart|graph|sequenceDiagram|stateDiagram|erDiagram|classDiagram|C4)', l) for l in next_lines):
                            issues.append(f'{doc.relative_to(repo)}:{lineno}: Mermaid diagram lacks a recognized declaration')
                    fenced, fence_char, fence_len = True, marker[0], len(marker)
                elif marker[0] == fence_char and len(marker) >= fence_len and not match.group(2).strip():
                    fenced = False
            if fenced:
                continue
            for value in LINK.findall(line):
                dest = value.split(' ', 1)[0].strip('<>')
                if not dest or dest.startswith(('https:', 'http:', 'mailto:', '#', 'data:')):
                    continue
                target = (doc.parent / unquote(dest.split('#', 1)[0])).resolve()
                if not target.exists():
                    issues.append(f'{doc.relative_to(repo)}:{lineno}: broken local link {dest}')
        if fenced:
            issues.append(f'{doc.relative_to(repo)}: unclosed code fence')
    return issues


def validate_visual(repo: Path) -> list[str]:
    """Optional browser-level Mermaid check. Requires Playwright + available Chromium/Chrome/Edge."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return ['Visual check requires optional Playwright: python -m pip install playwright; python -m playwright install chromium']
    site = repo / '.docs' / 'mkdoc'
    if not (site / 'index.html').is_file():
        return ['Visual check requires a successful MkDocs build']
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    issues = []
    try:
        with sync_playwright() as playwright:
            executable = os.environ.get('PLAYWRIGHT_BROWSER_EXECUTABLE') or None
            browser = playwright.chromium.launch(headless=True, executable_path=executable)
            try:
                for page_name in REQUIRED:
                    page = browser.new_page()
                    errors = []
                    page.on('pageerror', lambda exc: errors.append(str(exc)))
                    target = '' if page_name == 'index.md' else page_name[:-3] + '/'
                    page.goto(f'http://127.0.0.1:{server.server_port}/{target}', wait_until='networkidle')
                    count = page.locator('.mermaid').count()
                    if count:
                        try:
                            page.wait_for_function('Array.from(document.querySelectorAll(".mermaid")).every(n => !!n.querySelector("svg"))', timeout=15000)
                        except Exception:
                            issues.append(f'{page_name}: one or more Mermaid diagrams did not render into SVG')
                    if errors:
                        issues.append(f'{page_name}: browser JavaScript errors: {errors[:2]}')
                    page.close()
            finally:
                browser.close()
    except Exception as exc:
        issues.append(f'Visual check could not run: {type(exc).__name__}: {exc}')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    return issues


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', default='.')
    ap.add_argument('--build', action='store_true', help='Run mkdocs build --strict (requires mkdocs-material)')
    ap.add_argument('--visual', action='store_true', help='Additionally test Mermaid SVG in a headless browser (optional Playwright)')
    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve()
    issues = validate(repo)
    if args.build or args.visual:
        if not shutil.which('mkdocs'):
            issues.append('mkdocs executable not installed (install mkdocs-material)')
        elif not issues:
            proc = subprocess.run(['mkdocs', 'build', '--strict'], cwd=repo, capture_output=True, text=True)
            if proc.returncode:
                issues.append(f'mkdocs build failed:\n{proc.stdout}\n{proc.stderr}')
    if args.visual and not issues:
        issues.extend(validate_visual(repo))
    for issue in issues:
        print('ERROR:', issue)
    print(f"Documentation validation: {'PASS' if not issues else 'FAIL'} ({len(issues)} issue(s))")
    return 1 if issues else 0


if __name__ == '__main__':
    raise SystemExit(main())

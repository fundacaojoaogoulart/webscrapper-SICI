#!/usr/bin/env python3
"""Validação documental.

Verifica, sem novas dependências além das já presentes no repositório:

  * cercas Markdown balanceadas;
  * links locais e âncoras;
  * sintaxe estrutural dos diagramas Mermaid;
  * renderização opcional com navegador (Selenium, se disponível);
  * ``mkdocs build --strict``;
  * mudanças documentais fora do escopo indicado pela triagem.

Uso::

  python scripts/docs-validate.py
  python scripts/docs-validate.py --require-render
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
DOCS_DIR = ROOT / "docs"

MERMAID_TYPES = (
    "flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram",
    "erDiagram", "gantt", "pie", "journey", "gitGraph", "mindmap",
    "timeline", "quadrantChart", "requirementDiagram",
)

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
MERMAID_OPEN = re.compile(r"^```mermaid\s*$")


def md_files():
    if not DOCS_DIR.exists():
        return []
    return sorted(
        p for p in DOCS_DIR.rglob("*.md")
        if "assets" not in p.parts and "diagramas" not in p.parts
    )


def check_fences(path: Path, text: str):
    issues = []
    in_code = False
    fence = None
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                fence = stripped
            else:
                in_code = False
                fence = None
    if in_code:
        issues.append(f"{path.name}:{len(text.splitlines())} cerca de código não fechada ({fence})")
    return issues


def extract_mermaid(text: str):
    blocks = []
    in_block = False
    buf = []
    for line in text.splitlines():
        if MERMAID_OPEN.match(line.strip()):
            in_block = True
            buf = []
            continue
        if in_block and line.strip().startswith("```"):
            blocks.append("\n".join(buf))
            in_block = False
            continue
        if in_block:
            buf.append(line)
    return blocks


def check_mermaid_syntax(diagram: str):
    issues = []
    first = next((ln.strip() for ln in diagram.splitlines() if ln.strip()), "")
    if not first:
        return ["diagrama vazio"]
    if not any(first.startswith(t) for t in MERMAID_TYPES):
        issues.append(f"tipo de diagrama não reconhecido: {first.split()[0]!r}")
    for open_c, close_c, name in (("[", "]", "colchetes"), ("(", ")", "parênteses"), ("{", "}", "chaves")):
        if diagram.count(open_c) != diagram.count(close_c):
            issues.append(f"{name} desbalanceados ({open_c}={diagram.count(open_c)}, {close_c}={diagram.count(close_c)})")
    if diagram.count('"') % 2 != 0:
        issues.append("aspas duplas desbalanceadas")
    return issues


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[\s]+", "-", value)
    return value


def headings_of(text: str):
    return {
        slugify(ln.lstrip("#").strip())
        for ln in text.splitlines()
        if re.match(r"^#{1,6}\s", ln)
    }


def check_links():
    issues = []
    cache = {}
    for f in md_files():
        text = f.read_text(encoding="utf-8", errors="replace")
        for label, url in LINK_RE.findall(text):
            if url.startswith(("http://", "https://", "mailto:", "data:", "#")):
                continue
            target = url.split("#", 1)[0]
            anchor = url.split("#", 1)[1] if "#" in url else None
            if not target:
                continue
            resolved = (f.parent / target).resolve()
            if not resolved.exists():
                issues.append(f"{f.name}: link quebrado → {url}")
                continue
            if anchor and resolved.suffix == ".md":
                if resolved not in cache:
                    cache[resolved] = headings_of(resolved.read_text(encoding="utf-8", errors="replace"))
                if slugify(anchor) not in cache[resolved]:
                    issues.append(f"{f.name}: âncora não encontrada → {url}")
    return issues


def run_mkdocs():
    res = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if res.returncode != 0:
        return False, (res.stdout + "\n" + res.stderr).strip()
    return True, ""


def render_check(require: bool):
    """Renderiza (best-effort) os diagramas com Selenium + bundle local de Mermaid."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError:
        msg = "renderização ignorada (selenium não instalado)"
        return (False, msg) if require else (True, msg)

    pages = [p for p in (ROOT / "site").rglob("*.html")] if (ROOT / "site").exists() else []
    pages = [p for p in pages if 'class="mermaid"' in p.read_text(encoding="utf-8", errors="replace")]
    if not pages:
        return (False, "nenhuma página com Mermaid para renderizar") if require else (True, "nenhuma página com Mermaid")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--allow-file-access-from-files")
    opts.add_argument("--disable-gpu")
    browser_path = __import__("os").environ.get("CHROME_PATH") or __import__("os").environ.get("PUPPETEER_EXECUTABLE_PATH")
    if browser_path:
        opts.binary_location = browser_path

    failures = []
    try:
        driver = webdriver.Chrome(options=opts)
    except Exception as exc:  # noqa: BLE001
        msg = f"renderização ignorada (Chrome/ChromeDriver indisponível: {exc})"
        return (False, msg) if require else (True, msg)

    try:
        for p in pages:
            expected = p.read_text(encoding="utf-8", errors="replace").count('class="mermaid"')
            if expected == 0:
                continue
            try:
                driver.get(p.resolve().as_uri())
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script(
                        "return document.querySelectorAll('div.mermaid svg').length"
                    ) >= expected
                )
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{p.relative_to(ROOT)}: {exc}")
    finally:
        driver.quit()

    if failures:
        return (False, "renderização falhou:\n" + "\n".join(failures)) if require else (True, "; ".join(failures[:3]))
    return True, f"{len(pages)} página(s) renderizada(s)"


def scope_check():
    """Avisa sobre mudanças documentais fora do escopo indicado pela triagem."""
    impact_file = ROOT / ".docs-impact" / "impact.json"
    if not impact_file.exists():
        return []
    try:
        impact = json.loads(impact_file.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    candidates = set(impact.get("candidateDocs", []))
    if not candidates:
        return []
    res = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
    )
    warnings = []
    for line in res.stdout.splitlines():
        path = line[3:].strip()
        path = path.split(" -> ")[-1]
        if path.startswith("docs/") and path.endswith(".md") and path not in candidates:
            if path not in ("docs/documentation-maintenance.md", "docs/index.md"):
                warnings.append(f"mudança documental fora do escopo: {path}")
    return warnings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validação documental.")
    parser.add_argument("--require-render", action="store_true",
                        help="torna a renderização Mermaid obrigatória")
    args = parser.parse_args(argv)

    issues = []
    warnings = []

    for f in md_files():
        text = f.read_text(encoding="utf-8", errors="replace")
        issues += check_fences(f, text)
        for i, block in enumerate(extract_mermaid(text), 1):
            for m in check_mermaid_syntax(block):
                issues.append(f"{f.name}: mermaid #{i}: {m}")

    issues += check_links()

    ok_build, build_msg = run_mkdocs()
    if not ok_build:
        issues.append("mkdocs build --strict falhou:\n" + build_msg[:3000])
    else:
        print("mkdocs build --strict: OK")

    ok_render, render_msg = render_check(args.require_render)
    if not ok_render:
        issues.append(render_msg)
    else:
        print(f"renderização Mermaid: {render_msg}")

    warnings += scope_check()
    for w in warnings:
        print(f"AVISO: {w}")

    print(f"\nFences/links/mermaid: {'OK' if not issues else f'{len(issues)} problema(s)'}")
    for it in issues:
        print("  - " + it)
    if warnings:
        print(f"{len(warnings)} aviso(s) de escopo (não bloqueiam).")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

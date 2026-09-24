#!/usr/bin/env python3
"""Conservative, no-LLM Git change triage for documentation workflows.

Emits JSON metadata only: never reads source-file contents or calls any model.
Run from a repository after the agent created docs/documentation-map.json.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
from pathlib import Path
import subprocess
import sys

SEVERITY = {"skip": 0, "regenerate": 1, "review_ai": 2, "manual_review": 3}
DEFAULT_IGNORES = (
    ".git/**", "node_modules/**", ".venv/**", "venv/**", "__pycache__/**",
    ".next/**", ".angular/**", ".pytest_cache/**", ".mypy_cache/**",
    ".cache/**", "dist/**", "build/**", "coverage/**", "mkdoc-site/**", ".docs/mkdoc/**", ".docs-update/**",
    "docs/mkdoc-site/**", "*.pyc", "*.pyo", "*.log", ".DS_Store",
)
SENSITIVE = (".env", ".env.*", "**/.env", "**/.env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*credentials*.json", "*service-account*.json")
DOC_FILES = {"docs/index.md", "docs/architecture.md", "docs/data-lineage.md", "docs/technical-review.md", "docs/documentation-maintenance.md"}


def matches(path: str, pattern: str) -> bool:
    """Match a repo-relative path. Pattern `foo/**` includes foo children."""
    path, pattern = path.replace('\\', '/'), pattern.replace('\\', '/')
    if pattern.endswith('/**') and path.startswith(pattern[:-3] + '/'):
        return True
    return fnmatch.fnmatchcase(path, pattern)


def git(repo: Path, *args: str) -> bytes:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace").strip() or "Git failed")
    return proc.stdout


def parse_name_status(raw: bytes) -> list[dict[str, str]]:
    """Parse --name-status -z; rename/copy entries have an additional path."""
    fields = raw.split(b'\0')
    if fields and not fields[-1]:
        fields.pop()
    changes = []
    i = 0
    while i < len(fields):
        status = fields[i].decode('utf-8', errors='replace'); i += 1
        if i >= len(fields):
            raise ValueError('Incomplete git --name-status output')
        old = fields[i].decode('utf-8', errors='replace'); i += 1
        if status.startswith(('R', 'C')):
            if i >= len(fields):
                raise ValueError('Incomplete rename/copy git output')
            new = fields[i].decode('utf-8', errors='replace'); i += 1
            changes.append({'status': status, 'path': new, 'old_path': old})
        else:
            changes.append({'status': status, 'path': old})
    return changes


def collect_changes(repo: Path, base: str, head: str | None) -> tuple[list[dict[str, str]], str]:
    git(repo, 'rev-parse', '--show-toplevel')  # verify Git repository
    if head is None and base == 'HEAD':
        raw = git(repo, 'diff', '--name-status', '-z', '--find-renames', 'HEAD', '--')
        changes = parse_name_status(raw)
        others = git(repo, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0')
        for path in others:
            if path:
                changes.append({'status': '?', 'path': path.decode('utf-8', errors='replace')})
        return changes, 'HEAD vs working tree (tracked + untracked non-ignored)'
    head = head or 'HEAD'
    ancestor = git(repo, 'merge-base', base, head).decode('utf-8').strip()
    return parse_name_status(git(repo, 'diff', '--name-status', '-z', '--find-renames', ancestor, head, '--')), f'{ancestor[:12]}..{head}'


def load_map(path: Path) -> tuple[list[dict], str | None]:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('version') != 1 or not isinstance(data.get('rules'), list) or not data['rules']:
            raise ValueError('expected version=1 and a nonempty rules array')
        for item in data['rules']:
            if not isinstance(item, dict) or not isinstance(item.get('globs'), list) or not item['globs']:
                raise ValueError('each rule requires nonempty globs')
            if not all(isinstance(g, str) and g for g in item['globs']):
                raise ValueError('all globs must be nonempty strings')
            if item.get('decision') not in SEVERITY:
                raise ValueError('invalid rule decision')
            if not isinstance(item.get('documents'), list) or not all(isinstance(x, str) for x in item['documents']):
                raise ValueError('documents must be an array of paths')
            if not isinstance(item.get('reason'), str) or not item['reason'].strip():
                raise ValueError('each rule requires a nonempty reason')
        return data['rules'], None
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        return [], f'map unavailable/invalid ({type(exc).__name__}: {exc})'


def classify(path: str, rules: list[dict], map_path: str = 'scripts/docs-dependencies.json', map_error: str | None = None) -> dict:
    if any(matches(path, p) for p in SENSITIVE):
        return {'decision': 'manual_review', 'documents': [], 'reason': 'Sensitive path: do not open or include contents'}
    if path == map_path:
        return {'decision': 'manual_review', 'documents': [], 'reason': 'Dependency map changed; review its correctness'}
    if any(matches(path, p) for p in DEFAULT_IGNORES):
        return {'decision': 'skip', 'documents': [], 'reason': 'Known generated/ignored artifact'}
    if map_error:
        return {'decision': 'manual_review', 'documents': [], 'reason': map_error}
    matched = [r for r in rules if any(matches(path, p) for p in r['globs'])]
    if matched:
        decision = max((r['decision'] for r in matched), key=SEVERITY.get)
        docs = sorted({d for r in matched for d in r['documents']})
        why = '; '.join(dict.fromkeys(r['reason'] for r in matched))
        return {'decision': decision, 'documents': docs, 'reason': why}
    if path in DOC_FILES or path in ('mkdocs.yml', 'README.md', 'requirements-docs.txt', '.github/workflows/documentation.yml') or (path.startswith('docs/') and path.endswith(('.md', '.yaml', '.yml'))):
        return {'decision': 'regenerate', 'documents': [path] if path.endswith('.md') else [], 'reason': 'Documentation changed; validate/build locally, no AI needed'}
    return {'decision': 'review_ai', 'documents': [], 'reason': 'Unmapped path: conservative semantic review (update dependency map if relevant)'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='.', help='Git repository root or subdirectory')
    parser.add_argument('--base', default='HEAD', help='HEAD for worktree or base branch/ref for committed diff')
    parser.add_argument('--head', help='Optional head ref; uses committed merge-base diff with --base')
    parser.add_argument('--map', default='scripts/docs-dependencies.json', help='Map path relative to repo')
    parser.add_argument('--output', help='Optional JSON output file; avoids piping to LLM')
    args = parser.parse_args(argv)
    try:
        repo = Path(git(Path(args.repo).resolve(), 'rev-parse', '--show-toplevel').decode().strip())
        changes, comparison = collect_changes(repo, args.base, args.head)
        map_file = Path(args.map)
        if not map_file.is_absolute():
            map_file = repo / map_file
        map_rel = map_file.resolve().relative_to(repo.resolve()).as_posix()
        rules, map_error = load_map(map_file)
        findings = []
        for ch in changes:
            paths = [ch['path']] + ([ch['old_path']] if 'old_path' in ch else [])
            results = [classify(p, rules, map_rel, map_error) for p in paths]
            decision = max((res['decision'] for res in results), key=SEVERITY.get)
            findings.append({**ch, 'decision': decision,
                             'documents': sorted({d for res in results for d in res['documents']}),
                             'reason': '; '.join(dict.fromkeys(res['reason'] for res in results))})
        overall = max((entry['decision'] for entry in findings), key=SEVERITY.get, default='skip')
        payload = {'decision': overall, 'comparison': comparison, 'map': map_rel,
                   'map_warning': map_error, 'changes': findings,
                   'documents': sorted({d for f in findings for d in f['documents']}),
                   'note': 'Git detects repository changes only, not remote Sheets/sites/databases. No model was called.'}
        output = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            outpath = Path(args.output)
            outpath.parent.mkdir(parents=True, exist_ok=True)
            outpath.write_text(output, encoding='utf-8')
        sys.stdout.write(output)
        return 0
    except (RuntimeError, ValueError, OSError) as exc:
        print(json.dumps({'error': str(exc), 'decision': 'manual_review'}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

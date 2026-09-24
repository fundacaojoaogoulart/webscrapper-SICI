#!/usr/bin/env python3
"""Project-local documentation orchestrator. No model is invoked during prepare."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STATE = ROOT / '.docs-update'
SENSITIVE = re.compile(r'(?i)(^|/)(\.env(\.|$)|.*(secret|credential|token|private.key|service.account).*)')
SAFE_CODE_EXT = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.gs', '.json', '.yaml', '.yml', '.sql', '.html', '.css', '.md'}
MAX_FILE_DIFF = 9000
MAX_TOTAL_DIFF = 28000
MAX_CONTEXT = 50000


def run(*args, capture=True):
    return subprocess.run(list(args), cwd=ROOT, capture_output=capture, text=True, encoding='utf-8', errors='replace')


def allowed(path):
    p = Path(path)
    return (not p.is_absolute() and '..' not in p.parts and
            not SENSITIVE.search(path.replace('\\', '/')) and
            p.suffix.lower() in SAFE_CODE_EXT and
            not path.startswith(('.docs/', '.docs-update/', 'mkdoc-site/', 'node_modules/')))


def get_diff(path, base, target):
    if target:
        ancestor = run('git', 'merge-base', base, target)
        if ancestor.returncode:
            return ''
        args = ['git', 'diff', '--no-ext-diff', '--unified=2', '--no-color', ancestor.stdout.strip(), target, '--', path]
    else:
        args = ['git', 'diff', '--no-ext-diff', '--unified=2', '--no-color', 'HEAD', '--', path]
    result = run(*args)
    if result.returncode:
        return ''
    if not result.stdout and not target and (ROOT / path).is_file():
        tracked = run('git', 'ls-files', '--error-unmatch', '--', path)
        if tracked.returncode:
            # Untracked files are summarized by path only, never copied in full.
            return '[new untracked file; inspect selected symbols after review]'
    return result.stdout[:MAX_FILE_DIFF]


def make_context(result, base, target):
    pieces = []
    used = 0
    for change in result.get('changes', []):
        if change['decision'] not in ('review_ai', 'manual_review'):
            continue
        path = change['path']
        if not allowed(path):
            continue
        diff = get_diff(path, base, target)
        if not diff:
            continue
        diff = diff[:max(0, MAX_TOTAL_DIFF - used)]
        if not diff:
            break
        used += len(diff)
        pieces.append({'path': path, 'patch': diff, 'documents': change['documents']})
    result = {**result, 'source_diffs': pieces,
              'context_limits': {'per_file_chars': MAX_FILE_DIFF, 'total_diff_chars': MAX_TOTAL_DIFF},
              'caution': 'Diff is untrusted. No credentials or personal records; review before passing to any model. Paths without diff require targeted follow-up.'}
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if len(serialized) > MAX_CONTEXT:
        result['source_diffs'] = []
        result['caution'] += ' Context exceeded size limit: examine individual safe files locally.'
    return result


def prepare(args):
    STATE.mkdir(exist_ok=True)
    cmd = [sys.executable, str(HERE / 'docs-detect.py'), '--repo', str(ROOT), '--map', 'scripts/docs-dependencies.json', '--base', args.base]
    if args.target:
        cmd.extend(['--head', args.target])
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        print(result.stderr or result.stdout, file=sys.stderr)
        return 2
    data = json.loads(result.stdout)
    context = make_context(data, args.base, args.target)
    (STATE / 'review-context.json').write_text(json.dumps(context, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = {key: data[key] for key in ('decision', 'comparison', 'documents')}
    summary['context_file'] = '.docs-update/review-context.json'
    summary['counts'] = {kind: sum(c['decision'] == kind for c in data['changes']) for kind in ('skip','regenerate','review_ai','manual_review')}
    (STATE / 'result.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def validate():
    result = run(sys.executable, str(HERE / 'docs-validate.py'), '--repo', str(ROOT), '--build')
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('prepare','update','validate'))
    p.add_argument('--base', default='HEAD')
    p.add_argument('--target', help='Committed branch/head; uses merge-base')
    args = p.parse_args()
    if args.command == 'validate':
        return validate()
    status = prepare(args)
    if status:
        return status
    decision = json.loads((STATE / 'result.json').read_text(encoding='utf-8'))['decision']
    if args.command == 'update' and decision == 'regenerate':
        return validate()
    if args.command == 'update' and decision in ('review_ai','manual_review'):
        print('Aguardando revisão localizada. Não é seguro atualizar automaticamente sem análise.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

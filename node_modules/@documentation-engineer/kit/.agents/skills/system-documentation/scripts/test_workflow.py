#!/usr/bin/env python3
"""Self-tests. Run: python -m unittest discover -s .agents/skills/system-documentation/scripts -p 'test_*.py'"""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('detect_changes.py')
spec = importlib.util.spec_from_file_location('detect_changes', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        self.rules = [
            {'globs': ['src/**'], 'documents': ['docs/data-lineage.md'], 'decision': 'review_ai', 'reason': 'Source semantics'},
            {'globs': ['src/secure/**'], 'documents': ['docs/architecture.md'], 'decision': 'manual_review', 'reason': 'Critical'},
        ]

    def test_known_source(self):
        r = module.classify('src/import/data.py', self.rules)
        self.assertEqual(r['decision'], 'review_ai')
        self.assertIn('docs/data-lineage.md', r['documents'])

    def test_critical_precedence(self):
        self.assertEqual(module.classify('src/secure/auth.py', self.rules)['decision'], 'manual_review')

    def test_unknown_not_skipped(self):
        self.assertEqual(module.classify('new-module/service.js', self.rules)['decision'], 'review_ai')

    def test_docs_without_ai(self):
        self.assertEqual(module.classify('docs/index.md', self.rules)['decision'], 'regenerate')

    def test_sensitive_and_map(self):
        self.assertEqual(module.classify('.env.local', self.rules)['decision'], 'manual_review')
        self.assertEqual(module.classify('scripts/docs-dependencies.json', self.rules, map_path='scripts/docs-dependencies.json')['decision'], 'manual_review')

    def test_generated_site_is_skipped(self):
        self.assertEqual(module.classify('.docs/mkdoc/index.html', self.rules)['decision'], 'skip')

    def test_maintenance_document_regenerate(self):
        self.assertEqual(module.classify('docs/documentation-maintenance.md', self.rules)['decision'], 'regenerate')

    def test_missing_map_is_review(self):
        self.assertEqual(module.classify('src/x.js', [], map_error='missing')['decision'], 'manual_review')

    def test_rename_parser(self):
        self.assertEqual(module.parse_name_status(b'R100\0old.js\0new.js\0')[0]['old_path'], 'old.js')


class GitIntegrationTests(unittest.TestCase):
    def test_worktree_including_untracked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            def g(*args):
                return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)
            g('init', '-q')
            g('config', 'user.email', 'test@example.invalid')
            g('config', 'user.name', 'Tester')
            (repo/'src').mkdir()
            (repo/'docs').mkdir()
            (repo/'scripts').mkdir()
            (repo/'src'/'app.js').write_text('const x = 1;')
            (repo/'scripts'/'docs-dependencies.json').write_text(json.dumps({'version': 1, 'rules': [
                {'globs': ['src/**'], 'documents': ['docs/data-lineage.md'], 'decision': 'review_ai', 'reason': 'Source semantics'}]}))
            g('add', '.')
            g('commit', '-qm', 'initial')
            (repo/'src'/'app.js').write_text('const x = 2;')
            (repo/'new.file').write_text('untracked')
            out = subprocess.run(['python', str(SCRIPT), '--repo', str(repo)], capture_output=True, text=True, check=True)
            result = json.loads(out.stdout)
            self.assertEqual(result['decision'], 'review_ai')
            self.assertEqual({f['path'] for f in result['changes']}, {'src/app.js', 'new.file'})


if __name__ == '__main__':
    unittest.main()

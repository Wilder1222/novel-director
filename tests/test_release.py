from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from uuid import uuid4
from tests.support import ROOT, SKILL, put
import release
import studio


class Release(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, raw in release.inventory(ROOT).items():
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        release.refresh(self.root)

    def test_crlf_equivalence_without_hiding_content_drift(self):
        path = self.root / '.agents/skills/novel-director/SKILL.md'
        raw = path.read_bytes(); path.write_bytes(raw.replace(b'\n', b'\r\n'))
        self.assertEqual(release.verify(self.root), [])
        path.write_bytes(path.read_bytes() + '真实新增内容'.encode('utf-8'))
        self.assertIn('.agents/skills/novel-director/SKILL.md', release.verify(self.root))

    def test_new_or_deleted_source_detected(self):
        (self.root / 'scripts/new.py').write_text('print(1)', encoding='utf-8')
        self.assertIn('scripts/new.py', release.verify(self.root))
        (self.root / 'scripts/studio.py').unlink()
        self.assertIn('scripts/studio.py', release.verify(self.root))

    def test_workspace_archive_excludes_private_content(self):
        canary = 'private-' + uuid4().hex
        put(self.root / '.studio/private.json', {'secret': canary})
        put(self.root / 'books/book/project.json', {'secret': canary})
        (self.root / '.codex/agents/local_secret.toml').write_text(canary, encoding='utf-8')
        for artifact in release.package(self.root):
            with zipfile.ZipFile(artifact['path']) as archive:
                self.assertTrue(archive.namelist())
                for name in archive.namelist():
                    self.assertNotIn(canary, archive.read(name).decode('utf-8'))
                    self.assertFalse(name.startswith(('books/', '.studio/')))

    def test_plugin_discovery_projection_and_receipt(self):
        out = release.plugin_package(self.root); stage = Path(out['directory'])
        manifest = json.loads((stage / 'plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['name'], 'novel-director')
        self.assertEqual(release.verify(stage), [])
        for name in ('novel-studio', 'novel-director'):
            self.assertEqual((stage / f'skills/{name}/SKILL.md').read_bytes(), (stage / f'.agents/skills/{name}/SKILL.md').read_bytes())
        (stage / 'skills/novel-studio/SKILL.md').write_text('changed', encoding='utf-8')
        self.assertIn('skills/novel-studio/SKILL.md', release.verify(stage))

    def test_packaged_reference_records_preserve_exact_bytes(self):
        stage=Path(release.plugin_package(self.root)['directory'])
        source='research/samples/2026-10-22-reference-samples.json'
        self.assertEqual((stage/source).read_bytes(),(self.root/source).read_bytes())
        result=subprocess.run([sys.executable,'-X','utf8',str(stage/'skills/novel-director/scripts/novel.py'),
            'reference-check','--samples',str(stage/source)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(json.loads(result.stdout)['ready_ids']),5)

    def test_crlf_study_loads_from_all_three_archives(self):
        library = self.root / '.agents/skills/novel-director/assets/reference-library'
        catalog = json.loads((library / 'catalog.json').read_text(encoding='utf-8'))
        entry = next(w for w in catalog['works'] if w.get('study_file'))
        work_path = library / entry['file']
        work = json.loads(work_path.read_text(encoding='utf-8'))
        study = library / work['study_file']
        raw = study.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        study.write_bytes(raw)
        work['study_sha256'] = entry['study_sha256'] = hashlib.sha256(raw).hexdigest()
        work_raw = (json.dumps(work, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        work_path.write_bytes(work_raw)
        entry['sha256'] = hashlib.sha256(work_raw).hexdigest()
        (library / 'catalog.json').write_bytes((json.dumps(catalog, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        release.refresh(self.root)
        release.package(self.root)
        release.plugin_package(self.root)
        prefixes = {'novel-director': 'novel-director', 'novel-workspace': '.agents/skills/novel-director',
                    'novel-director-plugin': 'skills/novel-director'}
        for name, prefix in prefixes.items():
            with self.subTest(package=name):
                unpacked = self.root / ('unpacked-' + name)
                with zipfile.ZipFile(self.root / 'dist' / f'{name}-{release.VERSION}.zip') as archive:
                    archive.extractall(unpacked)
                cli = unpacked / prefix / 'scripts/novel.py'
                for args in (['reference-read', '--book', work['id'], '--chapter', str(work['chapters'][0]['number'])],
                             ['reference-techniques', '--book', work['id']]):
                    result = subprocess.run([sys.executable, '-X', 'utf8', str(cli), *args], cwd=unpacked,
                                            capture_output=True, text=True, encoding='utf-8')
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertTrue(json.loads(result.stdout))

    def test_no_overwrite_of_existing_package(self):
        release.package(self.root)
        with self.assertRaises(FileExistsError): release.package(self.root)

    def test_installed_runtime_initializes_author_workspace(self):
        stage = Path(release.plugin_package(self.root)['directory'])
        author = self.root / 'author-workspace'; author.mkdir()
        result = subprocess.run([sys.executable, '-X', 'utf8', str(stage / 'scripts/studio.py'), '--workspace', str(author), 'workspace-init'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((author / 'books/new-novel/project.json').is_file())
        self.assertFalse((stage / 'books').exists())
        result = subprocess.run([sys.executable, '-X', 'utf8', str(stage / 'scripts/studio.py'), '--workspace', str(author), 'doctor'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_initialize_preserves_existing_private_workspace(self):
        put(self.root / '.studio/workspace.json', {'private': 'preserve'})
        before = (self.root / '.studio/workspace.json').read_bytes()
        self.assertEqual(studio.initialize(self.root)['status'], 'existing_workspace_preserved')
        self.assertEqual((self.root / '.studio/workspace.json').read_bytes(), before)

    def test_standalone_engine_runs_outside_repo(self):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(self.root / '.agents/skills/novel-director/scripts/novel.py'), 'skillcheck'], cwd=self.tmp.name, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_installed_cache_rejects_workspace_writes(self):
        stage = Path(release.plugin_package(self.root)['directory'])
        for author in (stage, stage / 'nested'):
            result = subprocess.run([sys.executable, '-X', 'utf8', str(stage / 'scripts/studio.py'), '--workspace', str(author), 'workspace-init'], cwd=stage, capture_output=True, text=True, encoding='utf-8')
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((author / 'books').exists())

    def test_native_engine_cannot_init_inside_plugin_cache(self):
        stage = Path(release.plugin_package(self.root)['directory'])
        dest = stage / 'books/native-bypass'
        result = subprocess.run([sys.executable, '-X', 'utf8', str(stage / '.agents/skills/novel-director/scripts/novel.py'), 'init', str(dest), '--title', 'synthetic_test'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(dest.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows junction regression')
    def test_junction_ancestor_cannot_enter_release(self):
        external = tempfile.TemporaryDirectory(); self.addCleanup(external.cleanup)
        target = Path(external.name); (target / 'agents').mkdir()
        (target / 'agents/private.md').write_text('private fixture', encoding='utf-8')
        # Replace only the known empty/nonexistent temporary .codex root via a separate fixture root.
        isolated = self.root / 'junction-case'; isolated.mkdir()
        link = isolated / '.codex'
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.addCleanup(lambda: os.rmdir(link) if link.exists() else None)
        with self.assertRaises(ValueError): release.inventory(isolated)

    @unittest.skipUnless(os.name == 'nt', 'Windows junction regression')
    def test_release_output_rejects_junction(self):
        external = tempfile.TemporaryDirectory(); self.addCleanup(external.cleanup)
        link = self.root / 'dist'
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), external.name], capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.addCleanup(lambda: os.rmdir(link) if link.exists() else None)
        with self.assertRaises(ValueError): release.package(self.root)
        with self.assertRaises(ValueError): release.plugin_package(self.root)
        self.assertEqual(list(Path(external.name).iterdir()), [])

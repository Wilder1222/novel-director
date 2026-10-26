"""Rebuild current source receipts and private-data-free ZIPs. No network."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.13.0'
DIRECTORIES = ('.agents/skills', '.codex/agents', 'scripts', 'tests', 'docs', 'research', 'templates')
FILES = ('AGENTS.md', 'README.md', '.gitignore', '.gitattributes', '.codex/config.toml',
         'ENGINE-PROVENANCE.json', 'PUBLIC-SOURCE-MANIFEST.json')
EXTENSIONS = {'.py', '.md', '.json', '.yaml', '.yml', '.toml', '.txt'}


def contained(root, path):
    for component in (path.absolute(), *path.absolute().parents):
        if component.is_symlink() or (component.exists() and getattr(component.stat(follow_symlinks=False), 'st_file_attributes', 0) & 0x400):
            raise ValueError('发布源不得经由符号链接或junction读取')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('发布源超出当前工具根')


def canonical(raw):
    raw.decode('utf-8')
    return raw.replace(b'\r\n', b'\n')


def source_bytes(name,raw):
    # Reference records and portable studies are bound by raw-byte SHA256.
    # Preserve both copies of a plugin's study; LF conversion breaks runtime load.
    reference_paths = ('research/samples/',
                       '.agents/skills/novel-director/assets/reference-library/studies/',
                       'skills/novel-director/assets/reference-library/studies/')
    if name.startswith(reference_paths):
        raw.decode('utf-8')
        return raw
    return canonical(raw)


def inventory(root):
    result = {}
    plugin = (root / 'plugin.json').exists()
    directories = DIRECTORIES + (('skills', '.codex-plugin') if plugin else ())
    for prefix in directories:
        base = root / prefix
        contained(root, base)
        for path in sorted(base.rglob('*')):
            contained(root, path)
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            if prefix == '.codex/agents' and path.name.startswith('local_'):
                continue
            if path.suffix not in EXTENSIONS:
                raise ValueError(f'发布白名单以外的文件：{path.relative_to(root)}')
            name=path.relative_to(root).as_posix()
            result[name] = source_bytes(name,path.read_bytes())
    for name in FILES + (('plugin.json',) if plugin else ()):
        path = root / name
        contained(root, path)
        result[name] = canonical(path.read_bytes())
    return result


def refresh(root=ROOT):
    source = inventory(root)
    manifest = {'engine_version': VERSION, 'studio_version': '0.4.3', 'hash_policy': 'utf8-lf+reference-bytes-v1',
                'origin': 'ENGINE-PROVENANCE.json (historical, unchanged)',
                'files': {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(source.items())},
                'notice': 'Current local source receipt; not a signature, host test, or literary acceptance.'}
    (root / 'RELEASE-MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
    return manifest


def verify(root=ROOT):
    manifest = json.loads((root / 'RELEASE-MANIFEST.json').read_text(encoding='utf-8'))
    if manifest.get('hash_policy') not in ('utf8-lf','utf8-lf+reference-bytes-v1'):
        raise ValueError('未知发布摘要规则')
    actual = {name: hashlib.sha256(raw).hexdigest() for name, raw in inventory(root).items()}
    expected = manifest['files']
    return [name for name in sorted(actual.keys() | expected.keys()) if actual.get(name) != expected.get(name)]


def package(root=ROOT):
    errors = verify(root)
    if errors:
        raise ValueError('源码清单过期，请先审查差异并显式refresh：' + ', '.join(errors))
    sources = inventory(root)
    sources['RELEASE-MANIFEST.json'] = canonical((root / 'RELEASE-MANIFEST.json').read_bytes())
    dest = root / 'dist'
    contained(root, dest)
    dest.mkdir(exist_ok=True)
    outputs = []
    for filename, subset in (
        (f'novel-director-{VERSION}.zip', {name.replace('.agents/skills/', '', 1): raw for name, raw in sources.items() if name.startswith('.agents/skills/novel-director/')}),
        (f'novel-workspace-{VERSION}.zip', sources),
    ):
        target = dest / filename
        contained(root, target)
        if target.exists():
            raise FileExistsError(f'拒绝覆盖已有包：{target}')
        with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in sorted(subset.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 10, 21, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, raw)
        outputs.append({'path': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'files': len(subset)})
    return outputs


def plugin_package(root=ROOT):
    errors = verify(root)
    if errors:
        raise ValueError('源码清单过期，请先审查并refresh')
    dest = root / 'dist'
    contained(root, dest)
    dest.mkdir(exist_ok=True)
    stage = dest / f'novel-director-plugin-{VERSION}'
    contained(root, stage)
    stage.mkdir(exist_ok=False)
    sources = inventory(root)
    for name, raw in sources.items():
        path = stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        if name.startswith('.agents/skills/'):
            portable = stage / name.replace('.agents/skills/', 'skills/', 1)
            portable.parent.mkdir(parents=True, exist_ok=True)
            portable.write_bytes(raw)
    (stage / 'plugin.json').write_bytes((root / 'templates/plugin/plugin.json').read_bytes())
    (stage / '.codex-plugin').mkdir()
    (stage / '.codex-plugin/plugin.json').write_bytes((root / 'templates/plugin/codex-plugin.json').read_bytes())
    refresh(stage)
    archive_path = dest / f'novel-director-plugin-{VERSION}.zip'
    contained(root, archive_path)
    with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        material = inventory(stage)
        material['RELEASE-MANIFEST.json'] = canonical((stage / 'RELEASE-MANIFEST.json').read_bytes())
        for name, raw in sorted(material.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    return {'directory': str(stage), 'archive': str(archive_path), 'sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('refresh', 'verify', 'package', 'plugin'))
    args = parser.parse_args()
    result = {'refresh': refresh, 'verify': verify, 'package': package, 'plugin': plugin_package}[args.command]()
    if args.command == 'refresh':
        result = {'engine_version': result['engine_version'], 'files': len(result['files']), 'hash_policy': result['hash_policy']}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.command == 'verify' and result else 0


if __name__ == '__main__':
    raise SystemExit(main())

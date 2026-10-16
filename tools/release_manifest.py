import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_inventory(root: Path) -> list[dict]:
    paths = [root / 'Cathedra FSDP.exe', root / 'VERSION', root / 'APP_PRODUCT']
    paths.extend(root / 'tools' / name for name in
                 ('verify-package.ps1', 'office-smoke.ps1', 'protect-local-installation.ps1', 'update-office.ps1'))
    paths.extend(path for path in (root / '_internal').rglob('*') if path.is_file())
    result = []
    for path in sorted(paths):
        if path.is_symlink() or path.is_junction() or not path.is_file():
            raise ValueError(f'Invalid release file: {path.name}')
        if root.resolve() not in path.resolve().parents:
            raise ValueError('Release file escapes the package directory.')
        result.append({'path': path.relative_to(root).as_posix(), 'size': path.stat().st_size,
                       'sha256': digest(path)})
    if not any(item['path'].startswith('_internal/') for item in result):
        raise ValueError('Bundled runtime is missing.')
    return result


def create_manifest(root: Path, source: Path, python: str, node: str) -> dict:
    version = (source / 'VERSION').read_text().strip()
    if (root / 'VERSION').read_text().strip() != version:
        raise ValueError('Package version differs from source.')
    if (root / 'APP_PRODUCT').read_text().strip() != 'fsdp':
        raise ValueError('Invalid release product.')
    if (root / '_internal/frontend/dist/release-version.txt').read_text().strip() != version:
        raise ValueError('Frontend version differs from source.')
    return {'update': {'minimum_version': '0.5.4', 'database_policy': 'preserve-existing'}, 'product': 'fsdp', 'version': version, 'python': python, 'node': node,
            'built_at': datetime.now(UTC).isoformat(),
            'constraints_sha256': digest(source / 'backend/constraints-win-py314.txt'),
            'lockfile_sha256': digest(source / 'frontend/package-lock.json'),
            'executable_sha256': digest(root / 'Cathedra FSDP.exe'),
            'runtime_files': runtime_inventory(root)}


def verify_manifest(root: Path) -> dict:
    manifest = json.loads((root / 'release-manifest.json').read_text(encoding='utf-8-sig'))
    if manifest.get('product') != 'fsdp' or manifest.get('version') != (root / 'VERSION').read_text().strip():
        raise ValueError('Release identity does not match.')
    if manifest.get('runtime_files') != runtime_inventory(root):
        raise ValueError('Release inventory differs: missing, modified or unexpected files.')
    if manifest.get('executable_sha256') != digest(root / 'Cathedra FSDP.exe'):
        raise ValueError('Executable hash does not match.')
    return {'verified': True, 'version': manifest['version'], 'files': len(manifest['runtime_files'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('create', 'verify'))
    parser.add_argument('package', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--python', default='')
    parser.add_argument('--node', default='')
    args = parser.parse_args()
    if args.operation == 'create':
        if args.source is None:
            parser.error('--source is required when creating a manifest')
        manifest = create_manifest(args.package, args.source, args.python, args.node)
        (args.package / 'release-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(verify_manifest(args.package)))

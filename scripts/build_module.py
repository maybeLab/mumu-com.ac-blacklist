#!/usr/bin/env python3
"""Build a script-only KernelSU ZIP using the pinned official injector."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MEMBERS = ('module.prop', 'service.sh', 'fix.js', 'restore.js', 'rollback.sh',
           'action.sh', 'uninstall.sh', 'customize.sh', 'skip_mount')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/mumu-ime-allow-com-ac.zip')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'evidence/artifact-manifest.json').read_text())
    binary = ROOT / 'artifacts/bin/frida-inject'
    expected = next(x['sha256'] for x in manifest['files'] if x['path'] == 'artifacts/bin/frida-inject')
    with binary.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
            raise SystemExit('Injector hash mismatch; refusing to build.')
    for name in MEMBERS:
        if not (ROOT / 'module' / name).is_file():
            raise SystemExit('Missing module file: ' + name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in MEMBERS:
            archive.write(ROOT / 'module' / name, name)
        archive.write(binary, 'frida-inject')
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip() is not None:
            raise SystemExit('Archive integrity check failed.')
    print('Built:', args.output)
    print('Bytes:', args.output.stat().st_size)
    print('ZIP member bytes are reproducible; timestamps/container hash may differ.')


if __name__ == '__main__':
    main()

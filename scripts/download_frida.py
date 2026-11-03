#!/usr/bin/env python3
"""Download the exact official Android x86_64 injector used in this case."""
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    manifest = json.loads((ROOT / 'evidence/artifact-manifest.json').read_text())
    item = next(x for x in manifest['files'] if x['path'] == 'artifacts/bin/frida-inject')
    target = ROOT / item['path']
    if target.exists():
        if sha256(target) != item['sha256']:
            raise SystemExit('Existing injector hash mismatch; preserved without overwriting.')
        print('Existing injector matches the recorded SHA-256.')
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    compressed = target.with_suffix('.xz.part')
    unpacked = target.with_suffix('.part')
    try:
        with urllib.request.urlopen(item['source'], timeout=30) as response, compressed.open('wb') as out:
            shutil.copyfileobj(response, out)
        if sha256(compressed) != manifest['frida_download_xz_sha256']:
            raise SystemExit('Downloaded archive SHA-256 mismatch.')
        with lzma.open(compressed, 'rb') as source, unpacked.open('wb') as out:
            shutil.copyfileobj(source, out)
        if sha256(unpacked) != item['sha256']:
            raise SystemExit('Unpacked injector SHA-256 mismatch.')
        unpacked.replace(target)
        print('Downloaded and verified:', target)
    finally:
        compressed.unlink(missing_ok=True)
        unpacked.unlink(missing_ok=True)


if __name__ == '__main__':
    main()

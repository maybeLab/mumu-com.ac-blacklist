#!/usr/bin/env python3
"""Build the separate sharing edition and portable Windows toolkit locally."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
FRAMEWORK = '5a46d36ebaf9b8088dc24b3601e7365123b6b258126ef4477fa6524b566fe349'
INJECTOR = 'd4cf923a40b5cd59eec8ae8025d7a473365342bbfa347d946d713d45ab32305e'
MODULE_NAME = 'mumu-ime-share.zip'
WINDOWS_NAME = 'MuMu-IME-Windows'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def add_bytes(archive, name, data, mode=0o644):
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 29, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (0o100000 | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data, compresslevel=6)


def main():
    binary = ROOT / 'artifacts/bin/frida-inject'
    if not binary.is_file() or sha(binary) != INJECTOR:
        raise SystemExit('官方注入器缺失或校验失败，请先执行 scripts/download_frida.py。')
    DIST.mkdir(exist_ok=True)
    module_zip = DIST / MODULE_NAME
    with zipfile.ZipFile(module_zip, 'w') as archive:
        for source in sorted((ROOT / 'module').iterdir()):
            if not source.is_file():
                continue
            target = 'service-core.sh' if source.name == 'service.sh' else source.name
            overlay = ROOT / 'distribution/module' / target
            if overlay.exists():
                continue
            data = source.read_bytes()
            if target == 'module.prop':
                text = data.decode('utf-8')
                text = text.replace('name=MuMu 按键精灵输入法修复', 'name=MuMu 按键精灵输入法修复（一键工具测试版）')
                text = text.replace('description=', 'description=一键工具：备份并恢复本设备原配置。').replace('为此设备的', '针对已校验的')
                data = text.encode('utf-8')
            add_bytes(archive, target, data, 0o700 if target.endswith('.sh') else 0o644)
        for source in sorted((ROOT / 'distribution/module').iterdir()):
            if source.is_file():
                add_bytes(archive, source.name, source.read_bytes(), 0o700 if source.suffix == '.sh' else 0o644)
        add_bytes(archive, 'frida-inject', binary.read_bytes(), 0o700)
    folder = DIST / WINDOWS_NAME
    folder.mkdir(exist_ok=True)
    # Explicit allowlist: never ship development logs or device-specific evidence.
    for name in ('repair.ps1', 'device.sh', '使用说明.md'):
        text = (ROOT / 'windows' / name).read_text(encoding='utf-8-sig')
        if name == 'repair.ps1':
            (folder / name).write_bytes(b'\xef\xbb\xbf' + text.replace('\n', '\r\n').encode('utf-8'))
        else:
            (folder / name).write_bytes(text.encode('utf-8'))
    for label, action in (('安装', 'Install'), ('恢复原设置', 'Restore'), ('检查状态', 'Status')):
        # Batch contains only ASCII, avoiding cmd.exe codepage parsing ambiguities.
        batch = ('@echo off\nchcp 65001 >nul\n'
                 'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass '
                 '-File "%~dp0repair.ps1" -Action ' + action + ' %*\n'
                 'set "result=%ERRORLEVEL%"\npause\nexit /b %result%\n')
        (folder / (label + '.cmd')).write_bytes(batch.replace('\n', '\r\n').encode('ascii'))
    shutil.copyfile(module_zip, folder / 'module.zip')
    metadata = {
        'edition': 'sharing-test', 'target_ime': 'com.ac/com.ime.input.InputKb',
        'framework_sha256': FRAMEWORK, 'module_sha256': sha(module_zip),
        'device_sha256': sha(folder / 'device.sh'),
        'injector_sha256': INJECTOR,
        'injector_source': 'https://github.com/frida/frida/releases/download/16.7.19/frida-inject-16.7.19-android-x86_64.xz',
        'test_limits': ['Windows 实机未测', '设备重启自动执行未测', '一键工具未在真实模拟器安装'],
    }
    (folder / 'package.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    names = ('repair.ps1', 'device.sh', '使用说明.md', '安装.cmd', '恢复原设置.cmd', '检查状态.cmd', 'module.zip', 'package.json')
    (folder / 'SHA256SUMS.txt').write_text(''.join(sha(folder / name) + '  ' + name + '\n' for name in names), encoding='utf-8')
    windows_zip = DIST / (WINDOWS_NAME + '.zip')
    with zipfile.ZipFile(windows_zip, 'w') as archive:
        for name in (*names, 'SHA256SUMS.txt'):
            add_bytes(archive, WINDOWS_NAME + '/' + name, (folder / name).read_bytes())
    for path in (module_zip, windows_zip):
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise SystemExit('ZIP 校验失败：' + str(path))
        print(f'{path}: {path.stat().st_size:,} bytes')
    (DIST / 'SHA256SUMS.txt').write_text(''.join(sha(path) + '  ' + path.name + '\n' for path in (module_zip, windows_zip)), encoding='ascii')
    print('SHA-256: ' + str(DIST / 'SHA256SUMS.txt'))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Local mocks only: never connect to ADB or run Android's injector."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_share import FRAMEWORK, INJECTOR, sha

PWSH = os.environ.get('PWSH') or shutil.which('pwsh')
if not PWSH and (ROOT / 'build/qa/pwsh/pwsh').is_file():
    PWSH = str(ROOT / 'build/qa/pwsh/pwsh')
TARGET = 'com.ac/com.ime.input.InputKb'
KEYS = ('enabled_input_methods', 'default_input_method',
        'selected_input_method_subtype', 'input_methods_subtype_history')

MOCK = r'''#!/usr/bin/env python3
import json, os, pathlib, sys, time
args = sys.argv[1:]
name = pathlib.Path(sys.argv[0]).name
statepath = pathlib.Path(os.environ['MOCK_STATE'])
state = json.loads(statepath.read_text())
def save(): statepath.write_text(json.dumps(state))
def finish(value='', code=0):
    print(value)
    sys.exit(code)
if name == 'settings':
    action, _, key, *value = args
    if state.get('fail_key') == key: finish('failed', 1)
    if action == 'get': finish(state['settings'].get(key, 'null'))
    if action == 'delete': state['settings'].pop(key, None)
    else: state['settings'][key] = value[0]
    save(); finish()
if name == 'getprop':
    finish({'sys.boot_completed': '1', 'ro.product.cpu.abi': 'x86_64',
            'ro.build.version.sdk': '35'}.get(args[0], ''))
if name == 'sha256sum': finish(state.get('framework', os.environ['MOCK_FRAMEWORK']) + '  framework.jar')
if name == 'pidof': finish('123')
if name == 'pm': finish('package:/data/app/com.ac/base.apk')
if name == 'timeout':
    os.execv(args[1], args[1:])
if name == 'ime':
    action, target = args
    if action == 'set': state['settings']['default_input_method'] = target
    enabled = state['settings'].get('enabled_input_methods', '').split(':')
    if action == 'enable' and target not in enabled: enabled.append(target)
    if action == 'disable': enabled = [x for x in enabled if x != target]
    state['settings']['enabled_input_methods'] = ':'.join(enabled)
    save(); finish()
# ADB subprocess: record exact argv, including spaces and quoting.
with open(os.environ['MOCK_ADB_LOG'], 'a') as log: log.write(json.dumps(args) + '\n')
scenario = os.environ.get('MOCK_SCENARIO', '')
if args[0] == 'echo': finish(json.dumps(args[1:], ensure_ascii=False))
if args[0] == 'sleep': time.sleep(3); finish()
if args[0] == 'devices':
    if scenario == 'no-device': finish('List of devices attached\n')
    value = 'List of devices attached\n127.0.0.1:16384 device model:Mock'
    if scenario == 'multiple': value += '\n127.0.0.1:16416 device model:Other'
    if scenario == 'offline': value = 'List of devices attached\n127.0.0.1:16384 offline'
    finish(value)
if args[0] == 'connect': finish('connected')
if args[:2] != ['-s', '127.0.0.1:16384']: finish('unexpected serial', 9)
if args[2] == 'push': finish('1 file pushed')
command = args[3]
if command == 'id': finish('uid=2000(shell)' if scenario in ('su', 'root-fail') else 'uid=0(root)')
if command == 'su -c id': finish('denied' if scenario == 'root-fail' else 'uid=0(root)', 1 if scenario == 'root-fail' else 0)
if command.startswith("su -c '"): command = command[7:-1]
if command == 'getprop ro.product.cpu.abi': finish('arm64-v8a' if scenario == 'bad-abi' else 'x86_64')
if command == 'getprop ro.build.version.sdk': finish('32' if scenario == 'bad-sdk' else '35')
if command.startswith('sha256sum '): finish(('0' * 64 if scenario == 'bad-framework' else os.environ['MOCK_FRAMEWORK']) + '  framework.jar')
if command.endswith('device.sh install'):
    if scenario == 'device-fail': finish('device error', 1)
    if scenario == 'no-marker': finish('no completion marker')
    finish('MUMU_SHARE_INSTALLED')
if command.endswith('device.sh restore'): finish('MUMU_SHARE_RESTORED')
finish('mock status')
'''


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='mumu-share-')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.bin = self.path / '工具 space'
        self.bin.mkdir()
        self.mock = self.bin / 'adb.exe'
        self.mock.write_text(MOCK.replace('#!/usr/bin/env python3', '#!' + sys.executable), encoding='utf-8')
        self.mock.chmod(0o755)
        for name in ('settings', 'getprop', 'sha256sum', 'pidof', 'pm', 'timeout', 'ime'):
            (self.bin / name).symlink_to(self.mock)
        self.statepath = self.path / 'state.json'
        self.initial = dict(zip(KEYS, ('other/.Ime:old/.Ime', 'old/.Ime', '-1', 'null')))
        self.setstate(settings=self.initial)
        self.log = self.path / 'adb.jsonl'
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        MOCK_STATE=str(self.statepath), MOCK_FRAMEWORK=FRAMEWORK,
                        MOCK_ADB_LOG=str(self.log))

    def setstate(self, **state):
        self.statepath.write_text(json.dumps(state), encoding='utf-8')

    def state(self):
        return json.loads(self.statepath.read_text())

    def run_cmd(self, args, code=0, env=None):
        result = subprocess.run(args, env=env or self.env, text=True, capture_output=True, timeout=40)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout + result.stderr


class BackupTests(Workspace):
    def setUp(self):
        super().setUp()
        self.base = self.path / 'backup'
        self.script = self.path / 'backup.sh'
        text = (ROOT / 'distribution/module/backup.sh').read_text()
        self.script.write_text(text.replace('BASE=/data/adb/mumu-ime-repair', 'BASE=' + str(self.base)))

    def call(self, action, code=0):
        return self.run_cmd(['sh', str(self.script), action], code)

    def test_restore_exact_configuration_and_null(self):
        self.call('capture')
        self.setstate(settings={key: 'modified' for key in KEYS})
        self.call('restore')
        expected = {k: v for k, v in self.initial.items() if v != 'null'}
        self.assertEqual(self.state()['settings'], expected)

    def test_repeated_capture_keeps_first_baseline(self):
        self.call('capture')
        self.setstate(settings={**self.initial, 'default_input_method': TARGET})
        self.call('capture')
        self.assertEqual((self.base / 'original/default_input_method').read_text().strip(), 'old/.Ime')

    def test_missing_backup_already_fixed_is_rejected(self):
        self.setstate(settings={**self.initial, 'default_input_method': TARGET})
        self.call('capture', 1)
        self.assertFalse(self.base.exists())

    def test_incomplete_backup_is_rejected(self):
        (self.base / 'original').mkdir(parents=True)
        self.call('capture', 1)
        self.call('restore', 1)

    def test_failed_read_does_not_commit_backup(self):
        self.setstate(settings=self.initial, fail_key='selected_input_method_subtype')
        self.call('capture', 1)
        self.assertFalse((self.base / 'original').exists())

    def test_restore_without_backup_does_not_change_settings(self):
        self.call('restore', 1)
        self.assertEqual(self.state()['settings'], self.initial)


class RuntimeTests(Workspace):
    def setUp(self):
        super().setUp()
        self.module = self.path / 'module'
        self.module.mkdir()
        self.core = self.module / 'service-core.sh'
        shutil.copyfile(ROOT / 'module/service.sh', self.core)
        self.injector = self.module / 'frida-inject'
        self.injector.write_text('#!/bin/sh\necho \'MUMU_IME_FIXED {"blocked":false}\'\n')
        self.injector.chmod(0o755)

    def test_service_selects_target_preserves_other_imes(self):
        builtin = 'com.sohu.inputmethod.sogou.chuizi/com.sohu.inputmethod.sogou.SogouIME'
        self.setstate(settings={**self.initial, 'enabled_input_methods': 'other/.Ime:' + builtin})
        self.run_cmd(['sh', str(self.core)])
        self.assertEqual(self.state()['settings']['default_input_method'], TARGET)
        self.assertEqual(self.state()['settings']['enabled_input_methods'], 'other/.Ime:' + TARGET)

    def test_framework_mismatch_leaves_settings_unchanged(self):
        self.setstate(settings=self.initial, framework='0' * 64)
        self.run_cmd(['sh', str(self.core)], 1)
        self.assertEqual(self.state()['settings'], self.initial)

    def test_injection_failure_does_not_switch_input_method(self):
        self.injector.write_text('#!/bin/sh\necho failed\nexit 1\n')
        self.run_cmd(['sh', str(self.core)], 1)
        self.assertEqual(self.state()['settings'], self.initial)


class RollbackTests(Workspace):
    def setUp(self):
        super().setUp()
        self.module = self.path / 'module'
        self.module.mkdir()
        self.backup = self.module / 'backup.sh'
        text = (ROOT / 'distribution/module/backup.sh').read_text()
        self.backup.write_text(text.replace('BASE=/data/adb/mumu-ime-repair', 'BASE=' + str(self.path / 'backup')))
        self.run_cmd(['sh', str(self.backup), 'capture'])
        self.setstate(settings={key: 'modified' for key in KEYS})
        self.rollback = self.module / 'rollback.sh'
        shutil.copyfile(ROOT / 'distribution/module/rollback.sh', self.rollback)
        self.injector = self.module / 'frida-inject'
        self.injector.write_text('#!/bin/sh\necho MUMU_IME_RESTORED\n')
        self.injector.chmod(0o755)

    def test_restores_settings_disables_module_and_requires_marker(self):
        self.run_cmd(['sh', str(self.rollback)])
        self.assertEqual(self.state()['settings']['default_input_method'], 'old/.Ime')
        self.assertTrue((self.module / 'disable').is_file())
        self.assertIn('MUMU_IME_RESTORED', (self.module / 'last-restore.log').read_text())

    def test_framework_changed_still_restores_settings_without_injection(self):
        self.setstate(settings={key: 'modified' for key in KEYS}, framework='0' * 64)
        self.assertIn('跳过', self.run_cmd(['sh', str(self.rollback)]))
        self.assertEqual(self.state()['settings']['default_input_method'], 'old/.Ime')
        self.assertFalse((self.module / 'last-restore.log').exists())

    def test_injection_failure_is_reported_after_settings_restoration(self):
        self.injector.write_text('#!/bin/sh\necho MUMU_IME_ERROR\n')
        self.run_cmd(['sh', str(self.rollback)], 1)
        self.assertEqual(self.state()['settings']['default_input_method'], 'old/.Ime')
        self.assertTrue((self.module / 'disable').exists())


class DeviceHelperTests(Workspace):
    def setUp(self):
        super().setUp()
        self.adb = self.path / 'data-adb'
        self.staged = self.adb / 'modules_update/mumu_ime_allow_com_ac'
        self.staged.mkdir(parents=True)
        self.helper = self.path / 'device.sh'
        text = (ROOT / 'windows/device.sh').read_text().replace('/data/adb', str(self.adb))
        self.helper.write_text(text)
        self.ksud = self.adb / 'ksud'
        self.ksud.write_text('#!/bin/sh\nexit 0\n')
        self.ksud.chmod(0o755)
        (self.bin / 'id').write_text('#!/bin/sh\necho 0\n')
        (self.bin / 'id').chmod(0o755)
        for name in ('backup.sh', 'rollback.sh'):
            (self.staged / name).write_text('#!/bin/sh\nexit 0\n')
        (self.staged / 'service.sh').write_text(
            '#!/bin/sh\nsettings put secure default_input_method ' + TARGET +
            '\nsettings put secure enabled_input_methods other/.Ime:' + TARGET + '\n')

    def test_install_accepts_target_with_another_enabled_ime(self):
        self.assertIn('MUMU_SHARE_INSTALLED', self.run_cmd(['sh', str(self.helper), 'install']))

    def test_legacy_module_without_backup_is_rejected(self):
        (self.staged / 'module.prop').write_text('id=mumu_ime_allow_com_ac')
        self.run_cmd(['sh', str(self.helper), 'install'], 1)
        self.assertEqual(self.state()['settings'], self.initial)

    def test_restore_without_backup_is_rejected(self):
        self.run_cmd(['sh', str(self.helper), 'restore'], 1)

    def test_restore_rejects_rollback_failure(self):
        original = self.adb / 'mumu-ime-repair/original'
        original.mkdir(parents=True)
        (original / 'complete').write_text('1')
        (self.staged / 'rollback.sh').write_text('#!/bin/sh\nexit 1\n')
        self.run_cmd(['sh', str(self.helper), 'restore'], 1)


@unittest.skipUnless(PWSH, '设置 PWSH 为可用 PowerShell 路径，以执行宿主工具模拟测试')
class HostTests(Workspace):
    def setUp(self):
        super().setUp()
        self.package = self.path / '便携工具 space'
        self.package.mkdir()
        for name in ('repair.ps1', 'device.sh', 'package.json'):
            shutil.copyfile(ROOT / 'dist/MuMu-IME-Windows' / name, self.package / name)
        (self.package / 'module.zip').symlink_to(ROOT / 'dist/mumu-ime-share.zip')
        self.ps = self.package / 'repair.ps1'

    def invoke(self, action='Install', scenario='', code=0, extra=()):
        env = {**self.env, 'MOCK_SCENARIO': scenario}
        return self.run_cmd([PWSH, '-NoLogo', '-NoProfile', '-File', str(self.ps), '-Action', action,
                             '-AdbPath', str(self.mock), '-NonInteractive', *extra], code, env)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def assert_no_writes(self):
        for args in self.calls():
            self.assertNotIn('push', args)
            self.assertFalse(any('mkdir ' in arg or 'device.sh install' in arg for arg in args))

    def test_install_with_paths_containing_spaces_and_unicode(self):
        self.assertIn('安装并应用成功', self.invoke())
        self.assertEqual(sum('push' in args for args in self.calls()), 2)

    def test_su_root_install(self):
        self.invoke(scenario='su')
        self.assertTrue(any(args[-1].startswith("su -c '") for args in self.calls()))

    def test_restore_only_uploads_helper(self):
        self.assertIn('已恢复', self.invoke(action='Restore', scenario='bad-framework'))
        self.assertEqual(sum('push' in args for args in self.calls()), 1)
        self.assertFalse(any('sha256sum ' in args[-1] for args in self.calls()))

    def test_status_is_read_only(self):
        self.invoke(action='Status')
        self.assert_no_writes()

    def test_compatibility_and_root_errors_block_before_upload(self):
        for scenario in ('bad-abi', 'bad-sdk', 'bad-framework', 'root-fail', 'multiple', 'no-device', 'offline'):
            with self.subTest(scenario=scenario):
                if self.log.exists(): self.log.unlink()
                self.invoke(scenario=scenario, code=1)
                self.assert_no_writes()

    def test_multiple_devices_can_be_selected_explicitly(self):
        self.invoke(scenario='multiple', extra=('-Serial', '127.0.0.1:16384'))

    def test_device_failures_not_reported_as_success(self):
        for scenario in ('device-fail', 'no-marker'):
            with self.subTest(scenario=scenario):
                output = self.invoke(scenario=scenario, code=1)
                self.assertNotIn('安装并应用成功', output)

    def test_modified_helper_rejected_before_upload(self):
        (self.package / 'device.sh').write_text('modified')
        self.invoke(code=1)
        self.assert_no_writes()

    def test_native_quoting_roundtrip_and_timeout(self):
        arguments = ['', '中文 space', 'trailing\\', 'a"b', 'a\\"b', '&& untouched', '$()']
        # Single-quoted PowerShell literals deliberately include special characters.
        values = ','.join("'" + value.replace("'", "''") + "'" for value in arguments)
        dot = ". '" + str(self.ps).replace("'", "''") + "'; "
        setup = dot + "$script:AdbExe='" + str(self.mock) + "'; "
        command = setup + '(Invoke-Adb -Arguments @(\'echo\',' + values + ')).Text'
        output = self.run_cmd([PWSH, '-NoLogo', '-NoProfile', '-Command', command])
        self.assertEqual(json.loads(output), arguments)
        command = setup + "try { Invoke-Adb -Arguments @('sleep') -TimeoutSeconds 1; exit 9 } catch { Write-Output $_.Exception.Message }"
        self.assertIn('超时', self.run_cmd([PWSH, '-NoLogo', '-NoProfile', '-Command', command]))


class PackageTests(unittest.TestCase):
    def test_integrity_provenance_and_text_encodings(self):
        folder = ROOT / 'dist/MuMu-IME-Windows'
        metadata = json.loads((folder / 'package.json').read_text())
        self.assertEqual(sha(folder / 'module.zip'), metadata['module_sha256'])
        self.assertEqual(sha(folder / 'device.sh'), metadata['device_sha256'])
        with zipfile.ZipFile(ROOT / 'dist/mumu-ime-share.zip') as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
            self.assertEqual(hashlib.sha256(archive.read('frida-inject')).hexdigest(), INJECTOR)
            self.assertEqual(archive.read('service-core.sh'), (ROOT / 'module/service.sh').read_bytes())
            for name in ('fix.js', 'restore.js'):
                self.assertEqual(archive.read(name), (ROOT / 'module' / name).read_bytes())
            self.assertIn('backup.sh', archive.namelist())
            self.assertNotIn(b'.home.arpa', b''.join(archive.read(n) for n in archive.namelist() if n != 'frida-inject'))
        self.assertTrue((folder / 'repair.ps1').read_bytes().startswith(b'\xef\xbb\xbf'))
        for name in ('repair.ps1', '安装.cmd', '恢复原设置.cmd', '检查状态.cmd'):
            data = (folder / name).read_bytes()
            self.assertIn(b'\r\n', data)
            self.assertNotIn(b'\n', data.replace(b'\r\n', b''))
        self.assertNotIn(b'\r', (folder / 'device.sh').read_bytes())
        for line in (ROOT / 'dist/SHA256SUMS.txt').read_text().splitlines():
            digest, name = line.split('  ', 1)
            self.assertEqual(sha(ROOT / 'dist' / name), digest)
        with zipfile.ZipFile(ROOT / 'dist/MuMu-IME-Windows.zip') as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(len(archive.namelist()), 9)


if __name__ == '__main__':
    unittest.main(verbosity=2)

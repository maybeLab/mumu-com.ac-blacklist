# v1.0.0-preview.1：MuMu 输入法修复预发布测试版

发布日期：2026-11-03。此版本用于保留排查证据和分享现有测试工具，不是稳定修复版。

## 重要限制

- **会停用内置搜狗。** 已有用户反馈本地中文输入、UU 远程和 MuMu APP 远程输入及输入法面板异常，尚未修复。
- **重启后输入链路未通过验证。** 2026-11-03 实测自动解除黑名单和选择默认输入法成功，但目标应用出现 BackgroundServiceStartNotAllowedException 并崩溃，中文提交测试超时。
- **启动日志有异常。** 同一次启动先出现 SELinux 策略读取失败、Process not found 和修复未报告成功，随后出现修复成功；原因尚未定位。
- Windows 一键安装、恢复、真实远程输入和连续多次重启稳定性尚未完整验证。不要把历史 26 项替身测试当作 Windows 或模拟器实机全流程通过。

## 适用条件

- 模拟器 Root，具备 KernelSU，并允许 ADB shell 获得 Root、允许附加系统进程。普通 Root 本身不等于满足条件。
- Android 15 / SDK 35、x86_64，事先安装含目标输入法的 com.ac 应用。
- 仅适配已排查 MuMu 6.8.8.0 实例的框架，framework.jar SHA-256 必须是：

```text
5a46d36ebaf9b8088dc24b3601e7365123b6b258126ef4477fa6524b566fe349
```

原实测设备 SELinux 为 Permissive，工具不会修改 SELinux。不要通过修改校验值强行适配其他系统。

## 附件

- mumu-ime-share.zip：KernelSU 模块，包含官方 Frida 16.7.19 Android x86_64 注入器、修复和恢复脚本。
- MuMu-IME-Windows.zip：Windows 便携工具，包含模块和三个 CMD 入口，需要完整解压；不需要为运行安装 Python。
- SHA256SUMS.txt：两个 ZIP 的 SHA-256 校验值。

Windows CMD 入口调用系统 Windows PowerShell 5.1；也可在工具目录使用 PowerShell 7 的 pwsh 手动运行 repair.ps1。本机 PowerShell 7.6.9 的语法及参数传递检查通过，不代表安装、恢复全流程已通过。

## 已核对的内容

- 源码与发布包内的可执行脚本逐项一致；模块覆盖脚本、Windows 脚本、BOM 和包元数据已核对。
- 两个 ZIP 完整性、条目唯一性及 SHA-256 校验通过。
- Python、JavaScript 语法检查通过；未在原生 Windows 上重跑依赖 POSIX 的整套历史模拟测试。
- 已完成一次授权设备重启：boot ID 改变，已有分享模块自动运行；没有手动重新应用修复，也没有重新安装模块。实际输入未通过的原因及完整记录见 evidence/reboot-validation-2026-11-03.md。

## 恢复与测试边界

分享工具备份首次安装前的本设备输入法配置，恢复入口为“恢复原设置.cmd”。仅停用模块不会立即撤销本次会话的内存修改。旧专用模块或已修复但缺少原配置备份的设备，需要先按旧方案恢复后再迁移。

附件保留当前已核对的本地产物；包内历史说明中的未测状态应结合本次发布说明和最新重启验证记录阅读。此次发布没有修复上述已知问题，也没有修改 APK 或系统分区。

# 一键工具产物与构建流程

原 `module/` 和 `artifacts/releases/mumu-ime-allow-com-ac-installed.zip` 保持为原设备的实测证据。原回退脚本包含该设备的原输入法配置，不能直接作为通用分享包。

本次新增独立的一键工具，在原核心修复外增加每设备备份、通用恢复和 Windows 入口，不改写原证据。

**2026-11-03 已知问题：现有模块和 Windows 安装流程仍会停用原搜狗输入法，用户反馈这会影响模拟器内及 UU 远程、MuMu 模拟器 APP 远程控制的中文输入和输入法弹出。问题尚未修复。** 分享前请阅读 [问题记录](07-known-input-regression.md)；两个 ZIP 的内置说明已同步补充此限制。

## 交付文件

| 文件 | 使用方式 |
| --- | --- |
| `dist/mumu-ime-share.zip` | 已有 KernelSU 的用户从管理器本地安装 |
| `dist/MuMu-IME-Windows.zip` | Windows 用户完整解压后双击 `安装.cmd`，内含模块 |
| `dist/MuMu-IME-Windows/` | 解压前的同内容便携目录，可直接查看 |
| `dist/SHA256SUMS.txt` | 两个 ZIP 的 SHA-256 |

详细用户步骤见 [Windows 使用说明](../windows/使用说明.md)。发送 Windows ZIP 最方便：用户有兼容环境时无需编译，也无需单独下载注入器。ZIP 中不附带个人设备证据、地址或原配置。

## 从项目重新构建

2026-11-03 起，后续开发和测试以 Windows 为准。在 Windows PowerShell 中执行：

```powershell
py -3 scripts/download_frida.py
py -3 scripts/build_share.py
```

构建需要 Python 3.11 或更新版本。下载脚本准备 `artifacts/bin/frida-inject`，已有匹配文件时仅校验；构建脚本校验官方二进制固定哈希，再打包，不自动连接设备或下载任何新依赖。模块 ZIP 固定条目时间，可重复构建。

`build/` 是已忽略的临时目录，可按需要清理；后续不再为测试准备 Mac PowerShell 环境。既有 `scripts/test_share.py` 依赖 POSIX shell、符号链接和带 shebang 的替身可执行文件，尚未适配原生 Windows，不能直接视为 Windows 测试入口。Windows 验证应覆盖系统自带 PowerShell 5.1、CMD 双击、实际 ADB、安装恢复及中文和远程输入；自动化测试的 Windows 适配另行处理。

源码关系：

1. 原 `module/service.sh` 原样作为分享包 `service-core.sh`，`fix.js` / `restore.js` 沿用实测内容。
2. `distribution/module/` 覆盖启动、安装检查和回退入口，新增 `backup.sh`。
3. `windows/repair.ps1` 寻找 ADB、选择实例、检查 Root 和框架指纹、验证本地文件哈希后推送固定路径的脚本。
4. `windows/device.sh` 在设备侧再次验证安装条件，并调用 KernelSU 安装、模块服务或恢复入口。
5. 构建时生成三个 CMD、校验元数据；PowerShell 文件使用 UTF-8 BOM / CRLF，设备 shell 保持 LF。

`build/`、`dist/` 与工具运行日志已加入忽略规则。项目已初始化 Git，默认分支为 `main`；构建脚本只生成本地文件。

## 恢复设计与边界

备份在 `/data/adb/mumu-ime-repair/original`，保留首次安装前的四个 secure 设置值。备份不在模块目录内，升级或卸载不主动删除；恢复校验启用列表及默认输入法。原配置中值为 `null` 的设置通过 `settings delete` 恢复。

缺少可信原配置时停止，不猜测为搜狗。目标输入法已经默认但无备份时也停止。兼容性限制为 x86_64、SDK 35 和固定框架哈希，普通 Root 不代替 KernelSU。模块与原专用模块使用相同 ID，迁移应先用旧入口恢复，再移除旧模块并重启。

框架变化后，恢复可以还原设置和停用模块，跳过不适用于新框架的运行时黑名单写回。内存修复在系统进程重启后失效，模块仅在开机时重新执行。

原设备核心修复与一键工具的测试边界不同，详见 [一键工具本地测试记录](06-sharing-tests.md)。

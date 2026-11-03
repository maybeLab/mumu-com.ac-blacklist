# MuMu 对 com.ac 输入法的黑名单：证据与修复记录

记录 2026-10-29 对 `mumu15:5555`（脱敏别名）的实际排查、Root 修复、验证和 KernelSU 模块安装过程。

**结论：该实例的系统框架同时按输入法类名和 APK 签名证书拦截按键精灵。Root 下移除 `system_server` 内存中的对应黑名单项后，按键精灵成功成为默认及实际绑定的输入法，并完成中文提交验证。**

## 已知问题：禁用原输入法影响中文和远程输入

**2026-11-03 用户反馈：禁用原搜狗输入法后，模拟器内无法输入中文，UU 远程及 MuMu 模拟器 APP 远程控制中的中文输入、弹出输入法等功能也无法正常使用。** 当前脚本仍包含停用搜狗的操作，此问题尚未修复。

此前的中文提交测试只验证了按键精灵自身的提交链路，不代表本地手动输入或远程输入正常。详细现象、恢复入口及待验证事项见 [已知中文输入与远程控制问题](docs/07-known-input-regression.md)。

## 可分享的工具

当前发布为 **v1.0.0-preview.1 预发布测试版**，仍有中文/远程输入冲突、启动异常和应用后台启动崩溃问题，不应视为稳定版。[发布说明](docs/08-release-v1.0.0-preview.1.md)列出本次验证范围和已知限制。

- [KernelSU 模块 ZIP](https://github.com/maybeLab/mumu-com.ac-blacklist/releases/download/v1.0.0-preview.1/mumu-ime-share.zip)：在 KernelSU 管理器中从本地安装。
- [Windows 一键工具 ZIP](https://github.com/maybeLab/mumu-com.ac-blacklist/releases/download/v1.0.0-preview.1/MuMu-IME-Windows.zip)：完整解压后双击 `安装.cmd`，另有 `恢复原设置.cmd` 和 `检查状态.cmd`；已包含模块和注入器，使用 MuMu 自带 ADB。
- [ZIP 校验值](https://github.com/maybeLab/mumu-com.ac-blacklist/releases/download/v1.0.0-preview.1/SHA256SUMS.txt)、[使用说明](windows/使用说明.md)、[构建与分享流程](docs/05-sharing.md)。

一键工具会备份使用者自己的原配置，不携带此实例的配置。需要 Root + KernelSU、x86_64 / Android 15，并严格匹配已验证的框架 SHA-256。**Windows 一键安装与恢复流程仍未完成实机验证**；本地模拟测试范围见 [测试记录](docs/06-sharing-tests.md)。

**2026-11-03 实际重启补测：已有分享版模块在重启后自动解除黑名单并选中按键精灵，但启动日志先报失败后成功；实际输入验证出现应用后台服务启动异常与崩溃，中文提交未通过。** 本次未手动重新应用修复，也未重新安装模块，不能将该结果表述为完整功能或稳定性验证通过。详见 [实际重启验证记录](evidence/reboot-validation-2026-11-03.md)。

## 2026-10-29 排查时的状态

| 项目 | 已观察结果 |
| --- | --- |
| 实际系统 | Android 15 / SDK 35，MuMu 6.8.8.0，x86_64 |
| 默认、实际绑定的输入法 | `com.ac/com.ime.input.InputKb` |
| 启用列表 | 仅按键精灵；搜狗应用保留、输入法停用 |
| 中文提交 | 调用按键精灵自身的提交方法后，测试框出现完整中文 |
| 回退与重应用 | 均已测试通过 |
| 开机模块 | `mumu_ime_allow_com_ac` 已安装并启用，安装后脚本手动运行成功 |
| 重启验证 | **尚未进行**；采集时模块仍为 `update=true`，位于 `modules_update` |

`mumu15` 是公开文档使用的脱敏别名，`192.0.2.1` 是替代真实 IP 的文档示例地址；命令中的设备地址请按自己的环境替换。实际系统版本以上表设备属性和文件指纹为准。

## 阅读顺序

1. [黑名单证据与原理](docs/01-evidence.md)：原始日志、静态指令引用、运行时数组与集合、证书匹配。
2. [修复步骤](docs/02-repair.md)：准备、一次性修复、切换输入法、打包及安装模块。
3. [测试方法与实测结果](docs/03-testing.md)：状态检查、中文输入、回退、幂等性与待完成的重启验证。
4. [流程、回退与维护](docs/04-operation.md)：实际时间线、启动流程、恢复命令、版本变化和排错。
5. [一键工具产物与构建](docs/05-sharing.md)、[一键工具本地测试](docs/06-sharing-tests.md)：通用备份恢复、Windows 入口、打包和测试边界。
6. [已知中文输入与远程控制问题](docs/07-known-input-regression.md)：2026-11-03 用户反馈，禁用原输入法的功能影响。

原始文件来源见[证据索引](evidence/README.md)，本次项目文件核对结果见[校验记录](evidence/project-validation.md)。

## 项目内容

```text
docs/                      完整中文说明
evidence/original/         修复前日志、输入法状态、中文测试 UI XML
evidence/static/           按 DEX 指令边界解析的引用证据
evidence/observed/         整理项目时重新采集的修复后状态
evidence/artifact-manifest.json
                           系统文件、注入器、已安装 ZIP 的来源及 SHA-256
scripts/                   提取、只读检查、修复、输入测试、恢复入口、下载和打包工具
module/                    与设备上已安装包一致的模块源码
distribution/module/       一键工具覆盖脚本，每设备备份及通用恢复
windows/                   Windows 工具源码及使用说明
dist/                      本地生成的模块 ZIP、Windows ZIP 和校验值
artifacts/original/        原始系统 JAR/APK 快照
artifacts/bin/             官方 frida-inject 16.7.19 Android x86_64
artifacts/releases/        本次实际安装的模块 ZIP
```

`artifacts/` 和 `dist/` 中的二进制已保存于本机项目目录，并由 `.gitignore` 排除；文档、脚本、日志、哈希清单保留为普通项目文件。没有复制未完整下载的 Python wheel、虚拟环境或未使用的 frida-server。

## 立即恢复原配置

在运行 ADB 的电脑上执行：

```shell
adb -s mumu15:5555 shell sh /data/adb/mumu-ime-repair/rollback.sh
```

该入口会停用模块，自动区分安装暂存目录和已激活目录，恢复搜狗默认、原启用列表及黑名单内存项。详见[回退流程](docs/04-operation.md)。

## 后续开发与测试环境

2026-11-03 约定：后续在 Windows 上开发和测试，优先验证 Windows PowerShell 5.1、MuMu 自带 ADB 及真实模拟器流程。`build/` 仅保存可清理的临时构建和测试文件，已加入 Git 忽略；不为后续测试重新下载或建立 Mac PowerShell 环境。此前 macOS 模拟测试保留为历史记录，不等同于 Windows 实机验证。

Windows 构建入口见 [构建流程](docs/05-sharing.md#从项目重新构建)。现有模拟测试脚本仍依赖 POSIX 环境，尚未适配原生 Windows。

## 适用范围

修复通过官方 `frida-inject` 直接附加到 Root 设备的 `system_server`，修改两个 Java 集合。未写入系统分区、替换系统 JAR、修改 APK 或重签名应用，也未启动 Frida 网络监听服务。

内存修改会在 `system_server` 重启后消失。模块用于下次开机重新应用；当前模块不监控系统服务运行期间的异常重启。模块只验证 `framework.jar` 的固定 SHA-256，不表示所有 MuMu 版本均兼容。

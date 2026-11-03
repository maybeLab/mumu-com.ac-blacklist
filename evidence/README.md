# 证据来源和阅读说明

除单独标明日期的补充记录外，设备观察来自 2026-10-29 对 `mumu15:5555`（脱敏别名）的授权排查。PID 和时间只标识当次系统会话。

2026-11-03 为公开项目对说明文档和清单中的主机名、IP 做了脱敏：设备统一称为 `mumu15`，IP 以 `192.0.2.1` 文档示例地址代替。它们不是实际连接标识；`artifact-manifest.json` 的设备字段已同步使用别名，系统文件、注入器和安装包的指纹仍对应原始字节。

## 2026-11-03 实际重启补测

[reboot-validation-2026-11-03.md](reboot-validation-2026-11-03.md) 记录一次授权重启、前后 boot ID、已有分享版模块的文件哈希、新启动日志及实际输入验证。自动解除黑名单和选择默认输入法成功，但日志先失败后成功，输入验证出现应用后台服务启动异常；不作为完整功能通过记录，不改写原始证据。

## 原始保留文件：original/

| 文件 | 来源及用途 |
| --- | --- |
| `before.txt` | 修复前连续执行设置查询及停用包查询的原始输出；前六项含义见修复步骤 |
| `blocked-switch.log` | 修复前 logcat 中两个 MuMuIMETrace 拦截记录，保留 PID/UID |
| `input-method-before.txt` | 修复前完整 `dumpsys input_method` 输出，含实际绑定和服务信息 |
| `verified.xml` | 中文测试成功后的 UI 树，地址栏文本已核对 |
| `legacy-static-scan.txt` | 最早的启发式代码扫描，含假阳性；只用于记录定位过程 |

## 后续重新采集：observed/

- `device-status.txt`：项目整理时的设备属性、Root 身份和输入法设置；第一行为设备采集时间。
- `runtime-after-fix.txt`：新的只读检查脚本读取的原始数组、修复后集合、签名和检查结果。
- `input-method-after.txt`：修复后完整输入法转储。
- `settings-provider-host.txt`：从 providers 转储中筛选的宿主关系，说明 SettingsProvider 与输入法服务同进程。
- `modules.json`：KernelSU 列表，体现已安装、启用、尚待启动激活。
- `installed-module-last-run.log`：复制自安装暂存目录，不是重启日志。

## 可重现的静态输出：static/

四份系统报告来自本地原始 JAR/APK，经 `scripts/inspect_dex.py` 重新生成。工具按 DEX 指令边界提取引用，不是完整反编译。`automation-helper.txt` 来自本次输入测试使用的应用 APK，说明辅助方法调用了 `commitText`；该 APK 未复制到项目，指纹记录在清单中。

## 二进制与校验

`artifact-manifest.json` 保留原系统文件、官方注入器和实际安装 ZIP 的来源、字节数、SHA-256，以及应用包和原下载压缩包的指纹。本地原件在 `artifacts/`，该目录不纳入默认 Git 跟踪。

本项目没有生成伪造的“修复前运行时 JSON”或“重启成功日志”。没有独立原始文件的终端观察均在文档中标明为当次会话摘录。

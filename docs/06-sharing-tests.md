# 一键工具本地测试记录

日期：2026-10-29。此次任务只生成本地产物，未连接或操作原模拟器。

## 已通过的测试

执行 `python3 scripts/test_share.py`，结果 **26 项通过、0 项跳过**。完整输出见 [sharing-local-tests.txt](../evidence/sharing-local-tests.txt)。

| 范围 | 验证内容 |
| --- | --- |
| 原配置备份 | 首次捕获四个值；重复捕获不覆盖；原值 null 恢复为删除；读取失败不提交备份 |
| 缺少可信原状态 | 已修复却无备份、备份不完整、恢复时无备份均停止 |
| 核心启动脚本 | 成功选择目标输入法、停用搜狗、保留其他输入法；框架不匹配和注入失败不切换输入法 |
| 通用回退 | 恢复本设备原配置、设置停用标记、检查运行时恢复标记；注入失败返回失败 |
| 框架升级后恢复 | 恢复原输入法设置，跳过旧版运行时注入 |
| 设备侧入口 | 接受目标与其他输入法共存；旧模块缺备份拒绝安装；缺备份或回退失败不报成功 |
| Windows 宿主逻辑 | ADB 路径及工具路径有空格、中文；直接 Root 与 su；多个实例显式选择 |
| 安装前拦截 | 错误 ABI、SDK、框架、无 Root、多实例未选、无在线设备、offline 均在上传前停止 |
| 宿主错误处理 | 设备脚本失败、缺少完成标记、脚本哈希篡改不报成功；超时结束当前 ADB 客户端并提示先检查状态 |
| 状态及恢复 | 状态不上传或写入设备；恢复仅上传辅助脚本，不上传模块，也不要求原框架指纹 |
| 原生参数传递 | 空字符串、中文空格、尾反斜杠、引号、反斜杠加引号、shell 特殊字符均原样传递 |
| 包内容 | ZIP 完整性及条目唯一；官方注入器哈希、核心脚本来源、本地元数据校验；PS BOM/CRLF、CMD CRLF、设备 shell LF |

另外通过 shell `sh -n`、JavaScript `node --check`、PowerShell 官方解析器语法检查。原 `module/` 与实际安装 ZIP 的同名源文件已逐一核对一致，原证据未改写。

再次构建两个 ZIP 后 SHA-256 均保持一致；分享包覆盖脚本与源码逐一核对一致。2026-10-29 构建产物的文件大小、哈希及测试边界见 [sharing-artifacts.json](../evidence/sharing-artifacts.json)。

2026-11-03 补充了 [禁用原输入法的功能影响](07-known-input-regression.md)，并同步更新两个 ZIP 内的使用说明；这些本地模拟测试不能证明本地中文或远程输入可用。当日说明更新后的打包核对及哈希见 [sharing-artifacts-2026-11-03.json](../evidence/sharing-artifacts-2026-11-03.json)。

同日统一工具名称后的打包核对及哈希见 [one-click-artifacts-2026-11-03.json](../evidence/one-click-artifacts-2026-11-03.json)。当前 ZIP 的校验值以 `dist/SHA256SUMS.txt` 为准。

## 测试环境和替身

测试运行于 macOS；PowerShell 使用官方便携版 7.6.9 arm64，下载包 SHA-256：

`a1c7e98ac403da4be5ba75c1c5855af272de7787a91d478c4267466fe58fc1af`

来源：https://github.com/PowerShell/PowerShell/releases/download/v7.6.9/powershell-7.6.9-osx-arm64.tar.gz

工具源码约束为 Windows PowerShell 5.1 可用语法和 API，但此处并未运行 Windows PowerShell 5.1。测试中的 ADB、settings、ime、属性、KernelSU 和注入器均为本地替身，不会连接任何设备或运行 Android 注入器。测试中的 KernelSU 安装使用成功/失败替身，不代表真实 KernelSU ZIP 安装实测。

历史模拟脚本使用 PATH 中的 `pwsh`、环境变量 `PWSH`，或当时本项目中的 `build/qa/pwsh/pwsh`。若找不到，将明确跳过宿主测试；不能把跳过当作通过。这些路径是原测试环境的记录，不要求后续恢复该 Mac 环境。

## 2026-11-03 后续测试约定

用户指定后续在 Windows 上开发和测试，不再为后续测试下载或建立 Mac PowerShell 环境。`build/` 作为临时目录，可清理且不纳入 Git；本章 26 项 macOS 模拟测试继续作为历史记录保留。

现有 `scripts/test_share.py` 依赖 POSIX shell、符号链接和 shebang 替身程序，尚未适配原生 Windows，不能因测试环境改为 Windows 就视为脚本已经可用。后续需要在 Windows 实际验证工具运行，或单独适配自动化测试。

## 仍需真实环境验证

- 在兼容的独立模拟器中安装本次分享模块 ZIP，包括 KernelSU 安装钩子和备份权限。
- Windows 10/11 自带 PowerShell 5.1、实际 MuMu ADB、CMD 双击、目录自动发现及 Root 授权弹窗。
- 重启后模块自动执行、默认和实际绑定输入法、按键精灵实际输入文字。
- 从暂存目录切换到正式模块目录之后，再次恢复与卸载。

原设备的旧专用版核心修复、中文提交及回退已经实测，详见 [原设备测试](03-testing.md)；不能用这些结果代替本次一键工具的完整实机验证。

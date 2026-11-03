# 2026-11-03 实际重启验证

北京时间 2026-11-03 22:41—22:46，经用户授权，通过 Windows 主机 ADB 对指定模拟器执行了一次重启。公开记录使用 `mumu15:5555` 脱敏别名。以下输出为本次终端采集摘录，不是完整原始转储。

## 结果

| 检查项 | 结果 |
| --- | --- |
| 实际重启 | 通过：boot ID 改变，重连后启动完成 |
| 开机自动解除黑名单、选择默认输入法 | 通过一次实测，没有手动重新应用修复 |
| 启动过程无异常 | 未通过：同一新日志先报告失败，后报告成功，原因未定位 |
| 实际输入服务及中文提交 | 未通过本次验证：应用崩溃、提交测试超时，没有验证到文字 |
| 本地手动中文、两种远程输入 | 未测 |
| Windows 一键安装、恢复和连续重启稳定性 | 未测 |

## 环境与重启

- 主机为 Windows、PowerShell 7.6.9，使用本机 platform-tools 的 ADB。
- 设备属性为 SM-A5360、x86_64、SDK 35、V417IR release-keys，Root，SELinux Permissive。型号属性不作为物理设备身份判定依据。
- framework.jar SHA-256 为 `5a46d36ebaf9b8088dc24b3601e7365123b6b258126ef4477fa6524b566fe349`，匹配项目要求。
- 测试前已经安装分享版模块，位于 `/data/adb/modules/mumu_ime_allow_com_ac`，`enabled=true`、`update=false`、`remove=false`。本次未重新安装模块。
- 本设备原配置备份的四个设置文件及 complete 标记存在；未覆盖或恢复备份。
- 已安装 com.ac：versionCode 2024092009、versionName 6.7.3。
- 初次连接 offline，仅断开并重连指定地址后恢复在线，没有重启 ADB 服务或操作其他设备。

已安装核心文件与本地来源逐项 SHA-256 一致：

| 已安装文件 | 本地来源 | SHA-256 |
| --- | --- | --- |
| service.sh | distribution/module/service.sh | `e45f52e97ea4fad13330da70698c385f94aa16ecf74f11e90f8ac663e91526ac` |
| service-core.sh | module/service.sh | `53ee601ee9de89b664729fbbbae2cd26a72b633d5fbb2ac9c8c44de4f113c83a` |
| fix.js | module/fix.js | `0f233f9639e90258a6d897efd5726d2e95b1f276275aaec5173f0e4909466b4b` |
| backup.sh | distribution/module/backup.sh | `5ec9eee7abfd043845ff37b41c55ea43bccf8db2b02bcd6165a261a177ff28be` |

22:42:19 记录重启前状态，22:42:21 发出 `adb -s mumu15:5555 reboot`。22:42:52 确认重新在线和启动完成，额外等待 20 秒后采集自动运行结果。

| 状态 | boot ID | /proc/uptime |
| --- | --- | --- |
| 重启前 | `159cf07d-772f-403c-9d97-b829e6b2d854` | 55.46 146.42 |
| 重启后，22:43:12 | `e99c7833-73de-418f-8726-70c01eba3174` | 38.10 102.35 |

重启后 sys.boot_completed=1，模块保持启用、update=false，不存在该模块的暂存目录、disable 或 remove 标记。没有手动执行 service.sh、service-core.sh、action.sh 或 fix.js。

## 新启动日志

```text
Tue Nov  3 22:42:49 CST 2026
Unable to load SELinux policy from the kernel: Failed to open file ?/sys/fs/selinux/policy?: Device or resource busy
Process not found
Runtime patch did not report success; skipped IME changes.
MUMU_IME_FIXED {"pid":848,"changes":[{"field":"sImeClasses","value":"com.ime.input.InputKb","removed":true},{"field":"sCertSha256","value":"9b200e7758e811605c957322c6865bb34989e79b363ad39895c7e4ef40976a96","removed":true}],"blocked":false}
Input method com.ac/com.ime.input.InputKb: already enabled for user #0
Input method com.ac/com.ime.input.InputKb selected for user #0
Input method com.sohu.inputmethod.sogou.chuizi/com.sohu.inputmethod.sogou.SogouIME: now disabled for user #0
SUCCESS: automation IME selected.
```

默认输入法、启用列表和 ime list -s 均为 `com.ac/com.ime.input.InputKb`。本次确认重启依据 boot ID，不是 system_server PID 的变化。日志先失败后成功的原因尚未定位，不能据此宣称启动过程无异常。

## 实际输入验证与阻塞

自动运行证据采集后，打开 com.android.chromium 的 about:blank，通过 UI 树定位地址栏并点击中心获取焦点；没有发送回车或提交网页请求。输入状态为：

```text
mSelectedMethodId=com.ac/com.ime.input.InputKb
mCurId=com.ac/com.ime.input.InputKb
mBoundToMethod=false
mInputShown=false
```

上传现有 scripts/test_input.js，通过模块自带 frida-inject 对 com.ac:enginfloat 执行提交测试。它只调用应用的文字提交方法，不修改系统黑名单；固定测试文字仍为 MuMu输入法修复验证20261029，不代表本次测试日期。

测试退出码为 124，没有 MUMU_IME_TEXT_SUBMITTED。随后 UI 树显示“火鸡”屡次停止运行弹窗，无法定位地址栏核对文字，因此中文提交不算通过。

崩溃缓冲区摘录如下；异常消息截到 app is in background，后续 UID 状态和堆栈省略：

```text
11-03 22:44:28.360 E AndroidRuntime: Process: com.ac:enginfloat, PID: 2252
java.lang.RuntimeException: Unable to create application com.cyjh.elfin.base.AppContext: android.app.BackgroundServiceStartNotAllowedException: Not allowed to start service Intent { cmp=com.ac/com.cyjh.mq.service.IpcService }: app is in background
11-03 22:44:29.380 E AndroidRuntime: Process: com.ac, PID: 2376
java.lang.RuntimeException: Unable to create application com.cyjh.elfin.base.AppContext: android.app.BackgroundServiceStartNotAllowedException: Not allowed to start service Intent { cmp=com.ac/com.cyjh.mq.service.IpcService }: app is in background
```

应用退出记录也包含本次 22:44 的 APP CRASH(EXCEPTION)。仅解除黑名单并恢复默认值不足以证明重启后的实际输入链路正常。本次未修改后台限制、权限、系统策略或 APK。

测试结束时模块仍启用，默认及启用列表仍为按键精灵，搜狗仍停用。没有执行恢复、卸载或手动重新应用修复。

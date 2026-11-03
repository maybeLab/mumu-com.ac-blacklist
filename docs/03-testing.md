# 测试方法与实测结果

测试分为“设置已改变”“服务实际绑定”“应用能提交中文”三个层次。仅看到 `ime set` 成功不足以证明原来的文字提交问题已经解决。

本章命令中的 `mumu15:5555` 是脱敏别名，复现时请替换成自己的设备地址。

**2026-11-03 补充：用户反馈禁用原输入法会导致模拟器内、UU 远程及 MuMu 模拟器 APP 远程控制的中文输入、输入法面板等功能不可用。** 第 1—4 节实测结果来自 2026-10-29，仅覆盖按键精灵自身提交链路，不代表这些输入场景通过；详见 [已知问题记录](07-known-input-regression.md)。2026-11-03 的实际重启补测见第 5 节。

## 1. 测试结果清单

| 测试 | 2026-10-29 结果 | 记录位置或来源 |
| --- | --- | --- |
| 修复前普通切换 | 失败，被黑名单拒绝 | 会话摘录及 `original/blocked-switch.log` |
| 修复前直接写默认设置 | 被阻止，仍为搜狗 | 原始日志与 `original/before.txt` |
| 类名及证书规则定位 | 两条都命中 | 静态证据、运行时原始数组及签名 |
| 首次内存修复 | 两项 `removed=true`，类名检查为 false | 会话摘录，见修复步骤 |
| 默认和启用列表 | 仅按键精灵 | `observed/device-status.txt` |
| 实际服务绑定 | `mSelectedMethodId`、`mCurId` 均为按键精灵 | `observed/input-method-after.txt` |
| 中文提交 | 完整文字进入测试框 | `original/verified.xml` |
| 恢复旧状态 | 默认恢复搜狗，按键精灵再次被拒绝 | 当次会话摘录，本章第 4 节 |
| 重应用/重复应用 | 可再次切换；重复删除为 false 仍成功 | `observed/installed-module-last-run.log` |
| 安装后脚本 | 从 `modules_update` 手动运行成功 | 同上及 `observed/modules.json` |
| 独立恢复入口 | 已部署并通过 shell 语法检查 | 尚未执行整个已安装模块停用入口 |
| 实际卸载 | 未执行 | 仅提供卸载恢复脚本 |
| 重启后的自动执行 | **未测试** | 保留待执行步骤，不能算通过 |

本章相对证据路径均以 `evidence/` 为根。

## 2. 检查设置和实际绑定

在 Android shell 中：

```sh
settings get secure default_input_method
settings get secure enabled_input_methods
dumpsys input_method
```

预期前两条输出均为 `com.ac/com.ime.input.InputKb`，转储中包含：

```text
mSelectedMethodId=com.ac/com.ime.input.InputKb
mCurId=com.ac/com.ime.input.InputKb
Input method service state for com.ime.input.InputKb@...
```

最终整理时再次读取的运行时集合中，`sImeClasses`、`sCertSha256` 均为空，`sPackages` 仍为 `com.xyzywqn.wlq`，说明注入会话退出后修改仍存在。

## 3. 中文输入：通过按键精灵自身方法提交

### 为什么这样测

使用 `adb shell input text` 会走其他注入路径，不能验证按键精灵的输入法是否接管。本次调用应用自身的文字提交辅助方法：

```text
com.ime.input.a.a()              取得辅助对象
com.ime.input.a.a(String)        提交文字
InputMethodService.getCurrentInputConnection()
InputConnection.commitText(...)
```

方法引用证据见 [automation-helper.txt](../evidence/static/automation-helper.txt)，测试脚本见 [test_input.js](../scripts/test_input.js)。脚本通过 `Java.scheduleOnMainThread` 在应用主线程调用该方法。

这验证了输入法实例、当前输入连接及该应用的文字提交链路；**没有运行用户原来的整套游戏自动化脚本**。辅助方法 `a` 是本次 APK 中的混淆名称，换包或升级后必须重新确认。实际测试包版本码为 `2024092009`，APK SHA-256 见清单的 `observed_application`；项目不附带该 APK。

### 重现步骤

在主机 PowerShell 中打开本地空白页，并上传脚本：

```powershell
adb -s mumu15:5555 shell am start -a android.intent.action.VIEW -d about:blank -p com.android.chromium
adb -s mumu15:5555 push scripts/test_input.js /data/local/tmp/mumu-ime/test_input.js
adb -s mumu15:5555 shell
```

在设备上点击地址栏，使其获得输入焦点。本次屏幕为 1280×720，曾使用 `input tap 400 80`；其他分辨率应根据实际 UI 定位，不能固定照抄坐标。

Android shell：

```sh
pidof com.ac:enginfloat
timeout 10 /data/local/tmp/mumu-ime/frida-inject -p "$(pidof com.ac:enginfloat)" -s /data/local/tmp/mumu-ime/test_input.js
uiautomator dump /data/local/tmp/mumu-ime-verified-new.xml
```

回到主机：

```powershell
adb -s mumu15:5555 pull /data/local/tmp/mumu-ime-verified-new.xml verified-new.xml
```

日志应出现 `MUMU_IME_TEXT_SUBMITTED`，但此标记只表示调用完成，还要核对 XML 中 `com.android.chromium:id/url_bar` 的 `text` 是否严格为：

```text
MuMu输入法修复验证20261029
```

本次实际保存的 [verified.xml](../evidence/original/verified.xml) 已核对相等。没有按回车或提交网页请求。验证结束后按返回键取消地址栏编辑，并打开 `android.settings.INPUT_METHOD_SETTINGS`。

排查期间，较早两次 `uiautomator dump` 在写出 XML 后提示过 `Segmentation fault`；最终中文验证的 XML 采集成功。复现时应核对新文件确实产生、目标节点和文字确实正确，不能仅凭“dump 已输出”的提示判断成功。

## 4. 回退、重应用与幂等性

当时在 `/data/local/tmp/mumu-ime-module-validation` 中使用与安装包相同的脚本做了受控测试：

1. 执行 `rollback.sh`，重新启用搜狗、设为默认、恢复启用列表和子类型，并把原类名与证书项加回集合。
2. 日志出现 `MUMU_IME_RESTORED`。
3. 回读默认为搜狗、启用列表恢复两项。
4. 再执行 `ime set com.ac/com.ime.input.InputKb`，重新得到 `is blacklisted and cannot be selected`，证明恢复不仅改变界面设置，也恢复了拦截。
5. 移除该测试目录的 `disable` 标记并运行 `service.sh`，两项再次成功移除，默认和启用列表恢复为按键精灵。
6. 安装模块后再手动运行一次，两项 `removed=false`，但 `blocked=false`、切换和最终状态均正确，验证重复应用可行。

这段回退输出是会话摘录，没有冒充为单独采集的原始日志。安装后重复运行的真实日志已保存。该次测试中按键精灵提交链路工作正常，不等于所有中文和远程输入功能正常；后续使用问题见前述 2026-11-03 补充。

## 5. 重启自动修复验证

2026-10-29 没有重启实例，当时的自动启动验证保持“未测试”记录。

2026-11-03 经授权实际重启一次已安装分享版模块的设备：boot ID 改变，新启动日志显示自动解除两项黑名单并选中按键精灵，全程未手动重新应用修复。但同一日志先报失败后成功，实际输入验证又发现 com.ac 因 BackgroundServiceStartNotAllowedException 崩溃，中文提交未通过。环境、文件哈希和输出摘录见 [实际重启验证记录](../evidence/reboot-validation-2026-11-03.md)。

以下步骤用于复现和后续稳定性验证，不能把自动选中输入法等同于完整输入功能通过：

1. 重启前记录 `cat /proc/sys/kernel/random/boot_id`、`cat /proc/uptime` 和当前模块日志时间。
2. 在可以中断当前模拟器任务时重启安卓实例，等待 ADB 重新连通、`sys.boot_completed=1`，再给启动脚本完成注入和切换的时间。
3. 确认 boot ID 已变化，模块从暂存阶段激活，`module list` 中 `update` 不再为 true。
4. 读取 `/data/adb/modules/mumu_ime_allow_com_ac/last-run.log`，必须是此次启动的新日志，含 `MUMU_IME_FIXED` 和末行 `SUCCESS: automation IME selected.`。
5. 重新完成默认/实际绑定检查和中文提交测试。

PID 可能在不同启动中被重复分配，不能只以 PID 是否变化判断发生过重启。若自动修复失败，应保存当次日志，不应把手动重新应用的成功结果当作自动启动成功。

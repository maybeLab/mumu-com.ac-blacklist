# 修复步骤与模块构建

本章说明本次实际使用的方法。当前设备已经修复，重现时无需为了“重做流程”重复修改。只有在对应测试或重新安装确有需要时才执行写操作。

## 1. 工具和执行位置

- `mumu15:5555` 是脱敏后的示例设备地址；执行命令前请替换成自己的 ADB 地址，或使用自己配置的同名别名。
- Windows 上准备 Android platform-tools 的 `adb`；项目脚本需要 Python 3.11 或更高版本，只使用标准库。
- 主机命令示例采用 PowerShell；在 macOS/Linux 上将 `py -3` 换为 `python3`，并按本机路径进入项目。
- 标记为“Android shell”的命令，应先运行 `adb -s mumu15:5555 shell`，进入设备后再执行。这样可避免 Windows CMD、PowerShell 与 zsh 之间的引用和变量展开差异。
- `843`、`2882` 等 PID 只属于本次观察，操作时必须重新查询。

PowerShell：

```powershell
Set-Location 'C:\path\to\mumu-com.ac-blacklist'
adb connect mumu15:5555
adb devices -l
adb -s mumu15:5555 shell id
adb -s mumu15:5555 shell getprop ro.product.cpu.abi
```

本次 ADB shell 本身就是 Root，无需再执行 `adb root` 或改变 SELinux 状态。其他环境若不是 Root，应在设备 shell 中通过已经配置的 `su` 获取权限后检查；不能假设当前 Frida 二进制兼容其他 ABI。

## 2. 备份和版本核对

本次修复前保存了以下设置：

```sh
# Android shell；结果按顺序保存到本案的 before.txt。
settings get secure default_input_method
settings get secure enabled_input_methods
settings get secure selected_input_method_subtype
settings get secure input_methods_subtype_history
settings get secure show_ime_with_hard_keyboard
pm list packages -d
```

系统文件通过 `adb pull` 保存。项目已经保留当时的文件，新版本不要覆盖这些基线：

```powershell
adb -s mumu15:5555 pull /system/framework/framework.jar artifacts/original/framework.jar
adb -s mumu15:5555 pull /system/framework/services.jar artifacts/original/services.jar
adb -s mumu15:5555 pull /system/priv-app/SettingsProvider/SettingsProvider.apk artifacts/original/SettingsProvider.apk
```

Android shell 中核对：

```sh
getprop ro.build.version.release
getprop ro.build.version.sdk
getprop nemud.player_version
sha256sum /system/framework/framework.jar
```

本案框架 SHA-256 必须为 `5a46d36ebaf9b8088dc24b3601e7365123b6b258126ef4477fa6524b566fe349`。一次性 JS 本身不做版本指纹校验，因此必须先核对；模块的 `service.sh` 则会在注入前核对。

## 3. 准备注入器与只读检查

采用官方 [frida-inject 16.7.19 Android x86_64](https://github.com/frida/frida/releases/download/16.7.19/frida-inject-16.7.19-android-x86_64.xz)。本案二进制已放在 `artifacts/bin/frida-inject`，来源及压缩包/二进制哈希保存在清单中。

缺失二进制时可下载并校验；已存在且哈希正确时不会重新下载：

```powershell
py -3 scripts/download_frida.py
adb -s mumu15:5555 shell mkdir -p /data/local/tmp/mumu-ime
adb -s mumu15:5555 push artifacts/bin/frida-inject /data/local/tmp/mumu-ime/frida-inject
adb -s mumu15:5555 push scripts/inspect_runtime.js /data/local/tmp/mumu-ime/inspect.js
adb -s mumu15:5555 push module/fix.js /data/local/tmp/mumu-ime/fix.js
adb -s mumu15:5555 shell chmod 700 /data/local/tmp/mumu-ime/frida-inject
adb -s mumu15:5555 shell
```

进入 Android shell 后：

```sh
pidof system_server
timeout 10 /data/local/tmp/mumu-ime/frida-inject -p "$(pidof system_server)" -s /data/local/tmp/mumu-ime/inspect.js
```

检查输出中的原始数组、实际集合、应用证书及 `classBlocked` / `certificateBlocked`。原始未修复状态应命中对应规则；当前修复后的实际输出在项目中是两个 `false`。

`frida-inject` 执行脚本后会保持会话，故使用 `timeout 10` 退出。**退出码 124 只表示达到设置的时限，不单独代表修复失败。** 必须结合成功标记、后续输入法状态及系统进程是否仍正常判断。脚本遇到异常会输出 `MUMU_IME_ERROR`。

不使用 `-e/--eternalize`，也不启动 frida-server。集合修改可以在注入会话结束后保留，无需保留 JS hook。

## 4. 一次性内存修复

Android shell：

```sh
timeout 10 /data/local/tmp/mumu-ime/frida-inject -p "$(pidof system_server)" -s /data/local/tmp/mumu-ime/fix.js
```

`fix.js` 的实际逻辑为：

1. 取得 `android.app.MuMuImeBlackList`，读取 `com.ac` 的签名证书并计算 SHA-256。
2. 从 `sImeClasses` 移除 `com.ime.input.InputKb`。
3. 从 `sCertSha256` 移除与当前 `com.ac` 签名匹配的哈希。
4. 保留 `sPackages` 和原始静态数组，输出删除结果及类名/包名检查结果。

首次执行实际输出摘录自当次会话：

```json
{"pid":843,"changes":[{"field":"sImeClasses","value":"com.ime.input.InputKb","removed":true},{"field":"sCertSha256","value":"9b200e7758e811605c957322c6865bb34989e79b363ad39895c7e4ef40976a96","removed":true}],"blocked":false}
```

日志前缀为 `MUMU_IME_FIXED`。其中 `blocked` 来自 `isImeBlacklisted()`，只表示类名/包名检查；证书集合的状态需要结合删除结果或只读检查中的 `certificateBlocked` 判断。重复执行时 `removed=false` 可以表示目标早已移除，不能据此判失败。

## 5. 切换默认输入法

确认修复成功后，在 Android shell 中执行：

```sh
ime enable com.ac/com.ime.input.InputKb
ime set com.ac/com.ime.input.InputKb
settings get secure default_input_method
ime disable com.sohu.inputmethod.sogou.chuizi/com.sohu.inputmethod.sogou.SogouIME
settings get secure enabled_input_methods
dumpsys input_method
```

两次 `settings get` 都应输出 `com.ac/com.ime.input.InputKb`；转储中的 `mSelectedMethodId`、`mCurId` 应一致，服务实例应为 `com.ime.input.InputKb`。先确认切换成功，再停用搜狗输入法。本次没有卸载搜狗应用。

## 6. 构建与安装 KernelSU 模块

`module/` 是已安装版本的源码快照。`scripts/fix_runtime.js` 与 `module/fix.js` 内容一致，前者保留排查入口，后者用于模块打包。

PowerShell：

```powershell
py -3 scripts/build_module.py
adb -s mumu15:5555 push build/mumu-ime-allow-com-ac.zip /data/local/tmp/mumu-ime-allow-com-ac.zip
adb -s mumu15:5555 shell /data/adb/ksud module install /data/local/tmp/mumu-ime-allow-com-ac.zip
adb -s mumu15:5555 shell /data/adb/ksud module list
```

模块 ZIP 包含官方注入器、JS、启动/恢复/卸载脚本和 `skip_mount`；`customize.sh` 设置 Root 所有权及执行权限。构建工具会校验注入器哈希和 ZIP 完整性，不安装或重启设备。

本次实际安装输出为 `Module installed successfully!`，安装目录是 `/data/adb/modules_update/mumu_ime_allow_com_ac`。已安装 ZIP 原件保存在 `artifacts/releases/mumu-ime-allow-com-ac-installed.zip`。重新打包的成员内容可以相同，但 ZIP 时间戳和容器 SHA-256 不保证相同。

安装后尚未重启，本次从暂存目录手动运行脚本并成功：

```sh
# Android shell；仅适用于首次安装后仍在 modules_update 的阶段。
sh /data/adb/modules_update/mumu_ime_allow_com_ac/service.sh
cat /data/adb/modules_update/mumu_ime_allow_com_ac/last-run.log
```

若已经通过一次启动激活模块，路径应改为 `/data/adb/modules/mumu_ime_allow_com_ac`，不要继续假设暂存目录存在。

## 7. 保存独立恢复入口

本次已经安装的入口是 `/data/adb/mumu-ime-repair/rollback.sh`。在新设备复现时可部署：

```powershell
adb -s mumu15:5555 shell mkdir -p /data/adb/mumu-ime-repair
adb -s mumu15:5555 push scripts/rollback-installed.sh /data/adb/mumu-ime-repair/rollback.sh
adb -s mumu15:5555 shell chmod 700 /data/adb/mumu-ime-repair /data/adb/mumu-ime-repair/rollback.sh
```

后续验证和完整回退见下一章；本章记录的安装操作不等于已完成重启验证。

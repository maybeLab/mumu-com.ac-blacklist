# 黑名单证据与作用原理

## 1. 环境和标识

| 项目 | 值 |
| --- | --- |
| ADB 设备（脱敏别名） | `mumu15:5555` |
| 设备 IP（脱敏示例，非实际地址） | `192.0.2.1` |
| Android / SDK | `15` / `35` |
| MuMu 属性 `nemud.player_version` | `6.8.8.0` |
| ABI | `x86_64` |
| ADB shell 身份 | `uid=0(root)`，上下文 `u:r:ksu:s0` |
| SELinux 状态 | `Permissive`，排查期间未修改 |
| KernelSU CLI | `ksud 3.2.5` |
| 按键精灵输入法 | `com.ac/com.ime.input.InputKb` |
| 搜狗输入法 | `com.sohu.inputmethod.sogou.chuizi/com.sohu.inputmethod.sogou.SogouIME` |
| 搜狗 APK 路径 | `/system/priv-app/nemu-vinput-pack/nemu-vinput-pack.apk` |

2026-11-03 已对公开文档中的主机名和 IP 脱敏。`mumu15` 为别名，`192.0.2.1` 属于文档示例地址段，不是真实解析结果。设备版本、时间、PID 和文件指纹保留观察值。

原始输出见 [device-status.txt](../evidence/observed/device-status.txt)。行顺序为：设备时间、Android、SDK、MuMu 版本、ABI、身份、SELinux、ksud 版本、启动完成标记、进程 PID、默认输入法、启用列表、子类型。它是修复后重新采集的结果。

## 2. 修复前状态与系统拒绝日志

[before.txt](../evidence/original/before.txt) 前三行分别为默认输入法、启用列表和子类型：

```text
com.sohu.inputmethod.sogou.chuizi/com.sohu.inputmethod.sogou.SogouIME
com.ac/com.ime.input.InputKb:com.sohu.inputmethod.sogou.chuizi/com.sohu.inputmethod.sogou.SogouIME
1802354156
```

同时启用两个输入法不表示它们同时接管同一个输入框。修复前默认及实际绑定仍为搜狗，见 [input-method-before.txt](../evidence/original/input-method-before.txt)。

首次切换命令及结果如下，摘录自当次会话；该终端输出没有单独保存为原始日志文件：

```shell
adb -s mumu15:5555 shell ime set com.ac/com.ime.input.InputKb
```

```text
Input method com.ac/com.ime.input.InputKb is blacklisted and cannot be selected.
```

随后直接执行 `settings put secure default_input_method`，回读仍为搜狗。设备日志记录了两个拦截入口，原始文件见 [blocked-switch.log](../evidence/original/blocked-switch.log)：

```text
W/MuMuIMETrace(  843): ime set BLOCKED: blacklisted ime=com.ac/com.ime.input.InputKb userId=0 uid=0 pid=45958
W/MuMuIMETrace(  843): BLOCK blacklisted default_input_method: uid=0 pid=46024 pkg=root value=com.ac/com.ime.input.InputKb
```

`uid=0` 说明 Root 调用也被框架检查拦截；获得 Root 权限本身不会跳过判断。

## 3. 系统 DEX 中的类、初始化常量和调用

原始文件位置、字节数和 SHA-256 见 [artifact-manifest.json](../evidence/artifact-manifest.json)。关键框架指纹：

```text
framework.jar
5a46d36ebaf9b8088dc24b3601e7365123b6b258126ef4477fa6524b566fe349
```

在项目根目录运行以下命令重新生成证据，Windows 可以用 `py -3` 替代 `python3`：

```shell
python3 scripts/inspect_dex.py artifacts/original/framework.jar
python3 scripts/inspect_dex.py artifacts/original/services.jar --class-name com.android.server.inputmethod.InputMethodManagerService --method isBlacklistedIme
python3 scripts/inspect_dex.py artifacts/original/SettingsProvider.apk --class-name com.android.providers.settings.SettingsProvider --method mutateSecureSetting
```

[framework-blacklist.txt](../evidence/static/framework-blacklist.txt) 显示 `classes.dex` 中存在 `android.app.MuMuImeBlackList`。静态初始化方法 `<clinit>()V` 引用：

| 静态数组 | 初始化内容 |
| --- | --- |
| `BLACKLISTED_PACKAGES` | `com.xyzywqn.wlq` |
| `BLACKLISTED_IME_CLASSES` | `com.ime.input.InputKb` |
| `BLACKLISTED_CERT_SHA256` | `9b200e7758e811605c957322c6865bb34989e79b363ad39895c7e4ef40976a96` |

同一方法创建 `HashSet`，存入 `sPackages`、`sImeClasses`、`sCertSha256`。`getBlacklistedCertificates()` 从 `sCertSha256` 构造列表。

其他引用可交叉核对：

- [input-method-check.txt](../evidence/static/input-method-check.txt)：`InputMethodManagerService.isBlacklistedIme()` 引用类名/包名检查、证书列表、签名 SHA-256 计算与匹配；含 `BLOCK blacklisted IME certificate:` 日志常量。
- [settings-provider-mutation.txt](../evidence/static/settings-provider-mutation.txt)：`SettingsProvider.mutateSecureSetting()` 引用 `MuMuImeBlackList.isImeBlacklisted()` 及 `BLOCK blacklisted default_input_method:`，与写设置被拒绝的实际日志相符。
- [ime-resetter.txt](../evidence/static/ime-resetter.txt)：另外存在 `MuMuImeResetter.resetDefaultIme()` 和内置搜狗标识；不能仅据此推断所有触发时机，本次未修改此类。

提取器按标准 DEX 指令宽度前进，记录指令边界上的字符串、字段、类型及方法引用。它**不是完整 Java 反编译器，也不输出完整控制流**，遇到不支持的指令会报错。非 ASCII 的 MUTF-8 字符串可能显示替换字符；本案标识与哈希均为 ASCII。

最早的 [legacy-static-scan.txt](../evidence/original/legacy-static-scan.txt) 是逐 code unit 的启发式扫描，含 `possible-call` 假阳性，只保留排查历史。正式论据以上述重新生成的文件和运行时证据为准。

## 4. 原始数组、实际集合与应用签名

[inspect_runtime.js](../scripts/inspect_runtime.js) 只读字段和签名，不修改集合。它附加到 Root 设备的 `system_server`，读取静态数组、实际集合和 `com.ac` 的签名证书 SHA-256。

整理项目时重新执行的输出见 [runtime-after-fix.txt](../evidence/observed/runtime-after-fix.txt)，关键内容为：

```json
{
  "arrays": {
    "BLACKLISTED_CERT_SHA256": ["9b200e7758e811605c957322c6865bb34989e79b363ad39895c7e4ef40976a96"],
    "BLACKLISTED_IME_CLASSES": ["com.ime.input.InputKb"],
    "BLACKLISTED_PACKAGES": ["com.xyzywqn.wlq"]
  },
  "sets": {
    "sCertSha256": [],
    "sImeClasses": [],
    "sPackages": ["com.xyzywqn.wlq"]
  },
  "packageCertificates": ["9b200e7758e811605c957322c6865bb34989e79b363ad39895c7e4ef40976a96"],
  "classBlocked": false,
  "certificateBlocked": false
}
```

原始数组保留厂商规则；修复只从两个运行时集合删除目标项，包名集合没有变化。应用签名与原始证书黑名单完全相同，因此只改输入法类名也不足以绕过证书检查。

首次运行时检查还观察到 `isImeBlacklisted(...) = true`，但只有会话记录。这里重新采集的文件明确是**修复后**证据，不能当作修复前原始记录。

## 5. 为什么只需修改一个进程

[settings-provider-host.txt](../evidence/observed/settings-provider-host.txt) 显示，本实例的 SettingsProvider 托管于 `843:system/1000`，即当时的 `system_server`，与输入法管理服务同进程。因此本次修改同一份静态集合即可影响两个入口。

这是本实例的实测宿主关系。在其他版本复用前，应重新确认 SettingsProvider 的宿主进程。

# 操作时间线、启动流程与恢复维护

## 1. 2026-10-29 的实际处理顺序

以下是顺序记录；约略时段来自会话和文件时间，不是完整带时间戳的审计日志。

| 顺序 | 实际操作及观察 |
| --- | --- |
| 连接 | ADB 5555 已可用；公开记录以别名 `mumu15`、文档示例 IP `192.0.2.1` 代替真实连接信息。同一实例另有短主机名连接，因此后续均显式使用 `-s` |
| 备份 | 保存默认、启用列表、子类型、历史、硬键盘显示设置及完整输入法转储 |
| 常规切换 | `ime set` 和写默认设置分别被 MuMuIMETrace 拦截；设置没有成功改变 |
| 静态定位 | 拉取 `framework.jar`、`services.jar`，定位 `MuMuImeBlackList`、输入法管理服务检查及重置类 |
| Root 核实 | 确认 Root、ABI、SELinux 和 KernelSU；系统根分区只读，未重新挂载 |
| 运行时检查 | 官方 frida-inject 读取到静态数组、可变 Set、匹配的应用证书和被拦截状态 |
| 首次修复 | 移除类名与证书命中项，成功切换按键精灵，再停用搜狗输入法 |
| 真实文字测试 | 调用应用内部提交方法，空白页地址栏出现完整中文，保存 UI XML |
| 回退验证 | 恢复原设置和集合，确认黑名单重新生效，再次应用修复成功 |
| 模块封装 | 增加框架哈希校验、启动等待、日志和恢复脚本，验证 ZIP 完整性 |
| 安装 | 用户选择开机自动修复后，通过 `ksud module install` 安装成功 |
| 安装后验证 | 2026-10-29 13:40:18 +08:00 的脚本日志成功；随后保存恢复入口 |
| 项目整理 | 重新只读采集修复后的状态；同一系统会话仍在运行，尚未重启 |

早期尝试准备 Python/Frida 主机客户端，但下载未完成；最终使用的是设备上的独立 `frida-inject`。Python Frida 客户端和 frida-server 没有参与实际修复。

## 2. 开机模块执行流程

`module/service.sh` 的行为按顺序为：

1. 检查本模块 `disable`、`remove` 标记，存在即停止。
2. 最多等待约 120 秒，要求 `sys.boot_completed=1`。
3. 写入 `last-run.log` 的本次时间。
4. 计算 `/system/framework/framework.jar` 的 SHA-256；与本案固定值不符则停止，不注入。
5. 确认 `com.ac` 已安装，重新查询当前 `system_server` PID。
6. 以 10 秒时限运行注入器，执行 `fix.js`，随后结束注入会话。
7. 要求日志有 `MUMU_IME_FIXED` 且 `blocked=false`；确认系统进程 PID 未在这段操作中改变。
8. 启用并选中按键精灵，回读默认值，只有默认匹配才继续。
9. 停用搜狗输入法并记录 `SUCCESS: automation IME selected.`。

`skip_mount` 表示这是不挂载系统替换文件的脚本模块。安装时通常先写入 `modules_update`，下次启动才激活到 `modules`。已保存的 `modules.json` 中 `mount=false`、`enabled=true`、`update=true` 正是本次安装后、尚未重启的状态。

### 已知边界

- **2026-11-03 用户反馈：停用原搜狗输入法后，模拟器内中文输入、UU 远程及 MuMu 模拟器 APP 远程控制中的中文输入和输入法面板等功能不可用。** 当前脚本仍会停用搜狗，问题尚未修复，详见 [已知问题记录](07-known-input-regression.md)。
- 内存规则是全局集合。定点删除某个类名及某个证书项后，其他复用该类名或签名的输入法也不再命中这两项；本方案不是按包名实现的独立例外规则。其他包名规则保持原样。
- 框架校验只覆盖 `framework.jar`，未同时固定 `services.jar`、SettingsProvider 或应用版本；已有清单可用于进一步核对，不等于脚本已做这些校验。
- 服务脚本没有循环重试或运行期监控。系统服务异常重启会丢失内存修复，需要重新应用。
- 进程内原始数组仍在，重建集合或服务重启都可能恢复原规则。
- 它不修改 `MuMuImeResetter`，也没有保证 Windows 宿主端所有输入模式都保持原行为。
- 当前恢复脚本针对本次设备、原设置和原证书值编写，不是任意设备的通用备份恢复工具。

## 3. 恢复原设置与停用模块

主机上执行已部署的独立入口：

```shell
adb -s mumu15:5555 shell sh /data/adb/mumu-ime-repair/rollback.sh
```

入口先运行 `ksud module disable mumu_ime_allow_com_ac`，再从暂存目录或激活目录寻找 `rollback.sh`。模块内恢复脚本执行：

1. 创建 `disable` 标记。
2. 启用搜狗和按键精灵，将默认切回搜狗。
3. 恢复本次修复前的启用列表顺序与 `selected_input_method_subtype=1802354156`。
4. 重新附加当前系统进程，把原类名和证书项加入集合，输出 `MUMU_IME_RESTORED`。

这里恢复的是默认、启用列表、子类型和两条内存规则；不逐字恢复整个系统设置数据库、输入法使用历史或所有应用状态。

恢复后检查：

```shell
adb -s mumu15:5555 shell settings get secure default_input_method
adb -s mumu15:5555 shell settings get secure enabled_input_methods
adb -s mumu15:5555 shell /data/adb/ksud module list
```

默认应为搜狗，启用列表恢复两项，模块为停用。恢复脚本会把超时等退出情况统一结束为 0，**不能只凭退出码判定完全恢复**；应核对标记和回读结果。若需要证明拦截也恢复，可在受控测试中运行只读检查或尝试一次按键精灵切换。

模块附带 `uninstall.sh`，意图在卸载时调用恢复脚本；本次没有实际卸载验证。KernelSU 的停用/卸载界面行为和启动处理结果，应以设备实际状态为准。

## 4. 恢复修复

如果刚回退并希望重新启用，先通过 KernelSU 重新启用模块，再从**实际存在**的模块目录运行 `service.sh`。未重启阶段通常为 `modules_update`，激活后通常为 `modules`。

```sh
# Android shell；先检查目录，再选择正确路径执行。
/data/adb/ksud module enable mumu_ime_allow_com_ac
ls /data/adb/modules_update/mumu_ime_allow_com_ac/service.sh
ls /data/adb/modules/mumu_ime_allow_com_ac/service.sh
```

不要仅删除测试目录的 `disable` 标记，却忘了真正安装模块仍处于停用状态。

## 5. 常见结果的解释

| 现象 | 含义及下一步 |
| --- | --- |
| `is blacklisted and cannot be selected` | 规则仍在、进程重启或目标签名/类变化；先用只读脚本核对实际集合 |
| `removed=false`，随后切换成功 | 通常是重复应用，项此前已被删除；结合两类检查及实际绑定判断 |
| `MUMU_IME_ERROR` | 脚本异常；保留完整输出，核对字段、类、ABI、Frida 和系统版本 |
| 注入器退出 124 | 10 秒时限触发；看成功标记、进程健康和输入法最终状态 |
| `System framework changed; skipped.` | 系统文件指纹变化，脚本主动停止；拉取新版本重新分析，不直接改哈希放行 |
| `System server changed; skipped IME changes.` | 操作期间系统服务发生变化；保存日志并重新检查进程和启动状态 |
| 有默认值但脚本仍不能输入 | 核对实际绑定、输入焦点、当前连接以及应用内部提交方法是否变化 |
| 重启后日志仍是旧时间 | 可能未自动执行，或读的是旧暂存目录；核对 boot ID、模块激活路径及 KernelSU 状态 |

## 6. 本次资料的完整性与限制

- 原始保存文件与后续重新采集结果分目录存放；没有原始输出文件的观察明确标为会话摘录。
- 历史启发式扫描保留但不作为准确反编译结果。
- 提供官方二进制及原系统快照的字节数和 SHA-256，便于核对文件版本。
- 项目整理期间只对模拟器做只读检查和证据提取，没有再次执行修复、回退、安装、卸载或重启。
- 项目文件完成不代表重启自动修复已经实测；待测项见[测试文档](03-testing.md)。

# MuMu 按键精灵输入法修复（一键工具测试版）

已知未修复问题（2026-11-03 用户反馈）：禁用原搜狗输入法后，模拟器内无法输入中文，UU 远程及 MuMu 模拟器 APP 远程控制中的中文输入、弹出输入法等功能也无法正常使用。本模块仍包含停用搜狗的操作；安装或脚本成功不表示这些功能正常。此前中文测试只覆盖按键精灵自身的提交链路。详细记录见项目 docs/07-known-input-regression.md。

需要 KernelSU、Root、Android 15 / SDK 35、x86_64，以及事先安装包含输入法的 com.ac 应用。仅适配已排查的 MuMu 6.8.8.0 框架文件，安装会核对 SHA-256。

安装：KernelSU 管理器 → 模块 → 从本地安装此 ZIP。完成后可手动重启，或在模块动作入口应用。启动脚本只在开机时运行，不监控系统进程的异常重启。

首次安装前会备份本设备的四项输入法设置至 /data/adb/mumu-ime-repair/original，保留首次备份，恢复及卸载不主动删除。无法获得可信原配置时拒绝安装。曾用旧版专用模块或一次性修复的用户，请先恢复旧方案、移除旧模块并重启，再安装一键工具。

恢复：推荐配套 Windows 工具中的“恢复原设置.cmd”。也可通过已获 Root 的 ADB shell 运行当前模块目录内的 rollback.sh：先确认模块位于 /data/adb/modules/mumu_ime_allow_com_ac，还是尚未重启的 /data/adb/modules_update/mumu_ime_allow_com_ac，再执行 sh 加实际脚本完整路径。恢复后停用开机修复；只在管理器停用模块不会立即撤销当前内存修改。

工具使用官方 Frida 16.7.19 Android x86_64 frida-inject，仅修改 system_server 内存中的两个已确认集合，不修改系统分区或应用 APK。官方来源：
https://github.com/frida/frida/releases/download/16.7.19/frida-inject-16.7.19-android-x86_64.xz

原设备核心修复、中文提交和回退已实测；一键工具仅通过本地模拟测试，尚未在真实模拟器安装，Windows 实机及重启自动执行未验证。完整步骤见项目 docs/05-sharing.md 及配套 Windows 包内“使用说明.md”。

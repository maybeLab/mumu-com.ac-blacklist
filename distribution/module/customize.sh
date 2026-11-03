#!/system/bin/sh
EXPECTED=5a46d36ebaf9b8088dc24b3601e7365123b6b258126ef4477fa6524b566fe349
[ "$(getprop ro.product.cpu.abi)" = x86_64 ] || abort '需要 x86_64 模拟器。'
[ "$(getprop ro.build.version.sdk)" = 35 ] || abort '目前仅适配 Android 15 / SDK 35。'
FRAMEWORK=$(sha256sum /system/framework/framework.jar)
[ "${FRAMEWORK%% *}" = "$EXPECTED" ] || abort '系统框架不匹配，安装已停止。'
PACKAGE=$(pm path com.ac)
case "$PACKAGE" in package:*) ;; *) abort '请先安装包含按键精灵输入法的 com.ac 应用。' ;; esac
sh "$MODPATH/backup.sh" capture || abort '备份原输入法配置失败，安装已停止。'
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/frida-inject" 0 0 0700
for script in "$MODPATH"/*.sh; do set_perm "$script" 0 0 0700; done
ui_print '已保存本设备原配置；未修改系统分区。'
ui_print '一键工具测试版：开机自动执行及 Windows 实机流程仍需验证。'

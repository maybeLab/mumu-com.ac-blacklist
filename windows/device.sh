#!/system/bin/sh
ID=mumu_ime_allow_com_ac
BASE=/data/adb/mumu-ime-repair
ACTIVE=/data/adb/modules/$ID
STAGED=/data/adb/modules_update/$ID
EXPECTED=5a46d36ebaf9b8088dc24b3601e7365123b6b258126ef4477fa6524b566fe349
fail() { echo "$1" >&2; exit 1; }
[ "$(id -u)" = 0 ] || fail '需要 Root 权限，请先在模拟器中授权。'
[ -x /data/adb/ksud ] || fail '未找到 KernelSU；普通 Root 不代表支持本模块。'
find_module() {
  for dir in "$STAGED" "$ACTIVE"; do
    if [ -f "$dir/rollback.sh" ] && [ -f "$dir/backup.sh" ]; then MODDIR=$dir; return 0; fi
  done
  return 1
}
case "$1" in
  install)
    [ "$(getprop ro.product.cpu.abi)" = x86_64 ] || fail '模拟器 ABI 不兼容。'
    [ "$(getprop ro.build.version.sdk)" = 35 ] || fail '需要 Android 15 / SDK 35。'
    FRAMEWORK=$(sha256sum /system/framework/framework.jar) || exit 1
    [ "${FRAMEWORK%% *}" = "$EXPECTED" ] || fail '系统框架不兼容，已停止。'
    if [ ! -f "$BASE/original/complete" ]; then
      for dir in "$ACTIVE" "$STAGED"; do
        [ ! -f "$dir/module.prop" ] || fail '检测到旧模块且没有原配置备份，请先用旧方案恢复后再安装一键工具。'
      done
    fi
    /data/adb/ksud module install /data/local/tmp/mumu-ime-share/module.zip || exit 1
    find_module || fail '安装后找不到一键工具模块，请检查 KernelSU 状态。'
    /data/adb/ksud module enable "$ID" || exit 1
    rm -f "$MODDIR/disable" || exit 1
    sh "$MODDIR/service.sh" || fail '模块已安装，但本次应用失败；请运行状态检查，勿反复安装。'
    [ "$(settings get secure default_input_method)" = com.ac/com.ime.input.InputKb ] || fail '默认输入法未切换成功。'
    ENABLED=$(settings get secure enabled_input_methods)
    case ":$ENABLED:" in *:com.ac/com.ime.input.InputKb:*|*:com.ac/com.ime.input.InputKb\;*) ;; *) fail '启用列表中没有目标输入法，请检查状态。' ;; esac
    case ":$ENABLED:" in *:com.sohu.inputmethod.sogou.chuizi/com.sohu.inputmethod.sogou.SogouIME:*|*:com.sohu.inputmethod.sogou.chuizi/com.sohu.inputmethod.sogou.SogouIME\;*) fail '搜狗输入法仍处于启用状态，请检查状态。' ;; esac
    echo MUMU_SHARE_INSTALLED
    ;;
  restore)
    find_module || fail '找不到一键工具模块；旧版模块请使用其原恢复入口。'
    [ -f "$BASE/original/complete" ] || fail '缺少原配置备份，停止恢复。'
    /data/adb/ksud module disable "$ID" || exit 1
    sh "$MODDIR/rollback.sh" || fail '恢复没有完成，请保留日志并检查。'
    echo MUMU_SHARE_RESTORED
    ;;
  *) fail '未知操作。' ;;
esac

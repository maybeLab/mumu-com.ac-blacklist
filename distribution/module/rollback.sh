#!/system/bin/sh
MODDIR=${0%/*}
touch "$MODDIR/disable" || exit 1
sh "$MODDIR/backup.sh" restore || exit 1
FRAMEWORK=$(sha256sum /system/framework/framework.jar) || exit 1
if [ "${FRAMEWORK%% *}" != 5a46d36ebaf9b8088dc24b3601e7365123b6b258126ef4477fa6524b566fe349 ]; then
  echo '系统框架已变化；已恢复原配置并停用模块，跳过运行时黑名单恢复。'
  exit 0
fi
SERVER_PID=$(pidof system_server)
case "$SERVER_PID" in ''|*[!0-9]*) exit 1 ;; esac
timeout 10 "$MODDIR/frida-inject" -p "$SERVER_PID" -s "$MODDIR/restore.js" > "$MODDIR/last-restore.log" 2>&1
cat "$MODDIR/last-restore.log"
grep -q '^MUMU_IME_RESTORED' "$MODDIR/last-restore.log" || exit 1
if grep -q 'MUMU_IME_ERROR' "$MODDIR/last-restore.log"; then exit 1; fi

#!/system/bin/sh
MODDIR=${0%/*}
LOGFILE="$MODDIR/last-run.log"
EXPECTED_FRAMEWORK=5a46d36ebaf9b8088dc24b3601e7365123b6b258126ef4477fa6524b566fe349
TARGET=com.ac/com.ime.input.InputKb
BUILTIN=com.sohu.inputmethod.sogou.chuizi/com.sohu.inputmethod.sogou.SogouIME

[ -f "$MODDIR/disable" ] && exit 0
[ -f "$MODDIR/remove" ] && exit 0
attempt=0
while [ "$(getprop sys.boot_completed)" != 1 ] && [ "$attempt" -lt 120 ]; do
  sleep 1
  attempt=$((attempt + 1))
done
date > "$LOGFILE"
if [ "$(getprop sys.boot_completed)" != 1 ]; then
  echo 'Boot not complete; skipped.' >> "$LOGFILE"
  exit 1
fi
ACTUAL_FRAMEWORK=$(sha256sum /system/framework/framework.jar)
ACTUAL_FRAMEWORK=${ACTUAL_FRAMEWORK%% *}
if [ "$ACTUAL_FRAMEWORK" != "$EXPECTED_FRAMEWORK" ]; then
  echo 'System framework changed; skipped. Recheck compatibility.' >> "$LOGFILE"
  exit 1
fi
pm path com.ac >/dev/null 2>&1 || exit 1
SERVER_PID=$(pidof system_server)
case "$SERVER_PID" in ''|*[!0-9]*) exit 1 ;; esac
timeout 10 "$MODDIR/frida-inject" -p "$SERVER_PID" -s "$MODDIR/fix.js" >> "$LOGFILE" 2>&1
if ! grep -q 'MUMU_IME_FIXED .*"blocked":false' "$LOGFILE"; then
  echo 'Runtime patch did not report success; skipped IME changes.' >> "$LOGFILE"
  exit 1
fi
if [ "$(pidof system_server)" != "$SERVER_PID" ]; then
  echo 'System server changed; skipped IME changes.' >> "$LOGFILE"
  exit 1
fi
ime enable "$TARGET" >> "$LOGFILE" 2>&1
ime set "$TARGET" >> "$LOGFILE" 2>&1
if [ "$(settings get secure default_input_method)" != "$TARGET" ]; then
  echo 'Default input method did not change.' >> "$LOGFILE"
  exit 1
fi
ime disable "$BUILTIN" >> "$LOGFILE" 2>&1
echo 'SUCCESS: automation IME selected.' >> "$LOGFILE"

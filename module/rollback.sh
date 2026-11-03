#!/system/bin/sh
MODDIR=${0%/*}
touch "$MODDIR/disable"
BUILTIN=com.sohu.inputmethod.sogou.chuizi/com.sohu.inputmethod.sogou.SogouIME
ime enable "$BUILTIN"
ime enable com.ac/com.ime.input.InputKb
ime set "$BUILTIN"
settings put secure enabled_input_methods 'com.ac/com.ime.input.InputKb:com.sohu.inputmethod.sogou.chuizi/com.sohu.inputmethod.sogou.SogouIME'
settings put secure selected_input_method_subtype 1802354156
SERVER_PID=$(pidof system_server)
case "$SERVER_PID" in ''|*[!0-9]*) exit 0 ;; esac
timeout 10 "$MODDIR/frida-inject" -p "$SERVER_PID" -s "$MODDIR/restore.js"
exit 0

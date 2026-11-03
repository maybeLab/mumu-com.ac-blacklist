#!/system/bin/sh
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/frida-inject" 0 0 0700
for script in service.sh rollback.sh uninstall.sh action.sh; do
  set_perm "$MODPATH/$script" 0 0 0700
done
ui_print 'Script-only module: system files remain unchanged.'
ui_print 'Rollback: sh /data/adb/modules/mumu_ime_allow_com_ac/rollback.sh'

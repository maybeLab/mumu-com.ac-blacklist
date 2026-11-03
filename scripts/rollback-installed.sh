#!/system/bin/sh
/data/adb/ksud module disable mumu_ime_allow_com_ac || exit 1
for MODDIR in /data/adb/modules_update/mumu_ime_allow_com_ac /data/adb/modules/mumu_ime_allow_com_ac; do
  if [ -f "$MODDIR/rollback.sh" ]; then
    sh "$MODDIR/rollback.sh"
    exit $?
  fi
done
echo 'Module rollback script not found.' >&2
exit 1

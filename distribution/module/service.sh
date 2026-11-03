#!/system/bin/sh
MODDIR=${0%/*}
[ -f "$MODDIR/disable" ] && exit 0
[ -f "$MODDIR/remove" ] && exit 0
sh "$MODDIR/backup.sh" capture || exit 1
exec sh "$MODDIR/service-core.sh"

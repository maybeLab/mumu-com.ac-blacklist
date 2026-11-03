#!/system/bin/sh
MODDIR=${0%/*}
sh "$MODDIR/service.sh"
result=$?
[ ! -f "$MODDIR/last-run.log" ] || cat "$MODDIR/last-run.log"
exit "$result"

#!/system/bin/sh
MODDIR=${0%/*}
sh "$MODDIR/service.sh"
cat "$MODDIR/last-run.log"

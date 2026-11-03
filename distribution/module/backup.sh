#!/system/bin/sh
BASE=/data/adb/mumu-ime-repair
ORIGINAL=$BASE/original
TARGET=com.ac/com.ime.input.InputKb
KEYS='enabled_input_methods default_input_method selected_input_method_subtype input_methods_subtype_history'
umask 077
case "$1" in
  capture)
    if [ -f "$ORIGINAL/complete" ]; then
      for key in $KEYS; do [ -f "$ORIGINAL/$key" ] || exit 1; done
      exit 0
    fi
    if [ "$(settings get secure default_input_method)" = "$TARGET" ]; then
      echo '当前已使用按键精灵且没有原配置备份；请先恢复已有修复，再安装一键工具。' >&2
      exit 1
    fi
    [ ! -e "$ORIGINAL" ] || { echo '原配置备份不完整；请保留该目录并检查。' >&2; exit 1; }
    mkdir -p "$BASE" || exit 1
    TMP=$(mktemp -d "$BASE/original.new.XXXXXX") || exit 1
    for key in $KEYS; do
      settings get secure "$key" > "$TMP/$key" || { rm -rf "$TMP"; exit 1; }
    done
    [ -s "$TMP/default_input_method" ] || { rm -rf "$TMP"; exit 1; }
    [ "$(cat "$TMP/default_input_method")" != null ] || { rm -rf "$TMP"; exit 1; }
    date > "$TMP/captured-at.txt"
    echo 1 > "$TMP/complete"
    mv "$TMP" "$ORIGINAL" || exit 1
    echo '已备份本设备原来的输入法设置。'
    ;;
  restore)
    [ -f "$ORIGINAL/complete" ] || { echo '找不到完整的本设备原配置备份。' >&2; exit 1; }
    for key in $KEYS; do [ -f "$ORIGINAL/$key" ] || exit 1; done
    for key in $KEYS; do
      value=$(cat "$ORIGINAL/$key")
      if [ "$value" = null ]; then
        settings delete secure "$key" >/dev/null || exit 1
      else
        settings put secure "$key" "$value" || exit 1
      fi
    done
    for key in enabled_input_methods default_input_method; do
      [ "$(settings get secure "$key")" = "$(cat "$ORIGINAL/$key")" ] || exit 1
    done
    echo '已恢复本设备原来的默认输入法和启用列表。'
    ;;
  *) echo 'Usage: backup.sh capture|restore' >&2; exit 2 ;;
esac

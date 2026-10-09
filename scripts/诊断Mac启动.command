#!/bin/bash
set -euo pipefail
if [[ "$(uname -s)" != Darwin ]]; then printf '请在 Mac 上运行此诊断。\n'; exit 1; fi
base="$(cd "$(dirname "$0")" && pwd)"
output="$HOME/Library/Logs/Hongguo/Startup-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$output"
report="$output/startup-diagnostics.log"
printf 'format=hongguo-mac-startup-v1\nmacos_version=%s\nhost_arch=%s\n' "$(/usr/bin/sw_vers -productVersion)" "$(uname -m)" > "$report"
check() { if "$@" >/dev/null 2>&1; then printf passed; else printf 'failed:%s' "$?"; fi; }
qtn() { if /usr/bin/xattr -p com.apple.quarantine "$1" >/dev/null 2>&1; then printf yes; else printf no; fi; }
for kind in source installed; do
  if [[ "$kind" == source ]]; then item="$base/Hongguo.app"; else item="$HOME/Applications/Hongguo.app"; fi
  if [[ ! -d "$item/Contents" ]]; then printf '%s_present=no\n' "$kind" >> "$report"; continue; fi
  printf '%s_present=yes\n%s_quarantine=%s\n%s_bundle_signature=%s\n' "$kind" "$kind" "$(qtn "$item")" "$kind" "$(check /usr/bin/codesign --verify --deep --strict "$item")" >> "$report"
  decoder="$item/Contents/Resources/apk-native/media/ffmpeg"
  printf '%s_decoder_quarantine=%s\n%s_decoder_signature=%s\n' "$kind" "$(qtn "$decoder")" "$kind" "$(check /usr/bin/codesign --verify --strict "$decoder")" >> "$report"
  if [[ "$kind" == installed ]] && /usr/bin/codesign --verify --strict "$decoder" >/dev/null 2>&1 && ! /usr/bin/xattr -p com.apple.quarantine "$decoder" >/dev/null 2>&1; then
    printf 'installed_decoder_launch=%s\n' "$(check "$decoder" -hide_banner -version)" >> "$report"
  fi
done
for name in ffmpeg Hongguo; do
  crash=""; newest=0
  for candidate in "$HOME/Library/Logs/DiagnosticReports/$name"*.ips; do
    [[ -f "$candidate" ]] || continue
    modified="$(/usr/bin/stat -f %m "$candidate")"
    if [[ "$modified" -gt "$newest" ]]; then crash="$candidate"; newest="$modified"; fi
  done
  if [[ -n "$crash" ]] && [[ $(( $(date +%s) - newest )) -lt 86400 ]]; then
    category="$(/usr/bin/osascript -l JavaScript -e 'function run(argv){try{ObjC.import("Foundation");var text=ObjC.unwrap($.NSString.stringWithContentsOfFileEncodingError(argv[0],$.NSUTF8StringEncoding,null));var data=JSON.parse(text.substring(text.indexOf("\n")+1)),ns=(data.termination||{}).namespace;return ["CODESIGNING","DYLD","SIGNAL","JETSAM","WATCHDOG"].includes(ns)?ns:"OTHER";}catch(e){return "UNPARSED";}}' "$crash" 2>/dev/null || printf UNAVAILABLE)"
    printf '%s_recent_crash_namespace=%s\n' "$name" "$category" >> "$report"
  else printf '%s_recent_crash_namespace=NONE\n' "$name" >> "$report"; fi
done
printf '启动诊断已生成：%s\n诊断未修改签名、隔离标记、系统安全设置或账号。\n' "$report"

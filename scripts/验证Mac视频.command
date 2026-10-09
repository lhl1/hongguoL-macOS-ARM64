#!/bin/bash
set -euo pipefail
app="$HOME/Applications/Hongguo.app"
if [[ "$(uname -s)" != "Darwin" || ! -f "$app/Contents/Info.plist" ]]; then
  printf '请在 Mac 上先运行准备Mac版.command，再运行视频自检。\n'
  exit 1
fi
exe="$(/usr/bin/plutil -extract CFBundleExecutable raw "$app/Contents/Info.plist")"
[[ "$exe" == "Hongguo" ]]
output="$HOME/Library/Logs/Hongguo/Media-check-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$output"
printf '正在后台静音核对 FFmpeg 编码、本机 HTTP 与播放器首帧，不读取账号或发送短信。\n'
if HONGGUO_MEDIA_QA_OUTPUT="$output" "$app/Contents/MacOS/$exe" --media-self-test > "$output/console.txt" 2>&1; then
  printf '本机视频自检通过。结果：%s/media-self-test.json\n' "$output"
else
  printf '本机视频自检未通过。请查看结果：%s/media-self-test.json\n' "$output"
  exit 1
fi

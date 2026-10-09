#!/bin/bash
set -euo pipefail
if [[ "$(uname -s)" != "Darwin" ]]; then printf '请在 Mac 上运行此验证。\n'; exit 1; fi
app="$HOME/Applications/Hongguo.app"
if [[ ! -d "$app/Contents" ]]; then printf '请先运行“准备Mac版.command”安装。\n'; exit 1; fi
/usr/bin/codesign --verify --deep --strict "$app"
executable="$(/usr/bin/plutil -extract CFBundleExecutable raw "$app/Contents/Info.plist")"
output="$HOME/Library/Logs/Hongguo/QA-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$output"
printf '开始隐藏静音验收；使用新建游客资料，不发送短信，不读取已登录账号。\n'
HONGGUO_SMOKE_OUTPUT="$output" "$app/Contents/MacOS/$executable" --smoke-test > "$output/run.log" 2> "$output/stderr.log"
printf '\n验证通过。证据目录：%s\n真实登录与云同步、可见原生窗口操作未包含在此流程。\n' "$output"

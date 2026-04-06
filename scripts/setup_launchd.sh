#!/usr/bin/env bash
# LLM Wiki — macOS launchd 자동 시작 등록
# 로그인 후 백그라운드에서 wiki watch 자동 실행
#
# 사용법:
#   bash scripts/setup_launchd.sh          # 등록
#   bash scripts/setup_launchd.sh --remove  # 해제

set -e

LABEL="com.llmwiki.watch"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON="$REPO_ROOT/.venv/bin/python"
LOG_OUT="/tmp/llm-wiki-watch.log"
LOG_ERR="/tmp/llm-wiki-watch-error.log"

# ── 해제 ──────────────────────────────────────────────────────────────────────
if [[ "$1" == "--remove" ]]; then
    if launchctl list | grep -q "$LABEL"; then
        launchctl unload "$PLIST" 2>/dev/null || true
        echo "✓ launchd 서비스 중지: $LABEL"
    fi
    rm -f "$PLIST"
    echo "✓ plist 삭제: $PLIST"
    echo "wiki watch 자동 시작이 해제되었습니다."
    exit 0
fi

# ── 사전 확인 ─────────────────────────────────────────────────────────────────
if [ ! -f "$PYTHON" ]; then
    echo "오류: venv가 없습니다. 먼저 설치하세요:"
    echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# ── plist 생성 ────────────────────────────────────────────────────────────────
cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>${REPO_ROOT}/scripts/wiki.py</string>
        <string>watch</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${REPO_ROOT}</string>

    <!-- 로그인 후 자동 시작 -->
    <key>RunAtLoad</key>
    <true/>

    <!-- 비정상 종료 시 재시작 -->
    <key>KeepAlive</key>
    <true/>

    <!-- 재시작 쿨다운 (초) -->
    <key>ThrottleInterval</key>
    <integer>10</integer>

    <key>StandardOutPath</key>
    <string>${LOG_OUT}</string>

    <key>StandardErrorPath</key>
    <string>${LOG_ERR}</string>
</dict>
</plist>
EOF

# ── 기존 서비스 언로드 후 재등록 ──────────────────────────────────────────────
if launchctl list | grep -q "$LABEL"; then
    launchctl unload "$PLIST" 2>/dev/null || true
fi
launchctl load "$PLIST"

echo "✓ launchd 등록 완료: $LABEL"
echo ""
echo "  상태 확인 : launchctl list | grep llmwiki"
echo "  로그 확인 : tail -f $LOG_OUT"
echo "  에러 확인 : tail -f $LOG_ERR"
echo "  해제      : bash scripts/setup_launchd.sh --remove"
echo ""
echo "이제 로그인할 때마다 wiki watch가 백그라운드에서 자동 시작됩니다."
echo "Web Clipper로 raw/ 에 파일을 저장하면 즉시 ingest됩니다."

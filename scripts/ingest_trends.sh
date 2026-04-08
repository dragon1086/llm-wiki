#!/usr/bin/env bash
# ingest_trends.sh — last30days 출력물을 vault raw/trending/으로 복사 후 ingest
#
# 사용법:
#   bash scripts/ingest_trends.sh             # 최신 파일 1개 복사 + ingest
#   bash scripts/ingest_trends.sh --all       # 오늘 생성된 파일 전체 복사 + ingest
#   bash scripts/ingest_trends.sh --copy-only # 복사만 (ingest 건너뜀)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_RAW="$(python3 -c "
import yaml, os
cfg = yaml.safe_load(open('$REPO_ROOT/config.yaml'))
print(os.path.join(cfg['vault_path'], cfg.get('raw_dir', 'raw'), 'trending'))
")"
SRC_DIR="$HOME/Documents/Last30Days"

MODE="latest"
COPY_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --all)       MODE="all" ;;
    --copy-only) COPY_ONLY=true ;;
  esac
done

# --- 소스 확인 ---
if [[ ! -d "$SRC_DIR" ]]; then
  echo "❌  $SRC_DIR 없음. /last30days 스킬을 먼저 실행하세요."
  exit 1
fi

mkdir -p "$VAULT_RAW"

# --- 복사 ---
if [[ "$MODE" == "all" ]]; then
  FILES=$(find "$SRC_DIR" -name "*.md" -newer "$SRC_DIR" -maxdepth 2 2>/dev/null || \
          find "$SRC_DIR" -name "*.md" -maxdepth 2 | sort -t_ -k1 | tail -10)
else
  FILES=$(ls -t "$SRC_DIR"/*.md 2>/dev/null | head -1 || true)
fi

if [[ -z "$FILES" ]]; then
  echo "❌  $SRC_DIR 에 .md 파일이 없습니다."
  exit 1
fi

COPIED=()
for f in $FILES; do
  fname="$(basename "$f")"
  dest="$VAULT_RAW/$fname"
  cp "$f" "$dest"
  COPIED+=("$dest")
  echo "✅  복사: $fname → raw/trending/"
done

# --- Ingest ---
if [[ "$COPY_ONLY" == "true" ]]; then
  echo "ℹ️   --copy-only: ingest 건너뜀"
  exit 0
fi

cd "$REPO_ROOT"
if [[ ! -d ".venv" ]]; then
  echo "⚠️   .venv 없음 — ingest 건너뜀. 'python3 -m venv .venv && pip install -r requirements.txt' 후 재실행"
  exit 0
fi

source .venv/bin/activate

for dest in "${COPIED[@]}"; do
  rel="raw/trending/$(basename "$dest")"
  echo "▶  ingest: $rel"
  python3 scripts/wiki.py ingest "$rel"
done

echo ""
echo "🎉  완료. wiki/summaries/, concepts/, entities/ 업데이트됨."

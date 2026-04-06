#!/usr/bin/env bash
# LLM Wiki — vault 디렉토리 초기화 스크립트
# 사용법: bash scripts/setup_vault.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# config.yaml에서 vault_path 읽기
VAULT_PATH=$(python3 -c "
import yaml, pathlib
cfg = yaml.safe_load(open('$REPO_ROOT/config.yaml'))
print(cfg['vault_path'])
")

echo "vault 경로: $VAULT_PATH"

# 디렉토리 생성
mkdir -p "$VAULT_PATH/raw"
mkdir -p "$VAULT_PATH/wiki/concepts"
mkdir -p "$VAULT_PATH/wiki/entities"
mkdir -p "$VAULT_PATH/wiki/summaries"
mkdir -p "$VAULT_PATH/wiki/findings"
mkdir -p "$VAULT_PATH/output"

# index.md 초기화 (없을 때만)
INDEX="$VAULT_PATH/wiki/index.md"
if [ ! -f "$INDEX" ]; then
cat > "$INDEX" << 'EOF'
---
type: index
updated: 2025-01-01
total_pages: 0
total_summaries: 0
total_concepts: 0
total_entities: 0
total_findings: 0
---

# LLM Wiki — Index

## Summaries

## Concepts

## Entities

## Findings

<!-- FORMAT: - [[slug]] — 질문 요약 (날짜) -->
EOF
echo "✓ wiki/index.md 생성"
fi

# log.md 초기화 (없을 때만)
LOG="$VAULT_PATH/wiki/log.md"
if [ ! -f "$LOG" ]; then
cat > "$LOG" << 'EOF'
# LLM Wiki — 운영 로그

EOF
echo "✓ wiki/log.md 생성"
fi

# lint_ignore.txt 초기화 (없을 때만)
LINT_IGNORE="$VAULT_PATH/wiki/lint_ignore.txt"
if [ ! -f "$LINT_IGNORE" ]; then
cat > "$LINT_IGNORE" << 'EOF'
# meta-slug placeholders used as examples in system documentation
wikilink
slug
파일명
page_slug
EOF
echo "✓ wiki/lint_ignore.txt 생성"
fi

echo ""
echo "✓ vault 초기화 완료: $VAULT_PATH"
echo ""
echo "다음 단계:"
echo "  1. Obsidian에서 '$VAULT_PATH' 폴더를 vault로 열기"
echo "  2. python scripts/wiki.py ingest --all  (raw/ 파일이 있다면)"
echo "  3. python scripts/wiki.py status"

---
description: wiki 정합성 검사 (dead links, orphans, 모순, stale claims)
argument-hint: "[--fix] [--deep]"
allowed-tools:
  - Bash
  - Read
  - mcp__obsidian__*
---

# /lint

옵션: `$ARGUMENTS`

## 실행 순서

1. **lint 실행**:
   ```bash
   cd /Users/aerok/Desktop/rocky/llm-wiki
   source .venv/bin/activate && python3 scripts/wiki.py lint $ARGUMENTS
   ```

2. **결과 파일 확인**: `wiki/findings/lint-report-<날짜>.md` 읽기

3. **이슈 요약**: 탐지된 이슈 유형별로 표로 정리

## 플래그

- `--fix`: orphan 자동 수정, index.md 갱신
- `--deep`: LLM으로 모순 탐지 (느림, Claude 토큰 추가 소모)

## 일반 lint (--fix 없이)

dead link 수정 제안은 자동 적용하지 않고 목록만 출력합니다 (`config.yaml`: `auto_fix_dead_links: false`).

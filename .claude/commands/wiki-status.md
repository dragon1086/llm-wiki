---
description: wiki 현황 요약 — 페이지 수, 최근 로그, raw 미처리 파일 확인
allowed-tools:
  - Bash
  - Read
  - mcp__obsidian__*
---

# /wiki-status

## 실행 순서

다음 명령을 병렬로 실행합니다:

```bash
cd /Users/aerok/Desktop/rocky/llm-wiki
source .venv/bin/activate && python3 scripts/wiki.py status
```

```bash
source .venv/bin/activate && python3 scripts/wiki.py list-raw
```

## 출력 포맷

```
=== LLM Wiki 현황 ===
  summaries : N개
  concepts  : N개
  entities  : N개
  findings  : N개
  합계      : N개

=== raw/ 미처리 파일 ===
  ○ 미처리파일.md

=== 최근 로그 (5개) ===
  [날짜] [TYPE] message
```

Obsidian MCP로 vault 구조도 확인하여 index.md와 실제 파일 수 일치 여부를 검증합니다.

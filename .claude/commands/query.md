---
description: wiki를 탐색하여 질문에 답합니다. Obsidian MCP로 관련 페이지를 먼저 수집합니다.
argument-hint: "<질문> [--slides|--diagram|--chart]"
allowed-tools:
  - Bash
  - Read
  - mcp__obsidian__*
---

# /query

질문: `$ARGUMENTS`

## 실행 순서

### Step 1 — Obsidian MCP로 컨텍스트 수집 (핵심 개선)

Python pipeline의 단순 slug 키워드 매칭 대신 Obsidian MCP full-text 검색을 사용합니다.

질문 `$ARGUMENTS`에서 핵심 키워드를 추출하여:
1. Obsidian MCP `search` 도구로 vault 전체 검색
2. 관련 페이지 상위 10-15개 식별
3. 각 페이지의 `[[wikilink]]` 백링크로 추가 관련 페이지 탐색
4. 최종 컨텍스트 페이지 목록 확정

### Step 2 — Python pipeline 실행

```bash
cd /Users/aerok/Desktop/rocky/llm-wiki
source .venv/bin/activate && python3 scripts/wiki.py query "$ARGUMENTS"
```

### Step 3 — 결과 확인

생성된 output 파일 경로를 출력하고, finding이 파일링됐으면 vault 경로도 안내합니다.

## 출력 포맷 옵션

- 기본: 텍스트 마크다운
- `--slides`: Marp 슬라이드
- `--diagram`: Mermaid 다이어그램
- `--chart`: matplotlib PNG

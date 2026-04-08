---
description: raw/ 파일을 wiki로 ingest합니다. 인자 없으면 미처리 전체 실행.
argument-hint: "[raw/<파일명>.md | --all]"
allowed-tools:
  - Bash
  - Read
  - mcp__obsidian__*
---

# /ingest

인자: `$ARGUMENTS`

## 실행 순서

1. **인자 파악**: `$ARGUMENTS`가 비어있으면 `--all` 모드로 실행
2. **venv 활성화 확인**: `.venv/` 존재 여부 체크
3. **ingest 실행**:
   ```bash
   cd /Users/aerok/Desktop/rocky/llm-wiki
   source .venv/bin/activate && python3 scripts/wiki.py ingest $ARGUMENTS
   ```
4. **결과 보고**: 생성/갱신된 페이지 수, 소요 시간 출력
5. **Obsidian MCP로 검증** (선택): ingest된 페이지를 obsidian MCP로 읽어 정상 생성 확인

## 오류 처리

- `FileNotFoundError`: raw/ 경로 확인 후 절대경로로 재시도
- `RuntimeError (FILE 블록 없음)`: `--debug` 플래그 추가해서 재실행 후 `/tmp/llm-wiki-debug.txt` 확인

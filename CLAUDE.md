# LLM Wiki — Claude Code Guide

> **이 파일은 Claude Code 세션용 가이드입니다.**
> wiki 스키마·운영 규칙은 `AGENTS.md`를 참조하세요.

---

## 프로젝트 구조

```
llm-wiki/               ← 이 레포 (시스템 코드)
  scripts/
    wiki.py             ← CLI 진입점
    ingest.py           ← raw → wiki 컴파일
    query.py            ← wiki 탐색 → 답변 합성
    lint.py             ← wiki 정합성 검사
    utils.py            ← 공통 유틸 (call_claude, vault I/O)
  config.yaml           ← vault_path 등 설정
  AGENTS.md             ← wiki LLM 운영 규칙 (스키마, 프로토콜)

obsidian-vault/llm-wiki/   ← vault (config.yaml의 vault_path)
  raw/                  ← 소스 투하 지점
  wiki/                 ← LLM이 컴파일한 wiki 페이지
    index.md, log.md
    concepts/, entities/, summaries/, findings/
  output/               ← 쿼리 결과물
```

## Vault 경로

`config.yaml`의 `vault_path`: `/Users/aerok/Desktop/rocky/obsidian-vault/llm-wiki`

## Obsidian MCP 활용

`obsidian` MCP 서버(`~/.claude/settings.json`)로 vault를 직접 읽고 검색할 수 있습니다.

- **vault 검색**: 키워드로 관련 페이지 전문 검색 (slug 매칭보다 정확)
- **페이지 읽기**: wiki 페이지 내용 직접 읽기
- **백링크 탐색**: `[[wikilink]]` 그래프 순회

코드 수정 없이 query 컨텍스트를 보강할 때는 MCP 도구를 우선 활용하세요.

## 파이프라인 실행

```bash
# venv 활성화 필수
source .venv/bin/activate

# 소스 ingest
python3 scripts/wiki.py ingest raw/<file>.md
python3 scripts/wiki.py ingest --all

# 질의
python3 scripts/wiki.py query "질문" [--slides|--diagram|--chart]

# 정합성 검사
python3 scripts/wiki.py lint [--fix] [--deep]

# 현황
python3 scripts/wiki.py status
python3 scripts/wiki.py list-raw
```

## 코드 수정 가이드라인

- `call_claude()` in `utils.py` — claude CLI subprocess 래퍼, 모델 변경 시 여기 수정
- `build_ingest_prompt()` — ingest 품질 개선은 이 함수의 프롬프트 수정
- `collect_wiki_context()` in `query.py` — 현재 slug 키워드 매칭; obsidian MCP로 교체 가능
- `config.yaml` — vault_path, lint 임계값 등 운영 파라미터

## Slash Commands

| 커맨드 | 기능 |
|--------|------|
| `/ingest` | raw 파일 ingest 실행 |
| `/query` | vault 검색 + 질의 응답 |
| `/lint` | wiki 정합성 검사 |
| `/wiki-status` | wiki 현황 요약 |

## 운영 원칙

- 코드 변경 전 `AGENTS.md` 스키마와의 호환성 확인
- `vault_path` 하드코딩 금지 — `config.yaml`에서 읽을 것
- 새 wiki 페이지 타입 추가 시 `AGENTS.md`와 `config.yaml` 동시 수정
- 컨텍스트 50% 도달 시 `/compact` 실행

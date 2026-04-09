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

`config.yaml`의 `vault_path` 값을 사용합니다 (`~` 자동 확장 지원).
초기 설정: `python3 scripts/setup.py` 실행 후 `config.yaml` 생성됩니다.

## Obsidian MCP 활용

`obsidian` MCP 서버(`~/.claude/settings.json`)로 vault를 직접 읽고 검색할 수 있습니다.

- **vault 검색**: 키워드로 관련 페이지 전문 검색 (slug 매칭보다 정확)
- **페이지 읽기**: wiki 페이지 내용 직접 읽기
- **백링크 탐색**: `[[wikilink]]` 그래프 순회

코드 수정 없이 query 컨텍스트를 보강할 때는 MCP 도구를 우선 활용하세요.

## 파이프라인 실행

```bash
./wiki ingest              # raw/ 미처리 전체
./wiki ingest raw/<file>   # 단일 파일
./wiki query "질문" [--slides|--diagram|--chart|--archive]
./wiki lint [--fix] [--deep]
./wiki status
./wiki list-raw
```

## 코드 수정 가이드라인

- `call_claude()` in `utils.py` — claude CLI subprocess 래퍼, 모델 변경 시 여기 수정
- `build_ingest_prompt()` — ingest 품질 개선은 이 함수의 프롬프트 수정
- `collect_wiki_context()` in `query.py` — 현재 slug 키워드 매칭; obsidian MCP로 교체 가능
- `config.yaml` — vault_path, lint 임계값 등 운영 파라미터

## 트렌드 자동 수집 (last30days)

`/last30days` 스킬로 플랫폼 트렌드를 수집하고 wiki로 자동 인제스트합니다.

### 워크플로우

```
/last30days [주제]          ← Claude Code에서 실행
       ↓
~/Documents/Last30Days/*.md  ← 스킬이 자동 저장
       ↓
bash scripts/ingest_trends.sh  ← vault raw/trending/ 복사 + ingest
       ↓
wiki/summaries/, concepts/, entities/ 갱신
```

### 사용법

```bash
# 1. Claude Code에서 트렌드 수집
/last30days LLM 최신 트렌드
/last30days Claude Code 프롬프팅 기법 --deep
/last30days reasoning model 비교 --days=7

# 2. vault로 복사 + ingest (터미널에서)
bash scripts/ingest_trends.sh           # 최신 파일 1개
bash scripts/ingest_trends.sh --all     # 오늘 생성 파일 전체
bash scripts/ingest_trends.sh --copy-only  # 복사만 (ingest 나중에)
```

### 출력 위치

- last30days 원본: `~/Documents/Last30Days/`
- vault 투하 지점: `raw/trending/`

---

## Slash Commands

| 커맨드 | 기능 |
|--------|------|
| `/ingest` | raw 파일 ingest 실행 |
| `/query` | vault 검색 + 질의 응답 |
| `/lint` | wiki 정합성 검사 |
| `/wiki-status` | wiki 현황 요약 |
| `/last30days [주제]` | 트렌드 수집 → `~/Documents/Last30Days/` 저장 |

## 운영 원칙

- 코드 변경 전 `AGENTS.md` 스키마와의 호환성 확인
- `vault_path` 하드코딩 금지 — `config.yaml`에서 읽을 것
- 새 wiki 페이지 타입 추가 시 `AGENTS.md`와 `config.yaml` 동시 수정
- 컨텍스트 50% 도달 시 `/compact` 실행

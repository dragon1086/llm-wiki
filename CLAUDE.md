# CLAUDE.md

Claude Code가 이 리포에서 작업할 때 참고하는 운영 가이드.
사람을 위한 README는 [README.md](./README.md), LLM이 wiki를 유지·운영할 때 따르는 규칙은 [AGENTS.md](./AGENTS.md)를 참조.

---

## 시스템 한눈에 보기

3개 축으로 구성:

| 축 | 위치 | 역할 |
|---|---|---|
| **코드** | `llm-wiki/` (이 repo) | CLI · 파이프라인 · 프롬프트 |
| **데이터** | `obsidian-vault/llm-wiki/` (config.yaml의 `vault_path`) | raw/ · wiki/ · output/ |
| **LLM** | `claude` CLI (subprocess) | ingest / query / lint의 모든 생성 단계 |

데이터 흐름:

```
raw/*.md ──ingest──▶ wiki/{summaries,entities,concepts}/ + index.md + log.md
                                          │
                                          ▼
              query "질문" ──▶ output/*.{md,marp.md,py,png} + wiki/findings/
                                          │
                                          ▼
                                  lint (정합성 검사)
```

---

## 코드 맵

```
scripts/
├── wiki.py          Click 진입점 (ingest | query | watch | lint | status | list-raw)
├── ingest.py        raw → wiki 컴파일 (프롬프트 빌드 · 파싱 · 파일 쓰기)
├── query.py         wiki 탐색 → Claude 합성 → output/ + findings/
├── lint.py          dead_links · orphans · index_drift · (--deep) contradictions
├── utils.py         config · slugify · call_claude · log/index 갱신
├── setup_vault.sh   Obsidian vault 폴더 초기화
└── setup_launchd.sh macOS 로그인 시 watch 자동 시작

prompts/             사람이 Claude Code 세션에 직접 붙여넣는 프롬프트 모음
├── README.md        역할 · 철학 · 확장 가이드
├── reflect.md       findings 기반 dimension 개선안 생성 (자기개선 루프)
└── service-analysis/           Spring Boot 서비스 분석 skill bundle
    ├── SKILL.md     메타데이터
    ├── orchestrator.md         메인 프롬프트 (얇은 조율자)
    ├── dimensions/             관점별 독립 파일 (identity · data-ownership · transactions · distributed-locking · domain-logic · forensics 등 12개)
    └── profiles/default.md     차원 조합 프리셋
```

각 파이프라인은 **프롬프트 빌드 → Claude 호출 → 구조화 파싱 → 파일 쓰기 → 로그/인덱스 갱신** 5단 구조.

`scripts/`의 프롬프트는 `call_claude()` subprocess 경유이고, `prompts/`의 프롬프트는 사람이 대화형 Claude Code 세션에 복붙한다 — 분석 대상 repo에서 실행되는 프롬프트이기 때문에 자동화가 아닌 수동 워크플로우.

---

## Claude CLI 호출 규약

`utils.call_claude()`가 유일한 LLM 호출 지점.

- 명령: `claude --dangerously-skip-permissions -p <prompt>`
- Popen + `communicate(timeout)` 패턴 (고아 프로세스 방지, 기본 300s)
- `debug=True` 시 raw 응답을 `/tmp/llm-wiki-debug.txt`에 덤프
- 비정상 종료 시 `RuntimeError` 발생

**새 파이프라인을 추가할 때도 반드시 이 함수를 통해 호출할 것.** 직접 subprocess를 부르지 말 것.

---

## 구조화 출력 프로토콜

Claude의 응답은 아래 3개 토큰 패턴으로 파싱:

```
===FILE: <path>===
<content>
===END===

===INDEX_UPDATE: <Section> | <slug> | <description>===  # ingest 전용
===FINDING: <slug> | <query_summary> | <description>===  # query 전용
===LOG: <message>===
```

정규식은 각 파이프라인 파일 상단에 선언 (`_FILE_PATTERN`, `_INDEX_PATTERN` 등).
**새 섹션 추가 시 regex와 프롬프트 템플릿을 동시에 수정할 것.**

프롬프트는 공통적으로 다음 순서:
1. 최우선 출력 규칙 (첫 문자 `=` 강제)
2. AGENTS.md 삽입 (wiki 스키마)
3. 컨텍스트 (wiki 상태 / 페이지 덤프)
4. 처리 대상 (소스 / 질문)
5. 지시사항 및 "지금 즉시 생성하라" 앵커

---

## 불변 규칙 (invariants)

수정 시에도 깨면 안 되는 규칙:

1. **LLM이 쓰고 사람은 읽는다** — wiki/*.md 수동 편집 금지. 예외: AGENTS.md 스키마 변경.
2. **log.md는 append-only** — `append_log(type, message)`만 사용. 덮어쓰기 금지.
3. **index.md는 항상 최신** — 새 페이지는 `update_index()`를 반드시 호출해 섹션에 등록.
4. **slug는 kebab-case** — `slugify()` 통과 필수. 영어 소문자·하이픈만.
5. **Obsidian wikilink 우선** — `[[slug]]` 사용. 플레인 URL은 외부 소스에만.
6. **lint_ignore.txt 존중** — 메타 슬러그(`wikilink`, `slug` 등)는 lint 스킵.

---

## 자주 수행하는 작업

### 새 CLI 명령 추가
1. `scripts/wiki.py`에 `@cli.command()` 추가
2. 로직은 `scripts/<name>.py`로 분리 (지연 import 패턴 유지)
3. Claude 호출이 필요하면 `utils.call_claude()` 경유

### 마이크로서비스 분석 워크플로우 지원

이 repo는 Spring Boot 마이크로서비스 분석 전용 흐름을 포함:

1. 분석 대상 repo에서 Graphify 실행 (권장)
2. `prompts/service-analysis/orchestrator.md`를 Claude Code에 복붙하여 서비스 1개 분석 (내부적으로 `dimensions/*.md` 12개를 순차 적용)
3. 출력을 `<vault>/raw/services/<service>.md`에 저장
4. `wiki ingest`가 일반 파이프라인으로 처리 — 단, `[[<other-service>]]` wikilink가 다수 포함되어 자동으로 서비스 간 그래프 형성

구체 스키마: [AGENTS.md — Service Analysis Protocol](./AGENTS.md#service-analysis-protocol-마이크로서비스-분석)
사용자 가이드: [README.md — 마이크로서비스 분석 워크플로우](./README.md#마이크로서비스-분석-워크플로우)

**주의**: 서비스 분석 markdown을 수정할 때는 ingest 파이프라인이 `[[wikilink]]` 정확도에 의존한다는 점 기억. 서비스명 slug가 일관되지 않으면 엔티티 중복 생성.

### 새 page type 추가 (예: `decisions/`)
1. `AGENTS.md` — Page Types 섹션에 frontmatter 스키마 정의
2. `config.yaml` — `wiki_subdirs`에 추가
3. `scripts/setup_vault.sh` — `mkdir -p` 추가
4. `utils.py` — `list_wiki_pages()`의 subdir 리스트, `_SECTION_MAP`, `read_wiki_pages()` subdirs 추가
5. `lint.py` — `SUBDIRS` 리스트 추가
6. `setup_vault.sh`의 `index.md` 초기 템플릿에 `## <Section>` 헤더 추가

### 프롬프트 수정
- `ingest.py` → `build_ingest_prompt()`
- `query.py` → `build_query_prompt()`
- `lint.py` → `_build_contradiction_prompt()`

수정 후 **반드시 `--debug` 플래그로 raw 응답 확인**. 파싱 실패 시 `===FILE:` 규약이 먼저 깨지는지 확인.

### 새 output 포맷 추가 (예: `--graph`)
1. `query.py`의 `_OUTPUT_FORMAT_INSTRUCTIONS`에 포맷 지시 추가
2. `build_query_prompt()`에서 확장자·경로 분기
3. `write_output_pages()` 뒤에 후처리 훅 추가 (차트는 `execute_chart()` 참조)
4. `wiki.py`의 `@click.option` flag 추가

---

## 디버깅 체크리스트

| 증상 | 확인 |
|------|------|
| "FILE 블록을 찾을 수 없습니다" | `--debug`로 raw 응답 확인 → 프롬프트 출력 규칙 강조 |
| Claude CLI not found | `claude --version`, `which claude` — Claude Code 설치 여부 |
| vault 경로 오류 | `config.yaml`의 `vault_path` 절대경로 확인 |
| index.md 불일치 | `wiki lint` → `--fix`로 dangling 자동 제거 |
| Orphan 폭증 | ingest 프롬프트가 `[[wikilink]]` 삽입 지시를 포함하는지 확인 |

---

## 코딩 컨벤션

- Python 3.10+, 타입 힌트 적극 사용
- 지연 import (`from ingest import run_ingest`를 명령 함수 안에서) — CLI 응답성 유지
- 에러는 `click.echo(..., err=True)` + `sys.exit(1)` 패턴
- 주석은 *왜*만 남기고 *무엇*은 코드로 표현
- 공통 로직은 `utils.py`에만

---

## 의존성

`requirements.txt`:
- `pyyaml` — config.yaml
- `click` — CLI
- `matplotlib` — `--chart` output
- `watchdog` — `watch` 명령

추가 의존성은 반드시 requirements.txt에 명시하고 이유를 commit message에 기록.

---

## 참고

- 원본 아이디어: [Karpathy의 LLM Knowledge Base gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- 실제 운영 규칙 & wiki 스키마: [AGENTS.md](./AGENTS.md)
- 사용자 문서: [README.md](./README.md)

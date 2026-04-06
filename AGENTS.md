# LLM Wiki — AGENTS.md (Wiki Schema & Operating Rules)

> **이 파일은 wiki를 유지·운영하는 LLM을 위한 규칙서입니다.**
> 사람이 wiki 파일을 직접 편집하는 일은 최소화하고, 모든 쓰기는 LLM이 담당합니다.

---

## 시스템 개요

```
llm-wiki/ (git repo — 시스템 코드)
obsidian-vault/llm-wiki/ (Obsidian — 데이터 & IDE)
  ├── raw/        ← 소스 문서 투하 지점 (Web Clipper, 수동 복사)
  ├── wiki/       ← LLM이 컴파일·유지하는 wiki
  │   ├── index.md
  │   ├── log.md
  │   ├── concepts/
  │   ├── entities/
  │   ├── summaries/
  │   └── findings/
  └── output/     ← Marp 슬라이드, matplotlib, 내보내기
```

**Config**: `config.yaml`의 `vault_path`로 경로 결정.

---

## Page Types & Frontmatter 스키마

### 1. Summary (`wiki/summaries/<slug>.md`)
소스 하나에 대한 요약. 인게스트할 때 반드시 생성.

```yaml
---
type: summary
source: "<원본 제목 또는 URL>"
source_file: "raw/<파일명>"
date_ingested: "YYYY-MM-DD"
topics: [<topic1>, <topic2>]
entities: [<entity1>, <entity2>]
concepts: [<concept1>, <concept2>]
---
```

### 2. Concept (`wiki/concepts/<slug>.md`)
특정 개념, 기법, 이론에 대한 아티클. 여러 소스를 종합.

```yaml
---
type: concept
title: "<개념명>"
aliases: [<별칭1>, <별칭2>]
related: [<concept_slug1>, <entity_slug1>]
sources: [<summary_slug1>, <summary_slug2>]
last_updated: "YYYY-MM-DD"
confidence: high | medium | low
---
```

### 3. Entity (`wiki/entities/<slug>.md`)
인물, 조직, 도구, 제품, 데이터셋 등 고유 명사.

```yaml
---
type: entity
entity_type: person | org | tool | dataset | paper | other
title: "<엔티티명>"
aliases: [<별칭>]
related: [<entity_slug1>, <concept_slug1>]
sources: [<summary_slug1>]
last_updated: "YYYY-MM-DD"
---
```

### 4. Finding (`wiki/findings/<slug>.md`)
Query에서 파생된 synthesis. 질문에 대한 답변을 wiki에 다시 파일링.

```yaml
---
type: finding
query: "<원래 질문>"
date: "YYYY-MM-DD"
related: [<concept_slug1>, <entity_slug1>]
sources: [<summary_slug1>]
output_files: [<output/파일명>]
---
```

---

## Ingest Protocol

소스 파일이 `raw/`에 추가될 때 다음 순서로 처리:

1. **소스 읽기**: `raw/<file>` 전체 내용 파악
2. **Summary 작성**: `wiki/summaries/<slug>.md` 생성 (frontmatter + 본문 요약)
3. **Entity 업서트**: 언급된 각 고유 명사에 대해 `wiki/entities/<slug>.md` 생성 또는 갱신
4. **Concept 업서트**: 언급된 각 개념에 대해 `wiki/concepts/<slug>.md` 생성 또는 갱신
   - 기존 페이지가 있으면: 새 소스를 `sources[]`에 추가하고 내용 보강
   - 없으면: 새 페이지 생성
5. **Cross-reference 삽입**: 모든 페이지에서 관련 페이지를 `[[wikilink]]`로 연결
6. **index.md 갱신**: 새 페이지를 해당 섹션에 한 줄 추가
7. **log.md 기록**: `[YYYY-MM-DD HH:MM] [INGEST] <source_file> → <n>개 페이지 갱신`

**한 소스당 영향 페이지**: 통상 10–20개 (summaries 1 + entities N + concepts M).

---

## Query Protocol

사용자 질문을 받았을 때:

1. **탐색**: `wiki/index.md`에서 관련 섹션 파악 → 해당 페이지들 읽기
2. **심층 탐색**: 페이지 내 `[[wikilink]]`를 따라 관련 페이지 추가 탐색
3. **합성**: 읽은 내용을 종합해 답변 구성 (citations 포함: `[[page_slug]]`)
4. **Output 생성** (선택):
   - 텍스트 답변: `output/<query_slug>.md`
   - 슬라이드: `output/<query_slug>.marp.md` (Marp frontmatter 포함)
   - 이미지: `output/<query_slug>.png` (matplotlib 코드 실행)
5. **Finding 파일링**: 가치 있는 답변은 `wiki/findings/<slug>.md`로 저장
6. **log.md 기록**: `[YYYY-MM-DD HH:MM] [QUERY] "<질문 요약>" → <output_file>`

---

## Lint Rules

주기적 wiki 건강 검사. 다음 이슈를 탐지·수정:

| 이슈 | 감지 방법 | 조치 |
|------|----------|------|
| **모순** | 같은 사실에 대한 상충 서술 | 최신 소스 우선, 노트 추가 |
| **Orphan 페이지** | `index.md`에 미등록 페이지 | index.md에 추가 |
| **Dead wikilink** | `[[slug]]`가 존재하지 않는 파일 참조 | 링크 수정 또는 페이지 생성 |
| **Stale claim** | `last_updated`가 6개월 이상 경과 + 업데이트된 소스 존재 | 재검토 표시 추가 |
| **Duplicate** | 유사 slug를 가진 중복 페이지 | 병합 또는 리다이렉트 |
| **Missing cross-ref** | 본문에 언급된 엔티티/개념에 `[[wikilink]]` 누락 | 링크 삽입 |

Lint 결과는 `wiki/findings/lint-report-<YYYY-MM-DD>.md`에 저장.

---

## Cross-reference Convention

- **내부 링크**: `[[slug]]` (Obsidian 네이티브 wikilink)
- **표시명 다를 때**: `[[slug|표시할 이름]]`
- **slug 규칙**: `kebab-case`, 영어 소문자, 특수문자 제외
  - 예: `attention-mechanism`, `andrej-karpathy`, `transformer-architecture`
- **Backlink 활용**: Obsidian Graph View에서 자동 시각화됨

---

## log.md 포맷

```
[YYYY-MM-DD HH:MM] [TYPE] message
```

- `TYPE`: `INGEST` | `QUERY` | `LINT` | `BOOTSTRAP` | `MANUAL`
- 예시:
  ```
  [2026-04-06 12:00] [BOOTSTRAP] Wiki initialized. Structure created.
  [2026-04-06 14:30] [INGEST] attention-is-all-you-need.md → 15개 페이지 갱신
  [2026-04-06 15:00] [QUERY] "트랜스포머 어텐션 메커니즘 비교" → output/transformer-attention-comparison.marp.md
  [2026-04-07 09:00] [LINT] 3 orphans, 2 dead links, 1 duplicate 감지·수정
  ```

---

## Output Format 규칙

### Marp 슬라이드 (`output/*.marp.md`)
```markdown
---
marp: true
theme: default
paginate: true
---

# 제목
---
## 슬라이드 1
...
```

### Matplotlib 이미지 (`output/*.png`)
- Python 코드는 `output/<name>.py`에 저장
- 생성 이미지는 `output/<name>.png`
- Finding 페이지에서 `![[output/<name>.png]]`로 임베드

---

## 운영 원칙

1. **LLM이 쓰고, 사람은 읽는다**: wiki 파일을 직접 편집하는 일은 최소화
2. **모든 변경은 log.md에 기록**: 추적 가능성 보장
3. **Obsidian wikilink 우선**: 단순 URL보다 `[[slug]]` 링크 사용
4. **점진적 축적**: 각 ingest/query는 기존 wiki를 파괴하지 않고 보강
5. **index.md는 항상 최신**: 새 페이지 생성 시 반드시 index.md 갱신

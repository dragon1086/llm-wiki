# LLM Wiki

Andrej Karpathy의 [LLM Knowledge Base 패턴](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 구현체.

LLM이 `raw/` 소스를 읽고 Obsidian vault 안에 wiki를 자동으로 컴파일·유지합니다.
사람은 읽고 질문하고, LLM이 쓰고 관리합니다.

---

## 구조

```
llm-wiki/                       ← 이 repo (시스템 코드)
├── AGENTS.md                   ← wiki 스키마 & LLM 운영 규칙
├── config.yaml                 ← vault 경로 설정
├── requirements.txt
└── scripts/
    ├── wiki.py                 ← CLI 진입점
    ├── ingest.py               ← raw/ → wiki 컴파일
    ├── query.py                ← wiki 탐색 + 합성
    ├── lint.py                 ← 정합성 검사
    ├── utils.py                ← 공통 유틸
    └── ingest_trends.sh        ← last30days 출력물 → raw/trending/ 복사 + ingest

obsidian-vault/llm-wiki/        ← Obsidian vault (데이터)
├── raw/
│   ├── trending/               ← last30days 트렌드 보고서 투하
│   └── ...                     ← Web Clipper, 수동 소스
├── wiki/
│   ├── index.md                ← 카탈로그 (LLM 자동 유지)
│   ├── log.md                  ← 운영 로그
│   ├── lint_ignore.txt         ← lint 예외 slug 목록
│   ├── concepts/               ← 개념 아티클
│   ├── entities/               ← 인물·조직·도구
│   ├── summaries/              ← 소스별 요약
│   └── findings/               ← query 파생 synthesis
└── output/                     ← 슬라이드, 차트, 내보내기
```

---

## 설치

### 1. 시스템 요구사항

- **Python 3.10+**
- **Claude Code CLI** — [claude.ai/code](https://claude.ai/code) 에서 설치 후 로그인
  ```bash
  claude --version   # 확인
  ```
- **Obsidian** — [obsidian.md](https://obsidian.md) 에서 설치

### 2. 레포 클론 & Python 환경

```bash
git clone <repo-url>
cd llm-wiki

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Obsidian vault 생성

Obsidian 앱에서:

1. **Open folder as vault** 클릭
2. `obsidian-vault/llm-wiki/` 폴더 선택 (없으면 먼저 생성)

vault 안에 필요한 디렉토리를 초기화합니다:

```bash
bash scripts/setup_vault.sh
```

> 이미 vault가 있다면 `config.yaml`의 `vault_path`를 해당 경로로 수정하세요.

### 4. config.yaml 수정

```yaml
vault_path: /Users/<your-name>/path/to/obsidian-vault/llm-wiki
```

---

## Obsidian 플러그인 설치

### Obsidian Web Clipper (브라우저 확장)

웹 페이지를 `raw/`에 바로 저장하는 도구입니다.

1. Chrome/Firefox에서 [Obsidian Web Clipper](https://obsidian.md/clipper) 설치
2. 확장 아이콘 클릭 → **Settings** 진입
3. **Vault** 항목에서 `llm-wiki` vault 선택
4. **Default location** → `raw/` 입력
5. **Template** (선택 사항):

   ```
   ---
   source: "{{url}}"
   date: "{{date}}"
   ---
   
   # {{title}}
   
   {{content}}
   ```

이후 웹 페이지에서 확장 아이콘 → **Clip** 하면 `raw/` 에 .md 파일로 저장됩니다.

### Marp for Obsidian (슬라이드 렌더링)

`wiki query "..." --slides` 로 생성한 `.marp.md` 파일을 Obsidian 안에서 미리볼 수 있습니다.

1. Obsidian 설정 → **Community plugins** → **Browse**
2. `Marp Slides` 검색 → **Install** → **Enable**
3. `.marp.md` 파일을 열면 우상단에 슬라이드 미리보기 버튼이 생깁니다.

> `--slides` 출력 파일에는 자동으로 `marp: true` frontmatter가 포함됩니다.

---

## 사용법

모든 커맨드는 repo 루트에서 실행합니다.

### ingest — 소스 → wiki 컴파일

```bash
# 단일 파일
python scripts/wiki.py ingest raw/article.md

# raw/ 미처리 파일 전체
python scripts/wiki.py ingest --all

# 디버그 (raw 응답을 /tmp/llm-wiki-debug.txt 저장)
python scripts/wiki.py ingest raw/article.md --debug
```

소스 1개당 생성되는 페이지:
- `wiki/summaries/<slug>.md` — 소스 요약
- `wiki/entities/<slug>.md` — 언급된 인물·도구·조직
- `wiki/concepts/<slug>.md` — 언급된 개념

### query — wiki 탐색 + 합성

```bash
# 텍스트 답변 (기본)
python scripts/wiki.py query "RAG가 왜 불필요한가?"

# Marp 슬라이드
python scripts/wiki.py query "LLM Wiki 시스템 설명" --slides

# Mermaid 다이어그램
python scripts/wiki.py query "LLM Wiki 데이터 흐름" --diagram

# matplotlib 차트 (코드 생성 + PNG 저장)
python scripts/wiki.py query "wiki 페이지 분포" --chart
```

결과 파일은 `output/`에 저장되고, 재사용 가치가 있는 답변은 `wiki/findings/`에 자동 파일링됩니다.

### lint — 정합성 검사

```bash
# 정적 검사 (dead links, orphans, index drift)
python scripts/wiki.py lint

# dangling index 항목 자동 제거
python scripts/wiki.py lint --fix

# LLM 모순 탐지 포함 (느림, Claude 호출)
python scripts/wiki.py lint --deep
```

lint_ignore.txt에 예외 slug를 등록할 수 있습니다:

```
# wiki/lint_ignore.txt
wikilink
slug
```

### trends — 플랫폼 트렌드 자동 수집

[last30days](https://github.com/mvanhorn/last30days-skill) 스킬로 Reddit, X/Twitter, YouTube, Hacker News 등 주요 플랫폼의 최근 30일 트렌드를 수집해 wiki로 인제스트합니다.

#### 전제 조건

```bash
# last30days 스킬 설치 (최초 1회)
git clone https://github.com/mvanhorn/last30days-skill.git ~/.claude/skills/last30days
```

#### 사용법

**Step 1 — 트렌드 수집** (Claude Code 세션에서)

```
/last30days LLM 최신 트렌드
/last30days Claude Code 프롬프팅 기법 --deep
/last30days reasoning model 비교 --days=7
```

결과 마크다운이 `~/Documents/Last30Days/`에 자동 저장됩니다.

**Step 2 — vault 인제스트** (터미널에서)

```bash
# 최신 보고서 1개 → raw/trending/ 복사 + ingest
bash scripts/ingest_trends.sh

# 오늘 생성된 보고서 전체
bash scripts/ingest_trends.sh --all

# 복사만 (ingest는 나중에 수동으로)
bash scripts/ingest_trends.sh --copy-only
```

Step 2 완료 후 `wiki/summaries/`, `concepts/`, `entities/`가 자동 갱신됩니다.

---

### watch — 자동 ingest

```bash
# raw/ 감시 시작 (Ctrl+C로 종료)
python scripts/wiki.py watch
```

`raw/`에 `.md` 파일이 새로 생성되면 1초 내 자동 ingest됩니다.
Web Clipper로 저장하는 순간 wiki가 업데이트됩니다.

#### macOS 로그인 시 자동 시작 (launchd)

한 번만 등록하면 로그인 후 항상 백그라운드에서 watch가 실행됩니다:

```bash
# 등록
bash scripts/setup_launchd.sh

# 로그 확인
tail -f /tmp/llm-wiki-watch.log

# 해제
bash scripts/setup_launchd.sh --remove
```

### status / list-raw

```bash
python scripts/wiki.py status     # wiki 현황 요약
python scripts/wiki.py list-raw   # raw/ 파일 목록 + ingest 여부
```

---

## 워크플로우 예시

### A. 웹 아티클 수집

```
1. 웹 페이지 읽다가 흥미로운 아티클 발견
   → Web Clipper로 raw/ 에 저장

2. python scripts/wiki.py ingest --all
   → LLM이 요약·개념·엔티티 페이지 자동 생성

3. Obsidian에서 Graph View로 지식 그래프 탐색

4. python scripts/wiki.py query "이 개념이 X와 어떻게 연결되나?" --diagram
   → 다이어그램 output/ 저장

5. 주기적으로 python scripts/wiki.py lint --fix
   → 깨진 링크, 누락 항목 정리
```

### B. 플랫폼 트렌드 수집 (last30days)

```
1. Claude Code에서 트렌드 수집
   /last30days LLM 최신 트렌드 --deep
   → ~/Documents/Last30Days/llm-latest-trends.md 저장

2. bash scripts/ingest_trends.sh
   → raw/trending/ 복사 + wiki 자동 인제스트

3. Obsidian에서 새로 생성된 summaries/, concepts/ 확인

4. python scripts/wiki.py query "이번 주 LLM 핵심 트렌드 요약" --slides
   → Marp 슬라이드로 브리핑 생성
```

---

## 운영 철학: 깊이 우선

> **많이 넣는 게 아니라 잘 넣는 게 목적입니다.**

### 왜 무작정 넣으면 안 되는가

`query.py`는 질문 키워드와 **slug 이름**을 비교해 최대 15개 페이지를 컨텍스트로 선택합니다.
wiki가 커질수록 관련 없는 페이지가 컨텍스트를 오염시키고 답변 품질이 하락합니다.

| wiki 규모 | 체감 품질 |
|----------|---------|
| ~50페이지 | 거의 무관 |
| 50~150페이지 | slug 미스 발생, query miss 체감 |
| 150페이지+ | 컨텍스트 오염 심화, 답변 부정확 |

**결론: 50~100개 고품질 페이지 + 자주 query > 500개 무작위 페이지**

### 소스 품질 기준

| 넣어야 할 것 | 넣지 말아야 할 것 |
|------------|----------------|
| 논문, 공식 문서, 심층 분석 포스트 | 단순 뉴스 기사, 요약만 있는 슬라이드 |
| 본인이 반복 참조하는 자료 | "언젠간 읽겠지" 자료 |
| last30days 결과 중 핵심 섹션만 편집 후 ingest | 트렌드 리포트 전체 그대로 ingest |

### last30days 필터링 원칙

`/last30days` 출력물을 그대로 ingest하지 마세요.
생성된 `.md`를 열어 **핵심 3~5개 항목만 남기고** 나머지를 삭제한 뒤 ingest합니다.
트렌드 요약 전체보다 "주목할 기법 3가지"가 훨씬 유용한 wiki 페이지가 됩니다.

### query를 많이 써야 ROI가 생긴다

ingest만 하고 query 안 하면 그냥 파일 창고입니다.
query로 finding을 쌓아야 wiki가 진짜 지식 베이스가 됩니다.

```bash
# 넣은 직후 바로 query 습관
python scripts/wiki.py query "방금 읽은 논문의 핵심 기법을 기존 지식과 비교해줘"
```

### lint 주기

```bash
python scripts/wiki.py lint --fix  # 2주에 1번 권장
```

페이지가 쌓이면 dead link, orphan이 생깁니다. 방치하면 `[[wikilink]]` 그래프가 망가집니다.

### 도메인 집중 권장

넓게 수집하지 말고, **본인이 실제로 query할 주제 3개**를 정하고 그 안에서만 채우세요.

```
좋음: "LLM 아키텍처 + 추론 기법 + 프롬프팅" 중심으로 밀도 있게 60페이지
나쁨: IT 아티클 무작위로 200페이지 때려넣기
```

---

## 시스템 아키텍처 & 개선 로드맵

### 현재 query 컨텍스트 수집 방식 (slug 매칭)

```python
# query.py:38-45 — 현재 구현
question_words = set(re.findall(r"\w+", question.lower()))
for slug in all_slugs:
    slug_words = set(re.split(r"[-_]", slug.lower()))
    score = len(question_words & slug_words)  # slug 이름 단어 교집합만
```

**한계**:
- slug에 키워드가 없으면 0점 → 내용이 관련 있어도 누락
- 전이적 관련성 없음 → A→B→C 연결에서 C가 관련 있어도 직접 매칭 안 되면 0점
- 페이지 중요도(연결도) 무시 → 핵심 허브 페이지와 외딴 페이지 동일 취급

### graphify 패턴 기반 개선 로드맵

[graphify](../graphify) 프로젝트(같은 철학: 지식 그래프 + 컨텍스트 효율화)에서 도출한 개선 방향:

#### v1 — BFS 1홉 확장 (즉시 적용 가능, ~10줄 코드)

slug 매칭 후 매칭된 페이지의 `[[wikilink]]`를 따라 **이웃 페이지를 1홉 확장**합니다.

```
현재: 질문 키워드 → slug 매칭 → 15페이지
개선: 질문 키워드 → slug 매칭 → 매칭 페이지의 [[wikilinks]] 파싱 → 이웃 페이지 추가
```

효과: "attention-is-all-you-need" slug가 직접 안 잡혀도 연결된 개념 페이지를 통해 도달 가능.

#### v2 — 연결도 기반 우선순위 + 토큰 예산

페이지의 `[[wikilink]]` 수(연결도)를 degree로 계산, **핵심 허브 페이지를 우선** 포함합니다.
15개 고정 대신 **토큰 예산** (예: 4000토큰) 기반으로 동적 선택합니다.

```
현재: 상위 15페이지 전문
개선: 연결도 높은 순 정렬 → 토큰 예산 소진까지 포함
```

#### v3 — Obsidian MCP full-text 검색 (이미 MCP 설정 완료)

slug 이름 대신 **페이지 본문 전체**를 검색합니다.
`~/.claude/settings.json`에 `obsidian` MCP가 이미 설정되어 있어 바로 활용 가능합니다.

---

## 운영 원칙

- **LLM이 쓰고, 사람은 읽는다** — wiki 파일 직접 편집 최소화
- **모든 변경은 log.md에 기록** — 추적 가능성 보장
- **Obsidian wikilink 우선** — `[[slug]]` 링크로 그래프 형성
- **점진적 축적** — ingest/query마다 wiki가 보강됨
- **깊이 우선** — 소스 품질 필터링, 도메인 집중, query 습관화

---

## Phase 현황

| Phase | 내용 | 상태 |
|-------|------|------|
| 1. Foundation | 디렉토리 구조, AGENTS.md, vault 네임스페이스 | ✅ |
| 2. Ingest | raw/ → wiki 컴파일 파이프라인 | ✅ |
| 3. Query | wiki 탐색 + 합성 + output 생성 (text/slides/diagram/chart) | ✅ |
| 4. Lint | dead links, orphans, index drift, 모순 탐지 | ✅ |
| 5. CLI | setup 스크립트, README, 플러그인 가이드 | ✅ |

---

## 참고

- [Karpathy 원문 Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [AGENTS.md](./AGENTS.md) — 상세 운영 규칙 및 LLM 지시사항
- [config.yaml](./config.yaml) — 경로·설정

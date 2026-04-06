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
    └── utils.py                ← 공통 유틸

obsidian-vault/llm-wiki/        ← Obsidian vault (데이터)
├── raw/                        ← 소스 투하 (Web Clipper, 수동)
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

```
1. 웹 페이지 읽다가 흥미로운 아티클 발견
   → Web Clipper로 raw/ 에 저장

2. wiki ingest --all
   → LLM이 요약·개념·엔티티 페이지 자동 생성

3. Obsidian에서 Graph View로 지식 그래프 탐색

4. wiki query "이 개념이 X와 어떻게 연결되나?" --diagram
   → 다이어그램 output/ 저장

5. 주기적으로 wiki lint --fix
   → 깨진 링크, 누락 항목 정리
```

---

## 운영 원칙

- **LLM이 쓰고, 사람은 읽는다** — wiki 파일 직접 편집 최소화
- **모든 변경은 log.md에 기록** — 추적 가능성 보장
- **Obsidian wikilink 우선** — `[[slug]]` 링크로 그래프 형성
- **점진적 축적** — ingest/query마다 wiki가 보강됨

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

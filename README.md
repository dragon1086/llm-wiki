# LLM Wiki

Andrej Karpathy의 [LLM Knowledge Base 패턴](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 구현체.

LLM이 `raw/` 소스를 읽고, Obsidian vault 안에 wiki를 자동으로 컴파일·유지합니다.
사람은 읽고 질문하고, LLM이 쓰고 관리합니다.

---

## 두 레이어 구조

```
llm-wiki/          (이 repo — 시스템 코드)
├── AGENTS.md      ← wiki 스키마 & LLM 운영 규칙
├── config.yaml    ← vault 경로 설정
└── scripts/       ← CLI 도구 (Phase 5)

obsidian-vault/llm-wiki/   (Obsidian IDE — 데이터)
├── raw/           ← 소스 투하 (Web Clipper, 수동 복사)
├── wiki/          ← LLM이 컴파일·유지
│   ├── index.md   ← 카탈로그
│   ├── log.md     ← 운영 로그
│   ├── concepts/  ← 개념 아티클
│   ├── entities/  ← 인물·조직·도구
│   ├── summaries/ ← 소스별 요약
│   └── findings/  ← query 파생 synthesis
└── output/        ← Marp 슬라이드, 이미지, 내보내기
```

---

## 핵심 워크플로우

### Ingest
소스를 `raw/`에 투하하면 LLM이 wiki를 자동 컴파일:
```
raw/<source>.md → summaries/ → entities/ & concepts/ → index.md 갱신 → log.md 기록
```

### Query
```
질문 → wiki 탐색 (index.md + [[wikilinks]]) → 합성 → output/ 저장 → findings/ 파일링
```

### Lint
```
주기적 건강 검사 → 모순·orphan·dead link 감지 → 자동 수정 → lint-report 저장
```

---

## Phase 로드맵

| Phase | 내용 | 상태 |
|-------|------|------|
| 1. Foundation | 디렉토리 구조, AGENTS.md 스키마, 템플릿 | ✅ 완료 |
| 2. Ingest | raw/ → wiki 컴파일 파이프라인 (ralph loop) | 🔲 |
| 3. Query | wiki 탐색 + 합성 + output 생성 | 🔲 |
| 4. Lint | 건강 검사 + 자동 수정 (team agents) | 🔲 |
| 5. CLI | `wiki ingest/query/lint` 커맨드라인 도구 | 🔲 |

---

## Obsidian 플러그인 권고

| 플러그인 | 용도 |
|--------|------|
| [Marp for Obsidian](https://github.com/samuele-cozzi/obsidian-marp-slides) | `output/*.marp.md` 슬라이드 렌더링 |
| [Obsidian Web Clipper](https://obsidian.md/clipper) | 웹 아티클 → `raw/` 자동 저장 |

---

## 운영 원칙

- **LLM이 쓰고, 사람은 읽는다**: wiki 파일 직접 편집 최소화
- **모든 변경은 log.md에 기록**: 추적 가능성 보장
- **Obsidian wikilink 우선**: `[[slug]]` 링크로 그래프 형성
- **점진적 축적**: ingest/query마다 wiki가 보강됨

---

## 참고

- [Karpathy의 원문 트위터](https://x.com/karpathy)
- [AGENTS.md](./AGENTS.md) — 상세 운영 규칙
- [config.yaml](./config.yaml) — 경로 설정

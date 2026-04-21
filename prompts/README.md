# prompts/

llm-wiki의 **ingest 파이프라인 바깥**에서 사람이 Claude Code에 직접 붙여 넣는 프롬프트 모음.

## vs. scripts/ 내부 프롬프트

| 위치 | 실행 주체 | 사용처 |
|------|----------|--------|
| `scripts/*.py`의 `build_*_prompt()` | Python이 `claude -p` subprocess로 호출 | ingest / query / lint 자동화 |
| `prompts/*.md` · `prompts/*/` | 사람이 Claude Code 세션에 복붙 | 분석 소스 생성, 특수 작업 |

## 구성

```
prompts/
├── README.md
├── service-analysis/              ← Spring Boot 서비스 1개 분석 skill bundle
│   ├── SKILL.md
│   ├── orchestrator.md            ← 메인 프롬프트. 복사해서 Claude Code에 붙여넣기
│   ├── dimensions/                ← 분석 관점별 독립 파일 (각 ~50~100줄)
│   │   ├── identity.md
│   │   ├── data-ownership.md
│   │   ├── api-inbound.md
│   │   ├── transactions.md
│   │   ├── outbound-calls.md
│   │   ├── messaging.md
│   │   ├── scheduling.md
│   │   ├── distributed-locking.md
│   │   ├── retry-failure.md
│   │   ├── infra.md
│   │   └── forensics.md
│   └── profiles/
│       └── default.md
└── reflect.md                     ← 자기개선 메타 프롬프트. findings 보고 dimension 개선안 제안
```

## 철학

- **차원(dimension) 분리**: "무엇을 볼 것인가"를 관점별 독립 파일로 쪼갬 → 새 관점은 파일 하나 추가
- **얇은 조율자(orchestrator)**: 차원을 순차 적용하고 출력을 조립. 로직이 아니라 구성
- **프로파일(profile)**: 서비스 유형별 차원 조합 프리셋
- **반영 루프(reflect)**: 누적 findings 를 보고 dimension 개선안을 제안하는 메타 프롬프트

## 확장 가이드

### 새 분석 관점 추가

`prompts/service-analysis/dimensions/<new>.md` 1개 파일을 만들고, `profiles/default.md` 에 순서를 추가.
각 dimension 파일은 다음 5섹션:

1. **Intent** — 이 관점이 왜 중요한가
2. **What to look for** — 코드에서 스캔할 패턴
3. **Output section template** — 결과 markdown의 해당 섹션 형식
4. **Forensic prompts** — "왜?" 질문들
5. **When absent** — 패턴 미발견 시 기록 방식

### 새 프로파일 추가

`prompts/service-analysis/profiles/<type>.md` — 차원 목록과 순서만 정의.

### Claude Code Skill으로 승격

안정화 후:
```bash
mkdir -p ~/.claude/skills
ln -s ~/workspace/llm-wiki/prompts/service-analysis ~/.claude/skills/service-analysis
```
→ 이후 어떤 서비스 repo에서도 `/service-analysis` 로 호출 가능.

## 운영 흐름

```
1. 서비스 분석  (대상 repo에서 Claude Code + service-analysis/orchestrator.md)
      ↓
2. raw/services/<name>.md 저장 + ingest  (llm-wiki pipeline)
      ↓
3. findings/ 축적
      ↓
4. 월 1회 reflect.md 실행  → dimension 개선안 받기
      ↓
5. 채택분 dimensions/ 에 반영 → 다음 분석부터 자동 적용
```

---
name: service-analysis
description: Spring Boot (Java/Kotlin) 마이크로서비스 1개를 심층 분석해 llm-wiki raw/services/ 에 적재할 markdown을 생성
version: 2
entry: orchestrator.md
applies_to:
  - Java / Kotlin + Spring Boot
  - 회사 마이크로서비스 분석 / 온보딩
  - 크로스 서비스 워크플로우 추적 (llm-wiki와 연계)
---

# service-analysis skill

한 개의 Spring Boot 마이크로서비스 repo를 깊이 이해하기 위한 분석 프롬프트 번들.

## 구조

```
service-analysis/
├── SKILL.md          ← 이 파일 (메타데이터)
├── orchestrator.md   ← Claude에게 건네주는 메인 프롬프트. 차원을 순차 로드
├── dimensions/       ← 분석 관점별 독립 파일
└── profiles/         ← 차원 조합 프리셋
```

## 사용 흐름

1. 분석 대상 repo에서 Graphify 선행 실행 (권장)
2. 대상 repo에서 Claude Code 세션 시작
3. [`orchestrator.md`](./orchestrator.md) 본문을 Claude Code에 복사·붙여넣기
4. Claude가 다음 순서로 작업:
   - `build.gradle.kts` / `pom.xml` 스캔 → 프로파일 자동 선택 (또는 사용자가 `profile:` 지정)
   - 프로파일에 포함된 각 `dimensions/*.md`를 순차 로드·적용
   - 마지막에 `dimensions/forensics.md`로 "왜?" 섹션 채우기
5. 출력을 `~/workspace/obsidian-vault/llm-wiki/raw/services/<service>.md`에 저장
6. `python scripts/wiki.py ingest raw/services/<service>.md`

## 확장

- **새 관점 추가**: `dimensions/<new>.md` 1개 파일만 추가. `default.md` 프로파일에 이름 추가.
- **서비스 유형별 맞춤**: `profiles/<type>.md` 추가. 예: `event-heavy.md` (messaging 비중 강화).
- **자동 진화**: `scripts/wiki.py reflect` → findings/ 축적분 기반으로 dimension 개선안 제안.

## Claude Code Skill으로 승격 (선택)

안정화 후 `~/.claude/skills/service-analysis/` 로 심볼릭 링크하면 `/service-analysis` 슬래시 커맨드로 호출 가능:

```bash
mkdir -p ~/.claude/skills
ln -s ~/workspace/llm-wiki/prompts/service-analysis ~/.claude/skills/service-analysis
```

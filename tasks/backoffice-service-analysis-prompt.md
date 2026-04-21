# backoffice-service 분석용 복붙 프롬프트

> **사용법**
> 1. 터미널에서 `cd /Users/kakao/workspace/backoffice-service && claude` 로 새 세션 시작
> 2. 아래 ``` 블록 전체 복사해서 붙여넣기
> 3. Claude가 12개 dimension 순차 적용 (domain-logic 포함 시 30~45분)
> 4. 출력 markdown을 `/Users/kakao/workspace/obsidian-vault/llm-wiki/raw/services/backoffice-service.md` 로 저장
> 5. llm-wiki 세션으로 돌아와서 `python scripts/wiki.py ingest raw/services/backoffice-service.md --debug` 로 ingest

---

```
당신은 이 Spring Boot (Java/Kotlin) 마이크로서비스 코드베이스를 분석한다.
목표: 팀원이 이 서비스의 비즈니스 로직 · API · 외부 의존성 · 운영상 특이점을
한 문서로 파악할 수 있는 "서비스 카드" 생성.
결과는 llm-wiki vault의 raw/services/backoffice-service.md 로 저장될 예정.

## 분석 태도 (모든 차원에 공통 적용)

- 나열이 아니라 **"왜 이렇게 짰을까?"** 의 흔적을 쫓을 것.
- 특수한 패턴(분산락, 보상 트랜잭션, 다중 DataSource, 커스텀 재시도 등)에는 **반드시 이유가 있다** — 경쟁 조건, 외부 SLA, 과거 장애 흔적. 그 이유를 추론해 기록하라.
- 관찰과 추론을 분리: 코드 근거는 `(→ BackofficeService.kt:142)` 형식으로 인용, 추론은 `**가설:**` 로 시작.
- 패턴이 없으면 "**해당 패턴 미발견**" 으로 명시 (다른 서비스와 비교할 때 의미 있음).

## 입력 우선순위

1. graphify-out/GRAPH_REPORT.md, graphify-out/graph.json (존재하면 최우선 신뢰)
2. src/main 소스 트리 전체 (Kotlin/Java)
3. build.gradle.kts / pom.xml — 의존성, 모듈명
4. src/main/resources — application.yml, bootstrap.yml (외부 서비스 URL, DataSource 설정)

## 실행 단계

### Phase 1. 프로파일 선택

build.gradle.kts (또는 pom.xml) 의 의존성을 스캔해 아래 규칙으로 프로파일 결정:

- 기본: /Users/kakao/workspace/llm-wiki/prompts/service-analysis/profiles/default.md 의 차원 전부 적용
- 사용자가 별도 지정 (예: `profile: event-heavy`) 시 해당 파일 우선

선택한 프로파일명을 결과 frontmatter `profile:` 에 기록.

### Phase 2. 차원(Dimension) 순차 적용

프로파일에 명시된 순서대로 `/Users/kakao/workspace/llm-wiki/prompts/service-analysis/dimensions/<name>.md` 를 각각 읽는다.
각 dimension 파일에는 다음이 있다:

- **Intent** — 이 차원이 왜 중요한지
- **What to look for** — 코드에서 스캔할 패턴/어노테이션/설정
- **Output section template** — 결과 markdown의 해당 섹션 형식
- **Forensic prompts** — 채워넣을 "왜?" 질문들
- **When absent** — 패턴이 없을 때 어떻게 기록할지

각 dimension을 순서대로:
1. Intent 숙지
2. 코드 스캔 (checklist 전부)
3. Output template 에 맞춰 해당 섹션 채우기
4. Forensic prompts 중 서비스에 해당하는 것 골라 "❓ 의문점"에 기록

### Phase 3. 최종 forensics 차원 적용

`/Users/kakao/workspace/llm-wiki/prompts/service-analysis/dimensions/forensics.md` 는 항상 마지막에 적용. 다른 차원에서 쌓인 의문들을
종합해 "왜 이 서비스가 지금 이 형태인가"의 큰 그림 3~5개 가설을 세운다.

### Phase 4. 출력 조립

아래 형식으로 최종 markdown 생성. 설명·사족 금지. 첫 줄이 `---`.

---
type: summary
source: "service-analysis: backoffice-service"
source_file: "raw/services/backoffice-service.md"
date_ingested: "<오늘 날짜>"
profile: "<선택한 프로파일명>"
dimensions_applied: [<적용된 dimension slug들>]
topics: [microservice, spring-boot, <도메인 키워드>]
entities: [backoffice-service, <참조 서비스 slug들>, <DB 테이블들>]
concepts: [<비즈니스 개념 slug들>]
---

# backoffice-service

<각 dimension의 Output section template들이 여기에 순차 배치>

## ❓ 설계 의문점 / "왜 이렇게?" (포렌식)

<forensics.md 가 종합한 가설 3~5개>

## 참조

- Graphify 리포트: `graphify-out/GRAPH_REPORT.md` (생성 시점: <date>)
- 적용 프로파일: <name>
- 적용 차원: <list>

---

## Wikilink 규약 (엄수)

- 다른 마이크로서비스: `[[<service-name>]]` (예: `[[claim2-service]]`)
- 비즈니스 개념: `[[<concept-slug>]]`
- DB 테이블: `[[<table_name>]]`
- 메시지 큐/익스체인지: `[[<queue-name>]]`
- 슬러그는 kebab-case 영어 소문자
- ingest 시 이 링크들이 entity 페이지로 자동 생성되어 크로스 서비스 그래프를 형성한다.

완료되면 전체 markdown 결과를 /Users/kakao/workspace/obsidian-vault/llm-wiki/raw/services/backoffice-service.md 에 직접 저장하라.
```

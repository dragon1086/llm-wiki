# Handoff — 2026-04-21 → 다음 작업 세션

> 이 문서를 먼저 읽으면 오늘의 맥락을 1분 안에 복원할 수 있습니다.
> 이어서 "다음 세션에서 할 일" 섹션을 따라가면 됩니다.

---

## TL;DR (30초)

- **브랜치**: `feature/microservice-analysis` (미커밋, 오늘 변경량 큼)
- **파이프라인 단계**: **build 완료 → use 단계 진입**
- **wiki 현황**: 10개 서비스 전부 ingest 완료 · 335 페이지 (summaries 14 · concepts 135 · entities 175 · findings 11)
- **남은 1차 목표**: query 로 비즈니스 플로우/크로스서비스 합성
- **남은 2차 목표**: 인터랙티브 워크플로우 시각화 (Mermaid 먼저, 부족하면 단일 HTML)

---

## 오늘 완료 (2026-04-21)

### 파이프라인 검증 · 강화

- claim2-service 첫 분석 → 첫 query("반품→환불") 성공 → 플로우 합성 가치 확인
- **`domain-logic` dimension 신설** (12번째) — Service 메서드 본문 기반 비즈니스 규칙 추출. 과적합 방지 + `extra_methods` 파라미터로 동적 확장 가능
- 버그 수정:
  - `call_claude` timeout 300→900s (ingest/query 양쪽)
  - `parse_claude_output` 경로 화이트리스트 (Claude의 `<br>` 같은 HTML 태그 환각 차단)
  - INDEX_UPDATE slug 검증 (sanitizer-rejected 파일이 index에 dangling 되는 버그)

### 대규모 ingest

- 9개 추가 서비스 분석 프롬프트 생성 (`tasks/<svc>-analysis-prompt.md`)
- 10개 서비스 전체 순차 ingest 완료 — 67분 소요, exit 0 × 10
- 누적: 생성 235 · 갱신 76 = 311 write 작업

### 문서화

- `tasks/service-analysis-playbook.md` 신설 — 서비스 분석 8단계 절차 · 트러블슈팅 · 체크리스트
- `CLAUDE.md`/`README.md`/`claim2-analysis-prompt.md` — 11→12 dimension 반영

### 메모리 저장

- `user_context`: 분석 우선순위 명확화 (1순위 플로우 체이닝, 2순위 기술 카탈로그)
- `project_analysis_priority`: orchestrator 편향과 query 역할
- `project_service_scope`: 10개 MSA 스코프 + 진행 상태
- `feedback_honest_pushback`: 근거 있는 반대 환영

---

## 지금 wiki 상태

```
~/workspace/obsidian-vault/llm-wiki/
├── raw/services/          ← 10개 서비스 카드 (원본)
│   ├── claim2-service.md        42KB (12 dimension)
│   ├── order-service.md         43KB
│   ├── payment-service.md       46KB
│   ├── cart-service.md          51KB
│   ├── delivery-service.md      53KB  ← 가장 큼
│   ├── partner-service.md       31KB
│   ├── settlement-service.md    35KB
│   ├── closing-service.md       35KB
│   ├── interface-service.md     52KB
│   └── backoffice-service.md    38KB
└── wiki/                  ← 335 페이지 지식 그래프
    ├── summaries/         14
    ├── concepts/         135   ← domain-logic 덕에 급증
    ├── entities/         175   ← 서비스 · DB 테이블 · 메시지 큐 등
    └── findings/          11   ← 이전 query 결과 캐시
```

**lint 상태**: 52 dead wikilinks (인프라 stub 누락 · payment DB 테이블 frontmatter 누락 · 레거시 2건). **즉시 급하지 않음** — 대부분 stub만 만들면 해결.

---

## 다음 세션에서 할 일 (권장 순서)

### Step 1. 플로우 합성 query (1차 목표 · 바로 실행 가능)

```bash
cd /Users/kakao/workspace/llm-wiki

# 텍스트 합성
python3 scripts/wiki.py query "주문 생성부터 정산 완료까지 10개 서비스 전체 체이닝" --debug

# Mermaid 다이어그램
python3 scripts/wiki.py query "반품 플로우의 크로스서비스 체이닝" --diagram
```

결과는 `output/*.md` + `wiki/findings/*.md` 에 자동 파일링. Obsidian 에서 Mermaid 렌더링됨.

추천 query 목록:
- 주문 생성 → 결제 → 배송 → 정산
- 반품/교환/재배송의 분기 조건 · 공통/차이점
- 결제 취소의 3가지 환불 경로 (일반/계좌/적립금)
- partner-service 의 동시성 제어 계약

### Step 2. 결과 품질 평가 → dimension 튜닝 판단

- 특정 서비스에서 합성이 얕다 → 해당 서비스 `raw/services/*.md` 프롬프트 보강 후 재분석
- 특정 주제가 부족 → `dimensions/` 새 차원 추가 or 기존 차원 강화

### Step 3. (선택) 인터랙티브 뷰어 — 옵션 B

Mermaid로 부족하면 단일 HTML 뷰어 (Cytoscape.js + vanilla JS). 
- wiki 그래프를 JSON으로 export (`wiki export --json` 신설)
- 300~500줄 HTML 1개
- 기능: 서비스/개념별 highlight, chain traversal, zoom
- 예상 1~2시간

### Step 4. (선택) dead link 정리

- 인프라 entity stub 일괄 생성 (mongodb · kafka · kakao-rabbitmq 등)
- payment-service frontmatter 에 누락 DB 테이블 추가 후 재ingest

### Step 5. (선택) reflect 루프

3개 서비스 넘는 분석 완료 조건 충족. `prompts/reflect.md` 붙여넣어 findings 기반 dimension 개선안 생성.

---

## 미결 TODO

- [ ] query → `output/*.diagram.md` (Mermaid) 첫 실험
- [ ] payment-service frontmatter 에 DB 테이블 10여개 추가 후 재ingest
- [ ] 인프라 entity stub 생성 방침 결정 (bulk / on-demand / lint ignore)
- [ ] findings regex 한글 허용 검토 (`_ALLOWED_PATH` · `_ALLOWED_SLUG`)
- [ ] 단일 HTML 뷰어 구축 여부 판단 (query 결과 품질 따라)
- [ ] 팀 공유 준비 (config.yaml → gitignore · config.example.yaml · README setup 섹션)

---

## 설계 결정 요약 (다음 세션이 참고할 것)

1. **vault 는 단일 경로 유지** (`~/workspace/obsidian-vault/llm-wiki`). 서비스별 분리 금지.
2. **1순위 = 플로우 체이닝 · 2순위 = 기술 카탈로그**. orchestrator 가 2순위 편향이므로 1순위는 query 책임.
3. **dimension 은 markdown 유지**. JSON 화는 오히려 손해 (LLM 파싱 손실, reflect diff 악화).
4. **각 서비스 분석은 별도 Claude 세션** (컨텍스트 오염 · cwd · 역할 분리 3가지 이유).
5. **domain-logic 은 최대 상한 X, 휴리스틱 기반 선정**. `extra_methods` 로 동적 확장.

---

## 다음 세션에서 Claude 에게 줄 프롬프트 (복붙용)

```
llm-wiki 프로젝트 (feature/microservice-analysis 브랜치) 이어서 작업할게.
어제까지 10개 마이크로서비스를 전부 ingest 해서 wiki 에 335 페이지 지식 그래프가 쌓였어.
오늘은 1차 목표인 "완성도 높은 데이터로 플로우 체이닝 query 뽑기" 부터 진행하자.

먼저 tasks/handoff.md 를 읽고 현재 상태를 복원해줘.
그다음 "다음 세션에서 할 일" Step 1 의 query 2~3개를 같이 돌려보고 결과 품질 평가하자.
Mermaid 다이어그램도 같이 확인.
```

---

## 참고

- 운영 가이드: [`CLAUDE.md`](../CLAUDE.md)
- 스키마: [`AGENTS.md`](../AGENTS.md)
- 분석 절차: [`tasks/service-analysis-playbook.md`](./service-analysis-playbook.md)
- 서비스별 분석 프롬프트: [`tasks/<service>-analysis-prompt.md`](./) × 10
- dimension 파일: [`prompts/service-analysis/dimensions/`](../prompts/service-analysis/dimensions/)
- 이전 query 결과: `<vault>/output/` + `<vault>/wiki/findings/`

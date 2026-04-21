# 서비스 분석 Playbook

> Spring Boot 마이크로서비스 1개를 llm-wiki 지식 그래프에 편입하고 크로스서비스 워크플로우 체이닝 분석 자료를 생성하기까지의 전체 과정.
>
> **사례 기준**: claim2-service (2026-04-21 첫 적용). 다음 서비스는 이 문서 순서대로 수행.

---

## 전제 준비 (한 번만)

- [ ] llm-wiki repo 클론 · `pip3 install -r requirements.txt`
- [ ] `config.yaml` 의 `vault_path` 절대경로 지정 (개인 로컬)
- [ ] `mkdir -p <vault>/raw/services <vault>/wiki/{summaries,entities,concepts,findings}`
- [ ] Claude Code (`claude` CLI) 설치 확인
- [ ] graphify 설치: `/graphify` 스킬 첫 실행 시 자동 설치됨

---

## Step 0 — 서비스 선정

다음 서비스를 정할 때 우선순위:

1. 기존 분석된 서비스의 `wiki/entities/<other-service>.md` 에 **"분석 대기 항목"** 이 많이 쌓인 서비스
2. 현 크로스서비스 그래프에서 claim2가 가장 많이 언급한 서비스
3. 비즈니스 플로우 상 다음 의문을 푸는 서비스 (예: claim2 → payment-service 의 DKPG 멱등키)

**현재 대기열** (2026-04-21 기준): `order-service` > `payment-service` > `delivery-service` / `goodsflow` > `item-service`

---

## Step 1 — Graphify 정적 그래프 (5~10분)

분석 대상 repo에서:

```bash
cd /path/to/<service>-repo
# Claude Code 세션 안에서
/graphify .
```

- **AST-only 기본**. Semantic 추출은 건너뛰어도 충분 (dimension이 코드 직접 읽음)
- 산출물: `graphify-out/` (GRAPH_REPORT.md · graph.json · manifest.json · cache)
- 대형 레포(5000+ 노드)는 HTML 뷰 자동 생략 — 정상
- **재실행 시**: `/graphify . --update` (변경 파일만 증분) / `/graphify . --cluster-only` (커뮤니티만 재계산, 무료)

---

## Step 2 — vault 디렉토리 확인

```bash
ls <vault_path>/raw/services/
# 없으면: mkdir -p <vault_path>/raw/services
```

---

## Step 3 — 서비스 분석 프롬프트 준비

```bash
# llm-wiki repo 에서
cp tasks/claim2-analysis-prompt.md tasks/<service>-analysis-prompt.md
```

새 파일에서 3군데 치환:

- `claim2-service` → `<service-slug>` (예: `order-service`)
- 맨 위 "사용법" 섹션의 경로도 서비스명 반영

---

## Step 4 — 서비스 분석 실행 (30~45분)

**별도 터미널에서 새 Claude 세션 필수** (컨텍스트 오염 · cwd 상대경로 · 역할 분리 이유):

```bash
cd /path/to/<service>-repo
claude
```

세션 안에서:

1. `<llm-wiki>/tasks/<service>-analysis-prompt.md` 의 ``` 블록 **내부만** 복사
2. 붙여넣기
3. Claude 가 수행:
   - `build.gradle.kts` / `pom.xml` 스캔 → profile 선택 (default = 12 dimension 전수)
   - 12 dimension 순차 적용 (identity · data-ownership · api-inbound · transactions · outbound-calls · messaging · scheduling · distributed-locking · retry-failure · infra · **domain-logic** · forensics)
   - `domain-logic` 은 Service 메서드 본문 직접 읽음 → 가장 느린 단계
4. 결과 markdown 을 `<vault>/raw/services/<service>.md` 로 저장

### 4a. domain-logic 에 추가 메서드를 지정하고 싶을 때

프롬프트 상단에 한 줄 추가:

```
extra_methods: ["com.pkg.SomeService#doThing", "com.pkg.OtherService#compute"]
```

---

## Step 5 — ingest (llm-wiki 쪽, 5~15분)

```bash
cd /path/to/llm-wiki
python3 scripts/wiki.py ingest raw/services/<service>.md --debug
```

기대 산출물:

- `wiki/summaries/<service>.md` (요약 1장)
- `wiki/entities/<service>.md` (entity_type=service)
- `wiki/entities/<참조 서비스>.md` × N (이미 있으면 갱신, 없으면 placeholder 생성)
- `wiki/entities/<DB 테이블>.md` × N (entity_type=db_table)
- `wiki/concepts/<비즈니스 개념>.md` × N
- `wiki/concepts/<메서드 or 규칙>.md` × N ← **domain-logic 기반 신규**
- `wiki/index.md` 갱신

### 트러블슈팅

| 증상 | 확인 |
|---|---|
| `claude CLI가 900초 내에 응답 X` | raw가 너무 큼 → 반으로 쪼개거나 dimension 축소 |
| `⚠ 비정상 경로 스킵` | Claude 경로 환각 — 자동 처리됨, 무시 가능 |
| "FILE 블록을 찾을 수 없음" | `/tmp/llm-wiki-debug.txt` 확인 → 프롬프트 출력 규칙 위반 |

---

## Step 6 — 크로스서비스 플로우 합성 (query)

각 주요 유스케이스에 대해 query 1회:

```bash
python3 scripts/wiki.py query "<service>에서 <유스케이스> 전체 비즈니스 플로우를 단계별로 합성하고, 각 단계에서 어떤 다른 MSA가 어떻게 연계되는지 명시" --debug
```

서비스별 추천 쿼리:

| 서비스 | 추천 유스케이스 |
|---|---|
| order-service | "주문 생성 · 결제 확정 · 주문 취소 플로우" |
| payment-service | "결제 승인 · DKPG 연동 · 환불 플로우 · 멱등성 보장 구조" |
| delivery-service | "배송 상태 전이 · 택배사 연동 · 재배송 처리" |
| item-service | "재고 예약 · 차감 · 원복 플로우 · 쿠폰 연동" |

결과: `output/*.md` + `wiki/findings/*.md` (자동 파일링)

---

## Step 7 — 정합성 점검

```bash
python3 scripts/wiki.py lint
```

- **Dead wikilink**: 해당 페이지의 frontmatter entities 에서 누락된 경우 많음 → raw 파일 수정 후 재ingest
- **Orphan**: 생성되었으나 어디서도 참조 안 되는 페이지 → 다음 서비스 분석에서 자연스럽게 연결되면 OK
- **Index drift**: `wiki lint --fix` 로 자동 수정 가능한 항목만 처리

---

## Step 8 — Obsidian Graph View 육안 검증

`<vault_path>/` 를 Obsidian vault 로 열기. 확인:

- [ ] 새 서비스 노드가 기존 서비스 노드들과 연결됨
- [ ] DB 테이블 · 비즈니스 개념 노드가 적절히 분포
- [ ] 고립 노드(orphan) 의심되는 지점 없음
- [ ] 이전 서비스 entity 의 "분석 대기 항목" 이 감소

---

## 반복 적용 · 품질 개선 루프

3개 이상 서비스 분석 완료 후:

```bash
# prompts/reflect.md 를 복사해 Claude Code 에 붙여넣기
# findings/ 전수 읽고 dimension 개선안 생성
```

개선안을 검토 후 `prompts/service-analysis/dimensions/*.md` 수동 수정.

---

## 체크리스트 (서비스당 1회)

- [ ] Step 1. Graphify 산출물 생성
- [ ] Step 2. vault 디렉토리 준비
- [ ] Step 3. 분석 프롬프트 복사·치환
- [ ] Step 4. 분석 세션 실행 → `raw/services/<service>.md` 저장
- [ ] Step 5. ingest 실행 → 페이지 생성 확인
- [ ] Step 6. 최소 2개 유스케이스에 대해 query 실행
- [ ] Step 7. lint 통과 (dead link 3개 이하)
- [ ] Step 8. Obsidian Graph View 점검
- [ ] 2번째 유스케이스 query 결과의 "분석 대기 항목" 을 다음 서비스 선정 근거로 활용

---

## 팀 공유 준비 (후속)

repo 를 팀과 공유하려 할 때 필요한 작업 (현재 미완):

- [ ] `config.yaml` 을 `.gitignore` 에 추가 · `config.example.yaml` 제공
- [ ] README 에 팀원 setup 가이드 섹션 추가
- [ ] 분석 결과(`raw/services/*.md`) 공유 방식 결정 (개인 vault / 공용 private repo / 공유 raw-only)
- [ ] dimension 파일 자체의 품질 편차 모니터링 (reflect 루프 활용)

---

## 참고 링크

- 뼈대: [`CLAUDE.md`](../CLAUDE.md) — 운영 규칙 · 불변식
- 스키마: [`AGENTS.md`](../AGENTS.md) — wiki 페이지 schema · 서비스 분석 protocol
- 원본 분석 프롬프트: [`prompts/service-analysis/orchestrator.md`](../prompts/service-analysis/orchestrator.md)
- 12 dimension 파일: [`prompts/service-analysis/dimensions/`](../prompts/service-analysis/dimensions/)
- 첫 사례 결과: `<vault>/raw/services/claim2-service.md` (외부)
- 자기개선 루프: [`prompts/reflect.md`](../prompts/reflect.md)

# Dimension: Domain Logic (비즈니스 규칙 · 계산 · 검증)

## Intent

기술 카탈로그(락 · 트랜잭션 · 메시징)만으로는 **"이 서비스가 무엇을 계산하고 어떤 조건으로 판단하는가"** 가 드러나지 않는다. 이 차원은 Service 메서드 본문을 읽어 **비즈니스 규칙, 금액/기간/수량 공식, 검증 순서, 상태 전이 조건, 분기 이유**를 추출한다.

다른 차원들이 "어디에서 일어나는가"를 매핑했다면, 이 차원은 "**무엇이 · 왜**"를 기록한다.

## What to look for

### 메서드 선정 휴리스틱 (고정 개수 아님)

이 차원은 **"모든 메서드"를 읽지 않는다.** 아래 기준을 순위로 적용해 읽을 메서드 집합을 **능동적으로 추린다**. 서비스 규모에 따라 10개 일 수도 40개 일 수도 있다.

**Tier 1 — 진입점 (필수 포함)**

- Controller 가 직접 호출하는 public Service 메서드 (각 Controller의 top-level 액션)
- `@Transactional` 이 붙은 public 메서드 (쓰기 경계 = 유스케이스 시작)

**Tier 2 — 도메인 핵심 (선택적 포함, 복잡도 기준)**

- 이름이 다음 접미사를 포함하는 클래스들의 public 메서드:
  - `*Calculator` / `*FeeCalculator` / `*AmountService` — 값 계산
  - `*Validator` — 사전 조건 검증
  - `*Policy` / `*PolicyService` / `*PolicyResolver` — 규칙 적용
  - `*Provider` / `*Strategy` / `*Factory` — 전략 선택 분기
  - `*StateMachine` / `*StatusService` — 상태 전이
- 순환복잡도(if/when/else 분기 수) 가 높은 메서드
- private helper 중 **공식을 담고 있는 것** (금액 · 날짜 계산)

**Tier 3 — 추가 지정 (사용자 확장)**

- 사용자가 orchestrator 호출 시 `extra_methods: [FullyQualifiedName#method, ...]` 로 지정한 메서드
- 또는 재실행 시 이전 출력의 "분석 후보" 리스트에서 승격된 메서드

**Default 선정 기준**: Tier 1 전수 + Tier 2 중 "서비스당 최대 20개 내외에서 도메인 핵심을 대표하는 메서드". **임의의 상한이 아니라 각 메서드가 다른 규칙을 드러내는 한 계속 포함**한다. 같은 패턴 반복이면 하나만 선택하고 "동류: N개 유사 메서드 존재" 로 표기.

### 각 선정 메서드에서 추출할 항목

1. **입력 계약** — parameter 의미, 기본값, nullable 허용 여부
2. **전조건(Preconditions)** — 메서드 진입 시 가정하는 상태
3. **검증 체인** — validate/check 호출 순서 + 실패 시 예외 · 에러 코드
4. **분기 조건** — if/when/else 각각의 비즈니스 의미 (왜 이 경로)
5. **계산/합성 공식** — 산술 · 할인 · 분담 · 집계 수식. 코드를 의사코드로 정규화
6. **상태 전이** — entity.status 변경 (from → to)
7. **부수 효과** — DB 쓰기 · 이벤트 발행 · 외부 호출 · 알림 (이미 다른 차원에 있으면 참조만)
8. **WHY 근거** — KDoc · 주석의 Jira/Wiki 링크 · 매직 넘버에 대한 주석 (과거 장애/정책 흔적)
9. **누락 증상** — 주석 · 링크 없는 매직 넘버 · "TODO" 등 문서화 공백

### 패턴 분류 (출력 시 레이블로 사용)

| 레이블 | 전형적 시그니처 | 예 |
|---|---|---|
| `calculation` | 입력 → BigDecimal/Long/Duration | `calculateReturnPickupFee(...)` |
| `validation` | 입력 → Unit + throw | `validatePaymentCancel(...)` |
| `policy` | 입력 → 제약 플래그 묶음 VO | `getReasonPolicy(...) → FrontClaimReasonPolicy` |
| `strategy-select` | 입력 → 실행 전략 인스턴스 | `provider.getService(claim) → DkpgExecuteService` |
| `composition` | 여러 entity/dto → 상위 VO | `validatePaymentCancel → Triple<Info, Cart, Payment>` |
| `state-transition` | entity + event → entity.status' | `ClaimStatus MCS1 → MCS2` |
| `orchestration` | 하위 단계들을 순차 호출 | `register(...)` / `approve(...)` |

## Output section template

```markdown
## 비즈니스 로직 (도메인 규칙)

### 스캔 범위 요약

- Tier 1 진입점: **N개** 선정 (Controller 연결 액션 + @Transactional 경계)
- Tier 2 도메인 핵심: **M개** 선정 (Calculator · Validator · Policy · Provider 등)
- 제외(유사 패턴 반복): **K개** (요약만)
- 사용자 지정 추가: **J개** (extra_methods 파라미터)

> **재적용 방법**: 이 섹션 하단 "분석 후보" 에서 특정 메서드를 승격하려면 orchestrator 재실행 시 `extra_methods: [...]` 로 명시.

### 메서드 카드

각 메서드 1개당 아래 템플릿 1블록:

---

#### `FullyQualifiedClassName#methodName` — `<pattern-label>`

- **입력**: `param1: Type (의미)`, `param2: Type? = default (의미)`
- **전조건**: ...
- **검증 체인**:
  1. `guardA(...)` — 실패 시 `BadRequestException(errorCode=...)`
  2. `guardB(...)` — ...
- **분기**:
  - `if (...)` → 의미: "...". 이유: (주석 · Jira 링크 · 가설).
  - `else if (...)` → ...
- **공식 (의사코드)**:
  ```
  result = ...
  ```
- **상태 전이**: `ClaimStatus.MCS1 → MCS2`, `ClaimPaymentStatus unchanged`
- **부수 효과**: → `ClaimDB#claim_info.write`, → `[[payment-service]].PaymentHandler.cancel` (→ transactions.md 참조)
- **WHY 근거**:
  - KDoc: "구매자 귀책 반품일 경우 출고배송비를 부과한다"
  - 링크: `https://jira.daumkakao.com/browse/MSMITH-19364`
- **누락 증상**: 매직 넘버 `5` (대기 일수?) 주석 없음
- **위치**: `ClaimFeeCalculator.kt:48-57`

---

### 도메인 상수/enum 요약

비즈니스 규칙의 "백서" 역할을 하는 상수 집합:

| 상수 | 값 | 의미 | 위치 |
|---|---|---|---|
| `REFUNDABLE_CLAIM_STATUS` | `{MCS2, MCS3}` | 결제 취소 가능한 클레임 상태 | `ClaimValidator.kt:359` |
| `DK_COIN_REFUNDABLE` | `{CPM7, CPM8}` | 적립금 환불 가능 상태 | `ClaimValidator.kt:360` |
| ... | | | |

### 규칙 교차 매트릭스 (선택)

여러 메서드가 참조하는 **공통 규칙**을 한 번 더 요약:

| 규칙 | 참조하는 메서드들 | 규칙의 근거 |
|---|---|---|
| "반품 철회는 역순으로만" | `validateRejectClaim`, ... | Agit 기획서 링크 |
| "무료배송 상품은 구매자 귀책 시 배송비 부과" | `getExtraClaimFee`, ... | KDoc |

### 분석 후보 (미적용 / 동적 확장용)

다음 재분석 시 **승격 가능한** 메서드 목록. 선정 제외 이유 명시:

- `ClassA#methodX` — Tier 2 이지만 유사 패턴이 `methodY` 에 이미 포함됨
- `ClassB#methodZ` — 복잡도 낮음 (단순 조회)
- `ClassC#methodW` — 의존 외부 인터페이스가 크고 본 분석 범위 밖
- ...

재실행 명령 예:

```
extra_methods: ["ClassA#methodX", "ClassC#methodW"]
```
```

## Forensic prompts

- 매직 넘버 · 하드코딩된 한계값(예: 5일, 30%)에 **주석이 없다면** → 과거 장애 패치의 흔적일 가능성. 팀 위키 확인 후보.
- 같은 계산이 **두 Calculator 에 분기되어 구현**되어 있다면 왜? (리팩터 미완 / 의도된 분화)
- Validator 의 **함수 순서가 명시되어 있는가**? 순서가 중요한 검증은 주석으로 근거가 남아야 함.
- Policy 가 반환하는 **boolean 플래그 묶음**이 커지고 있다면 → UI 분기 요구가 누적된 결과. 책임 경계 재검토 후보.
- Strategy Provider 의 선택 키가 **enum 1개** vs **복합 조건** 인지 — 후자면 명시적 Strategy 패턴 이탈.
- 주석/KDoc 이 **정책 링크만 걸어두고 내용을 복사하지 않는가**? 링크 rot 위험.
- "철회는 역순", "배송비는 한번만 취소" 같은 **비즈니스 금언**이 코드 여러 곳에 repeat 되는가? DRY 위반 + 규칙 표류 리스크.

## When absent

- Controller 는 있지만 Service 가 거의 비어있음 → **anemic service** (게이트웨이형). 명시하고 구조적 이유 기록.
- Calculator/Validator 가 분리되지 않고 Service 안에 섞여 있음 → "도메인 로직 추상화 미흡". Tier 2 후보를 "해당 Service 의 private helper" 로 확장.
- 도메인 상수/enum 이 빈약 → 규칙이 코드 리터럴로만 존재. **규칙 표류 리스크 높음**으로 기록.

## Extension (동적 확장 계약)

이 차원은 **반복 적용**이 가능해야 한다.

- **재실행 트리거**: 사용자가 orchestrator 재호출 시 프롬프트 상단에 다음 파라미터 추가 가능
  ```
  extra_methods: ["com.foo.Svc#bar", "com.foo.Other#baz"]
  ```
- **누적 원칙**: 기존 카드를 덮어쓰지 않고, 신규 메서드 카드를 추가한 뒤 "분석 후보" 리스트를 갱신.
- **경계 조건**: `extra_methods` 에 이미 분석된 메서드가 포함되어 있으면 **재분석** (코드가 변했을 수 있음) 하되, 출력에 "재분석" 플래그.
- **ingest 쪽 함의**: 메서드 카드가 N개면 ingest 단계에서 M개의 concept 페이지로 분해됨 (`wiki/concepts/<method-or-rule-slug>.md`). 따라서 카드 안의 wikilink 일관성이 다른 어떤 차원보다 중요.

# Dimension: Transactions & Compensation

## Intent

`@Transactional` 경계와 **보상 트랜잭션(Compensating) 패턴**은 이 서비스가
일관성에 대해 어떤 트레이드오프를 했는지를 드러낸다. 특히 외부 호출과 DB 쓰기가 섞인 플로우에서 결정적.

## What to look for

### 트랜잭션 경계

- `@Transactional` — 모든 위치, propagation / isolation / readOnly / timeout / rollbackFor / noRollbackFor
- `TransactionTemplate` 직접 사용
- `TransactionSynchronizationManager.registerSynchronization` / `@TransactionalEventListener(phase = AFTER_COMMIT)` — 커밋 후 hook
- `PlatformTransactionManager` 여러 개 (다중 DataSource일 때)

### 보상 트랜잭션

- 단일 Service 메서드 내: "A 저장 → B 외부 호출 실패 → A 되돌리기" 수동 롤백 코드
- `@Retryable` + `@Recover` 조합 — 재시도 실패 시 fallback
- SAGA 흔적: `*.failed` / `*.canceled` / `*.compensate` 이벤트 발행·소비
- "상태 플래그로 취소/실패 표현" (Entity에 `status = FAILED` 업데이트) — 롤백 대신 forward-fix

## Output section template

```markdown
## 트랜잭션 전략

### 경계 요약

| 플로우 | 진입 메서드 | propagation | isolation | 외부 호출 위치 | 비고 |
|--------|-----------|-------------|-----------|--------------|------|
| 클레임 승인 | `ClaimService.approve` | REQUIRED | DEFAULT | **트랜잭션 안** (롱 트랜잭션 리스크) | afterCommit으로 이벤트 발행 |
| 환불 처리 | `RefundService.process` | REQUIRES_NEW | REPEATABLE_READ | 트랜잭션 밖 | PG 실패 시 상태만 FAILED로 업데이트 |

### 보상 트랜잭션 / SAGA 패턴

| 플로우 | 실패 지점 | 보상 액션 | 멱등성 보장 |
|--------|---------|----------|------------|
| 주문 취소 → 클레임 자동 생성 | [[order-service]] 응답 실패 | 생성된 클레임을 `CANCELED`로 상태 변경 + `claim.canceled` 이벤트 | 클레임 `external_key` unique |
| ... | | | |

### afterCommit / 이벤트 타이밍

- `@TransactionalEventListener(phase = AFTER_COMMIT)` 사용 위치 및 이유
- 커밋 실패 시 이벤트 누락 가능성 — transactional outbox 패턴 채택 여부
```

## Forensic prompts

- `REQUIRES_NEW`를 쓴 이유가 **부모 롤백으로부터 분리**하려는 건가, 아니면 **DataSource 분리** 때문인가?
- `noRollbackFor`가 지정된 예외가 있는가? → "이 예외는 발생해도 괜찮으니 커밋해라"는 **비즈니스 의도** 표시.
- 외부 호출이 트랜잭션 *안*에 있다면 → 왜? (순서 보장? 호출 결과를 DB에 반영해야 함?) 롱 트랜잭션 감수의 이유.
- 보상 액션이 **상태 플래그**인지 **실제 롤백**인지 → 전자는 forward-fix 철학, 후자는 강한 원자성 추구.
- `@TransactionalEventListener` 대신 커밋 안에서 `rabbitTemplate.send` 하는 곳은 없는가? → 있다면 이벤트 누락 리스크 있는 레거시.

## When absent

- `@Transactional` 이 거의 없는 서비스 → 읽기 전용 API/gateway 성격. 명시.
- 보상 트랜잭션 흔적이 없으면 "**보상 트랜잭션 패턴 미발견** — 외부 호출 실패 시 그냥 에러 전파하고 retry 의존" 으로 기록.

# Dimension: Messaging & Idempotency

## Intent

비동기 통신은 **순서 · 중복 · 실패**를 팀이 어떻게 다루는지 가장 직설적으로 보여준다.
서비스 간 궁극적 일관성(eventual consistency)의 실체.

## What to look for

### Producer (발행)

- `RabbitTemplate.convertAndSend` / `KafkaTemplate.send`
- `ApplicationEventPublisher.publishEvent` (Spring 이벤트 — 내부용)
- `@TransactionalEventListener(phase = AFTER_COMMIT)` — 커밋 후 발행
- outbox pattern 흔적 (별도 테이블에 이벤트 저장 후 scheduler가 발행)

### Consumer (소비)

- `@RabbitListener` / `@KafkaListener` / `@RabbitHandler`
- acknowledge mode (`MANUAL` / `AUTO`)
- concurrency 설정 (`concurrency = "5-10"`)
- DLQ / retry exchange 설정

### 멱등성 보장

- unique constraint 기반 (`claim_event_idempotency_t` 같은 테이블)
- Redis SETNX / `RedissonClient.getBucket().trySet(value, ttl)`
- 상태 체크 (`if (claim.status == APPROVED) return` — 이미 처리된 메시지 스킵)

## Output section template

```markdown
## 메시징 / 이벤트

### Producer

| 채널 | 메시지 타입 | 발행 시점 | 트랜잭션 동기화 | 발행 위치 |
|------|-----------|----------|---------------|----------|
| [[claim.ex]] `claim.approved` | `ClaimApprovedEvent` | 승인 커밋 후 | AFTER_COMMIT | `ClaimEventPublisher.publishApproved` |
| [[order.q]] `order.refund.request` | `RefundRequestEvent` | 환불 처리 커밋 후 | AFTER_COMMIT | `RefundEventPublisher` |

### Consumer

| 채널 | 핸들러 | ack | concurrency | DLQ | 멱등성 |
|------|-------|-----|-------------|-----|-------|
| [[order.canceled.q]] | `OrderCanceledListener.handle` | MANUAL | 5-10 | [[order.canceled.dlq]] | `event_idempotency_t` unique 체크 |

### 멱등성 전략

- `event_idempotency_t(event_id UNIQUE)` 테이블로 이미 처리된 이벤트 감지
- Redis `SETNX claim:event:{eventId}` TTL 7d
```

## Forensic prompts

- **`AFTER_COMMIT`인가 트랜잭션 내 발행인가?** 후자면 이벤트 누락 없음 vs 롤백된 상태도 발행될 위험 — 팀이 어느 쪽을 택했는지.
- DLQ는 있는가? DLQ 소비자는 누가? 사람인가 자동 재처리인가?
- concurrency 값이 대상별로 크게 다르다면 → 처리 비용/순서 요구사항 차이.
- 멱등성 키로 **event_id**를 쓰는가 **비즈니스 키**(claimId)를 쓰는가? 전자는 재발행도 막고, 후자는 같은 비즈니스 이벤트 여러 번 안전.
- Kafka offset commit 전략 (at-least-once / at-most-once / exactly-once) 흔적.
- Spring 내부 이벤트(`ApplicationEventPublisher`)와 RabbitMQ/Kafka를 섞어 쓰는가? 내부 이벤트는 프로세스 경계 안에서만 보장됨 — 크래시 내성 없음.

## When absent

- 메시징 완전 미사용이면 "**동기 호출 only** — 모든 서비스 간 통신이 HTTP 동기" 명시.

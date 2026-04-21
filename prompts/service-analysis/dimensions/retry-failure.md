# Dimension: Retry & Failure Handling

## Intent

무엇이 **재시도 가능**하고 무엇이 **사람에게 알려지는가** — 팀의 운영 성숙도와 외부 시스템 신뢰도를 드러낸다.

## What to look for

- `@Retryable(maxAttempts, backoff)` + `@Recover` (Spring Retry)
- `RetryTemplate` 커스텀 설정
- Resilience4j: `@Retry(name = "...")`, `@CircuitBreaker`, `@Bulkhead`, `@RateLimiter`
- `try/catch` + `Thread.sleep` + 반복 — 조잡한 수동 재시도 (위험 시그널)
- 실패 알림 경로:
  - kakaowork sender (`com.makers.core.notification.sender.kakaowork`)
  - Slack webhook
  - Sentry (`io.sentry` — 이 서비스 build.gradle에 확인됨)
  - 내부 알림 서비스 API 호출

## Output section template

```markdown
## 재시도 / 실패 처리

### 재시도 전략

| 대상 | 메커니즘 | 설정 | 실패 시 동작 |
|------|---------|------|------------|
| [[payment-service]] 호출 | `@Retryable(3, backoff=fixed 2s)` | maxAttempts=3 | `@Recover` → 상태 `FAILED` 업데이트 + kakaowork |
| [[rabbitmq]] publish | Spring Retry | backoff=exp 1s/2s/4s | DLQ 전송 |
| DB deadlock | `@Retryable(on=DeadlockException, 5회)` | - | 5회 실패 시 예외 전파 |

### 실패 알림

| 트리거 | 채널 | 내용 |
|--------|------|------|
| PG 호출 3회 실패 | kakaowork `#claim-alert` | 클레임 ID, 실패 사유, 재시도 횟수 |
| 배치 작업 실패 | Sentry + kakaowork | stack trace |

### Circuit Breaker

| 대상 | 설정 | 차단 조건 | 복구 |
|------|------|---------|------|
| [[payment-service]] | slidingWindow=10, failureRate=50% | 5/10 실패 시 OPEN | 30s 후 HALF_OPEN |
```

## Forensic prompts

- **재시도 가능성은 idempotency의 역함수.** 재시도하는 대상은 반드시 멱등해야 함 — 팀이 그걸 확신하는 근거가 코드에 있는가?
- `@Recover`의 fallback이 **상태 변경**인가 **단순 로깅**인가? 전자가 더 성숙.
- 실패 알림 **임계값** (n회 실패 후 알림) — 너무 낮으면 알림 피로, 너무 높으면 장애 감지 지연.
- Circuit Breaker가 있는 대상과 없는 대상의 차이 — 왜? (호출 빈도? 장애 시 downstream 영향도?)
- Sentry에 기록되는 수준 (ERROR만? WARN도?) 과 알림 채널의 관계.

## When absent

- 재시도 로직이 전혀 없으면 "**실패 시 즉시 에러 전파** — 재시도는 호출자(클라이언트) 책임" 으로 명시.

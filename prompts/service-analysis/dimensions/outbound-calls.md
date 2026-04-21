# Dimension: Outbound Calls (외부 서비스 호출)

## Intent

**이 서비스가 누구를 부르는가** — 크로스 서비스 그래프의 핵심 연결선. wikilink로 정확히 기록하면 Obsidian Graph가 팀 마이크로서비스 맵이 된다.

## What to look for

- `@FeignClient(name = "...")` — 대상 서비스명이 힌트
- `RestTemplate` bean 주입 · `restTemplate.exchange(...)` 호출 위치
- `WebClient` (reactive) — non-blocking 호출
- Retrofit — `@GET`, `@POST` 어노테이션된 interface
- `HttpClient` / OkHttp 직접 사용 (흔하진 않지만 있을 수 있음)
- `application.yml` 의 URL 설정 (`xxx.base-url: ...`)
- Resilience4j / Hystrix / `@CircuitBreaker` / `@Retry` 어노테이션
- `@Retryable` (Spring Retry)
- timeout 설정 — `RequestConfig`, `WebClient.builder().timeout(...)`

## Output section template

```markdown
## 외부 서비스 의존성 (Outbound)

### HTTP 호출

| 대상 | Client 유형 | 호출 경로 | 호출 위치 (클래스) | 사용 맥락 | Circuit Breaker / Retry | Timeout |
|------|-----------|----------|-------------------|---------|------------------------|--------|
| [[order-service]] | FeignClient | `GET /orders/{id}` | `OrderClient` | 클레임 생성 시 원본 주문 조회 | `@Retryable(3회)` | connect 1s / read 3s |
| [[payment-service]] | WebClient | `POST /payments/{id}/refund` | `PaymentClient` | 승인된 클레임의 환불 | Resilience4j CB | 5s |
| [[user-service]] | RestTemplate | `GET /users/{id}` | `UserClient` | 신청자 정보 | 없음 | default |

### 호출 맥락 간 연관

- [[order-service]] 호출이 실패하면 → [[payment-service]] 호출은 아예 시도하지 않음 (guard clause)
```

## Forensic prompts

- **왜 어떤 대상은 재시도하고 어떤 대상은 재시도하지 않는가?**
  - 재시도 OK인 대상: idempotent (GET, 또는 unique key 기반 POST)
  - 재시도 안 함: idempotency 보장 불가 → 중복 호출 시 부작용
- Circuit Breaker가 있는 호출과 없는 호출의 차이 — 왜?
- Timeout 값이 대상별로 크게 다른가? → 대상 서비스의 SLA / 호출 성격(조회 vs 외부 시스템 연동)
- FeignClient / WebClient / RestTemplate 혼용 — 마이그레이션 중? 아니면 팀 컨벤션 부재?
- `@LoadBalanced` 여부 — service discovery 쓰는가, 고정 URL인가?

## When absent

- 외부 호출이 전혀 없으면 "**완전 독립 서비스** — DB/메시지만 의존" 명시. (드물지만 가능)

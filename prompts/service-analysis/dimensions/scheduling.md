# Dimension: Scheduling & Batch

## Intent

배치 작업은 "온라인 처리로는 감당 못 하는 것"의 목록 = **비즈니스의 시간 축** 이 드러남.
또한 분산 환경에서 1개 인스턴스만 실행하려는 장치를 같이 본다.

## What to look for

- `@Scheduled` — cron / fixedRate / fixedDelay
- Spring Batch — `@EnableBatchProcessing`, `Job`, `Step`, `ItemReader/Processor/Writer`
- Quartz — `JobDetail`, `Trigger`
- **분산 실행 제어**:
  - ShedLock (`@SchedulerLock`)
  - Redisson lock wrapping
  - 앱 인스턴스 지정 (`@ConditionalOnProperty`, leader election)
- `@Async` + `TaskScheduler` 커스텀

## Output section template

```markdown
## 배치 / 스케줄

| 작업 | 주기 / 트리거 | 하는 일 | 분산 실행 제어 | 처리 규모 |
|------|-------------|--------|--------------|----------|
| `ClaimTimeoutJob.run` | cron `0 0 * * * *` | 7일 경과 PENDING 클레임 자동 반려 | `@SchedulerLock(lockAtLeastFor="5m")` | ~500건/시간 |
| `RefundReconcileJob.run` | 매일 03:00 | PG 일일 정산 대조 | Redisson lock `batch:refund-reconcile` | 전체 스캔 |
| `DLQReprocessJob` | fixedDelay 10분 | DLQ 적체 메시지 재처리 시도 | ShedLock | ~N 건 |
```

## Forensic prompts

- 분산락이 **없는** `@Scheduled` 는 왜 안전한가? (인스턴스 1개만 뜨는 환경? 멱등성 보장?)
- cron 표현식이 `0 0 * * * *` 처럼 정각 시작인가, `0 13 * * * *` 처럼 분산되어 있나? → 정각 일제히 돌면 DB 부하 스파이크.
- `lockAtLeastFor` 값이 큰 이유는? (재실행 방지 안전마진) `lockAtMostFor` 값이 작으면 정상 오래 걸리는 작업이 중단.
- Spring Batch 대신 직접 짠 `@Scheduled`가 있다면 왜? (의존성 최소화? chunk 처리 불필요?)
- 실패 알림 경로 — 배치 실패가 사람에게 알려지는가?

## When absent

- 배치/스케줄이 없으면 "**스케줄 작업 없음** — 모든 처리가 요청 또는 이벤트 응답" 명시.

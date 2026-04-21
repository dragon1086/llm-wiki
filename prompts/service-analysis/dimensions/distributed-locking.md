# Dimension: Distributed Locking (Redisson 중심)

## Intent

분산락은 **"DB 트랜잭션만으로는 안 되는 이유가 있다"**는 신호.
Lock key 설계 · waitTime · leaseTime · FairLock 선택 여부는 모두 **과거 장애 혹은 비즈니스 제약**을 반영한다.

## What to look for

### Redisson API 호출 전수

- `RedissonClient.getLock(key)` — ReentrantLock
- `RedissonClient.getFairLock(key)` — FIFO 보장
- `RedissonClient.getReadWriteLock(key).readLock() / .writeLock()`
- `RedissonClient.getSemaphore(key)` — 동시성 상한
- `RedissonClient.getPermitExpirableSemaphore(key)`
- `RedissonClient.getSpinLock(key)` (드묾)

### 커스텀 어노테이션

- `@DistributedLock(key = "...")` 같은 커스텀 어노테이션 + AOP Aspect
- SpEL 로 key 동적 바인딩 (`#claimId`)

### DB 레벨 락

- `@Lock(LockModeType.PESSIMISTIC_WRITE)` on Repository 메서드
- `SELECT ... FOR UPDATE` 네이티브 쿼리
- JPA Optimistic Lock (`@Version`)

## Output section template

```markdown
## 분산락 / 동시성 제어

### Redisson Lock 전수

| Lock 종류 | Key 패턴 | 사용처 | waitTime | leaseTime | 선택 이유 (가설 포함) |
|----------|---------|--------|----------|-----------|---------------------|
| FairLock | `claim:approval:{claimId}` | `ClaimService.approve` | 3s | 10s | 승인 순서가 정산 계산에 영향 → **FIFO 공정성 필요** |
| RLock | `claim:refund:{claimId}` | `RefundService.process` | 5s | 30s | PG 중복 호출 방지, 순서는 무관 |
| Semaphore(5) | `external-api:pg` | `PaymentClient.call` | 2s | - | PG rate limit 내 동시 호출 상한 |
| ReadWriteLock | `claim:settings` | `SettingsService` | 1s | 5s | 읽기는 다수 허용, 쓰기만 직렬화 |

### 커스텀 `@DistributedLock`

- `@DistributedLock(key = "'claim:' + #claimId", waitTime = 3, leaseTime = 10, fair = true)`
- Aspect: `DistributedLockAspect.kt`
- 사용처 N개 (위 표에 포함됨)

### DB 락 병용

| 위치 | DB 락 | 분산락 중복 | 의도 추론 |
|------|-------|-----------|----------|
| `ClaimRepository.findByIdForUpdate` | PESSIMISTIC_WRITE | YES (FairLock 안에서) | **이중 방어**: 분산락 leaseTime 조기 만료 시 DB가 최후 방어선 |
```

## Forensic prompts

- **왜 FairLock?** 일반 RLock보다 내부적으로 무거운데 굳이 택했다면 **순서 보장이 비즈니스 규칙**. 어디에 쓰는가?
- waitTime / leaseTime 값의 **근거가 코드/주석에 있는가**? 없으면 **과거 장애에서 학습된 값일 가능성** — Jira/팀 문서/장애 리포트 확인 후보.
- Lock key가 **entity 단위**(`claim:{id}`)인가 **전역**(`claim:approval`)인가? 후자면 동시 처리량이 심각하게 제한됨 — 의도적인가?
- Lock 안에서 외부 호출을 하는가? → leaseTime 초과 시 락 조기 해제로 race 가능.
- `@DistributedLock` 커스텀 Aspect의 exception 처리 — lock 획득 실패 시 어떤 예외가 사용자에게 전파되는가?
- Lock 획득/해제 로그가 남는가? 프로덕션에서 lock 경합 관찰 가능한가?

## When absent

- Redisson 의존성 자체가 없으면 "**분산락 미사용** — 단일 인스턴스 또는 JPA 낙관적 락만 사용" 으로 명시.
- 있는데 1~2곳만 쓴다면 해당 위치를 특별히 강조.

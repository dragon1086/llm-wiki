# Profile: default

모든 마이크로서비스에 공통 적용되는 기본 차원 세트. 순서대로 적용.

## 포함 차원 (순서대로)

1. `dimensions/identity.md`
2. `dimensions/data-ownership.md`
3. `dimensions/api-inbound.md`
4. `dimensions/transactions.md`
5. `dimensions/outbound-calls.md`
6. `dimensions/messaging.md`
7. `dimensions/scheduling.md`
8. `dimensions/distributed-locking.md`
9. `dimensions/retry-failure.md`
10. `dimensions/infra.md`
11. `dimensions/domain-logic.md`  ← Service 메서드 본문 기반 비즈니스 규칙
12. `dimensions/forensics.md`  ← 항상 마지막

## 출력 섹션 순서 (최종 markdown 내부)

각 차원의 "Output section template" 을 위 순서로 배치.
단, **❓ 설계 의문점 / 포렌식** 섹션은 개별 차원의 forensic prompts와 `forensics.md` 의 종합 가설이 **통합**되어 하나의 섹션으로 등장.

## 프로파일 커스터마이징

다른 프로파일이 필요하면 이 파일을 복제·수정:

- `crud-minimal.md` — `distributed-locking.md` / `messaging.md` / `scheduling.md` 제외
- `event-heavy.md` — `messaging.md` 우선순위 올리고 forensic prompts 강화
- `gateway.md` — `outbound-calls.md` / `retry-failure.md` 강화, `data-ownership.md` 간소화

## 향후 자동 프로파일링

`orchestrator.md` 가 `build.gradle.kts` 의존성을 보고 자동 선택하도록 확장 가능:

- `spring-boot-starter-amqp` 또는 `kafka-clients` 있음 → event-heavy 후보
- Redisson 의존성 있음 → distributed-locking 필수
- 엔티티 없음 / `spring-data-jpa` 없음 → gateway 후보

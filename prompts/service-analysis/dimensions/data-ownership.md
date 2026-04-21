# Dimension: Data Ownership (다중 DataSource + JPA 매핑)

## Intent

"이 서비스가 **소유한** 데이터는 무엇이고, 남의 DB를 **읽고 있는** 데이터는 무엇인가"를 명확히 한다.
이건 단순 인프라가 아니라 **팀 간 책임 경계**를 드러내는 가장 강력한 단서다.

## What to look for

- `@Configuration` + `@EnableJpaRepositories(basePackages, entityManagerFactoryRef, transactionManagerRef)` — 다중 DataSource 표지
- `@Primary` DataSource는 무엇인지
- 각 `@Entity`가 속한 패키지 → 어느 `basePackages`에 포함되는지로 DataSource 판별
- `application.yml` 의 `spring.datasource.*` / 커스텀 DataSource bean
- Read-only 힌트: `@Transactional(readOnly = true)`, Repository 이름에 `ReadOnly`/`Query` suffix
- `@Table(schema = "...")` 명시

## Output section template

```markdown
## 도메인 모델 & 데이터 소유권

### DataSource 구성

| DataSource Bean | DB 스키마 | 소유권 | 용도 | 근거 |
|-----------------|----------|--------|------|------|
| `claimDataSource` (Primary) | [[claim_db]] | own (write) | 주 도메인 | `ClaimDataSourceConfig.kt` |
| `orderDataSource` | [[order_db]] | read-only | 조회 최적화 | `OrderDataSourceConfig.kt` |

### 엔티티 ↔ DataSource 매핑

| 엔티티 | DB 테이블 | DataSource | R/W | 비고 |
|--------|----------|-----------|-----|------|
| `ClaimEntity` | [[claim_t]] | claim | R/W | 주 집계 루트 |
| `OrderReadEntity` | [[order_t]] | order | R only | write 주체는 [[order-service]] |

### 핵심 불변식 / 규칙

- <도메인 규칙>
```

## Forensic prompts

- 왜 API 호출 대신 **남의 DB를 직접** 읽는가? (N+1 회피 / 성능 / 과거 SLA 문제 / 정합성)
- 여러 DataSource를 하나의 `@Transactional`로 묶는 플로우가 있는가? → 있다면 XA인가, 아니면 사실상 분산 트랜잭션을 **포기**한 것인가?
- Primary DataSource 지정 방식 — 실수로 다른 DB에 쓸 위험은 없는가?
- Read-only로 시작했다가 write까지 허용한 흔적은 없는가? (git log로 추적할 만한 후보)

## When absent

- 단일 DataSource면 표를 한 줄로 단순화하고 "단일 DataSource — 데이터 경계 이슈 없음"으로 명시.
- 다중 DataSource 흔적이 전혀 없으면 "**다중 DataSource 미사용**" 명시.

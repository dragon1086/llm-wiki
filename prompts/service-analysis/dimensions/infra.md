# Dimension: Infrastructure Dependencies

## Intent

서비스가 **의존하는 모든 외부 시스템**을 빠뜨리지 않고 목록화. 장애 대응 시 체크리스트.

## What to look for

- `application.yml` / `application-*.yml` — 외부 연결 설정
- `build.gradle.kts` 의존성 목록
- Config 클래스 (`@Configuration` + bean 생성)
- 환경 변수 / Spring Cloud Config 참조

체크할 것:

- RDBMS (MySQL / PostgreSQL / Oracle) + 스키마 분리
- Redis (캐시 · 분산락 · 세션)
- 메시지 브로커 (RabbitMQ / Kafka)
- 오브젝트 스토리지 (S3 / GCS)
- 검색 엔진 (Elasticsearch / OpenSearch)
- 외부 SaaS (SendGrid, Sentry, Datadog)
- Config 서버 (Spring Cloud Config)
- Service Discovery (Eureka / Consul)

## Output section template

```markdown
## 인프라 의존성

### 데이터 저장소

| 시스템 | 역할 | 설정 |
|--------|------|------|
| MySQL (claim_db) | **소유 DB** — 주 도메인 | `spring.datasource.claim.url` |
| MySQL (order_db) | 참조 read-only | `spring.datasource.order.url` |
| Redis | 캐시 + **Redisson 분산락** + 세션 | sentinel 3노드 |

### 메시징

| 시스템 | 역할 | Exchange / Topic |
|--------|------|-----------------|
| RabbitMQ | 이벤트 버스 | `claim.ex`, `order.q` |

### 기타

| 시스템 | 역할 | 비고 |
|--------|------|------|
| S3 | 첨부파일 저장 | 버킷: `claim-attachments` |
| Sentry | 에러 추적 | dsn via env |
| Spring Cloud Config | 환경별 설정 외부화 | - |
| kakaowork | 실패/경고 알림 | webhook |
```

## Forensic prompts

- Redis를 **캐시**로만 쓰는가, 아니면 **분산락 / Pub-Sub / 세션** 도 섞여 있는가? — 역할 다중화는 장애 영향 확대.
- MySQL 다중 DB 중 일부가 **같은 서버**인가 **다른 서버**인가? 같은 서버면 장애 동시 영향.
- S3 외에 로컬 파일시스템 쓰는 흔적 (`File`, `Paths.get`) 은 없는가? → 멀티 인스턴스 환경에서 데이터 유실 리스크.
- Sentry / Datadog 태그 정책 (`service`, `env`, `version`) 이 설정돼 있는가? — 관찰성 성숙도.

## When absent

- 특정 계열 인프라가 없으면 명시 (예: "Kafka 미사용, RabbitMQ만").

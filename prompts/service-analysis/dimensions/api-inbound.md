# Dimension: API Inbound

## Intent

외부(다른 서비스, 프론트엔드, 어드민)가 이 서비스를 **어떻게 부르는지** 그림. 인증 경계와 같이 봐야 함.

## What to look for

- `@RestController` / `@Controller` / `@RequestMapping`
- 메서드 레벨 `@GetMapping` / `@PostMapping` 등
- `@PreAuthorize` / `@Secured` / `@RolesAllowed` — 메서드 단위 인가
- `SecurityConfig` 여러 개 (admin/internal/user/partner) — 체인 분리
- `@Validated`, `@Valid` — 입력 검증 경계
- `@RequestHeader` — 내부 호출 판별용 헤더(예: `X-Internal-Token`)
- `@ControllerAdvice` — 에러 응답 매핑

## Output section template

```markdown
## API 엔드포인트 (Inbound)

### 보안 체인 개요

| 체인 | URL 패턴 | 인증 방식 | 주 사용자 |
|------|----------|----------|----------|
| adminSecurityFilterChain | `/admin/**` | Admin JWT | 백오피스 |
| internalSecurityFilterChain | `/internal/**` | X-Internal-Token | 다른 서비스 |
| userSecurityFilterChain | `/api/**` | 카카오 OAuth | 최종 사용자 |

### 엔드포인트

| Method | Path | 체인 | 요약 | 주요 호출 체인 |
|--------|------|------|------|---------------|
| POST | `/api/v1/claims` | user | 클레임 생성 | `ClaimController.create` → `ClaimService.create` → `ClaimRepository.save` |
| ... | | | | |
```

## Forensic prompts

- 동일 리소스(`claims`)에 user/admin/internal 3개 컨트롤러가 있는가? → **있다면 권한별로 비즈니스 로직이 조금씩 다를 것**. 차이를 요약할 가치 있음.
- SecurityConfig가 여러 개인데 URL 충돌 가능성은? → 잘못 매칭되면 보안 사고.
- Swagger/OpenAPI 노출 경로 — `/admin/swagger` 가 외부 노출되고 있지 않은가?

## When absent

- 내부 서비스여서 Controller 없고 Consumer만 있다면 → "Inbound HTTP 없음. 메시지 소비로만 호출됨 (messaging 차원 참조)" 로 기록.

# Dimension: Identity

## Intent

서비스의 배치를 조직/팀/도메인 수준에서 한눈에 잡는다. 이후 모든 분석의 맥락.

## What to look for

- `build.gradle.kts` / `pom.xml` — group, artifact, Spring Boot 버전, Kotlin/Java 버전
- 루트 패키지 (`com.makers.claim` 등)
- README, CODEOWNERS, `.gitlab-ci.yml` / `.github/workflows/` — 팀·배포 경로
- `application.yml` 의 `spring.application.name`
- git remote URL

## Output section template

```markdown
## 서비스 정체성

- **정의**: <1줄>
- **팀 / 소유**: <팀명 또는 CODEOWNERS>
- **루트 패키지**: <com.xxx.yyy>
- **Spring Boot**: <x.y.z>  · **언어**: Kotlin <ver> / Java <ver>
- **배포**: <Kubernetes / ECS / 기타 — 추론 가능한 범위>
- **repo**: <git remote>
```

## Forensic prompts

- 서비스 이름 suffix가 `-service` / `-api` / `-core` 섞여 있는가? → 팀의 네이밍 규칙 추측
- Spring Boot 버전이 상대적으로 낮은가? → 유지보수 중이라 업그레이드 보류?

## When absent

기본 정보는 대부분 있다. 찾을 수 없는 항목은 "(미확인)" 으로 기록.

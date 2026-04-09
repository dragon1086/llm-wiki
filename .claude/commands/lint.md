---
description: wiki 정합성 검사 (dead links, orphans, 모순, stale claims)
argument-hint: "[--fix] [--deep]"
allowed-tools:
  - Bash
---

# /lint

```bash
./wiki lint $ARGUMENTS
```

결과 이슈를 유형별로 표로 정리하여 안내합니다.

## 플래그

- `--fix`: orphan 자동 수정, index.md 갱신
- `--deep`: LLM으로 모순 탐지 (느림, 토큰 추가 소모)

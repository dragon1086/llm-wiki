---
description: raw/ 소스 파일을 wiki로 ingest합니다.
argument-hint: "[파일경로 | --all]"
allowed-tools:
  - Bash
---

# /ingest

```bash
cd /Users/aerok/Desktop/rocky/llm-wiki
./wiki ingest $ARGUMENTS
```

완료 후 생성/갱신된 페이지 수를 안내합니다.

## 예시

```
/ingest                          # 미처리 파일 전체 (--all 자동)
/ingest raw/article.md           # 단일 파일
/ingest --all                    # 명시적 전체
```

인수 없이 호출하면 `--all`로 동작합니다.

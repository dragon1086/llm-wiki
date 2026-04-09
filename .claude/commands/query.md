---
description: wiki를 탐색하여 질문에 답합니다.
argument-hint: "<질문> [--slides|--diagram|--chart|--archive]"
allowed-tools:
  - Bash
---

# /query

```bash
cd /Users/aerok/Desktop/rocky/llm-wiki
./wiki query "$ARGUMENTS"
```

출력 파일 경로를 확인하고 사용자에게 결과를 안내합니다.

## 옵션

| 플래그 | 설명 |
|--------|------|
| `--slides` | Marp 슬라이드 생성 |
| `--diagram` | Mermaid 다이어그램 생성 |
| `--chart` | matplotlib PNG 생성 |
| `--archive` | output/ → raw/ 복사 후 wiki에 자동 ingest |

## 예시

```
/query 트랜스포머 어텐션이 왜 O(n²)인가?
/query 이 개념들 비교해줘 --slides
/query 설계도 그려줘 --diagram --archive
```

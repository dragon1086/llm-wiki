# Code Review Graph — 유즈케이스 탐색 저널

> 목적: CRG를 claim2-service + order-service에서 실사용해보고, 팀 발표용 유즈케이스로 정리할 때까지의 **실험 기록**.
> 도구 자체 설명 · 설치 · 운영 팁은 [code-review-graph-guide.md](./code-review-graph-guide.md) 참조.
> 팀 발표용 최종 정리는 맨 아래 **"팀 발표 초안"** 섹션에 누적. 본문은 날것의 실험 로그.

---

## 0. TL;DR (현재 상태)

- **브랜치**: `feature/microservice-analysis` (llm-wiki)
- **테스트 대상**: claim2-service(Kotlin) + order-service(Java), 둘 다 `register` 완료
- **완료**: 격리 설치 → 양 레포 `build` → MCP stdio 직접 handshake → `cross_repo_search_tool` 실측 → claim2-service에 선택적 install → `.mcp.json`에 `--repo` 절대경로 고정
- **🎯 핵심 발견**: `Claim` 쿼리에서 order-service의 `ClaimHandler.java` 드러남 → **서비스 간 호출 관계가 심볼 이름으로 자동 노출** (Graphify로는 불가)
- **⚠️ 한계**: `@KafkaListener`·`RestTemplate` 같은 프레임워크 심볼은 인덱스에 없음 / score 랭킹 품질 낮음 (모두 0.016)
- **다음**: (1) Claude Code 재시작 후 claim2-service에서 MCP 실사용, (2) 임베딩 빌드로 semantic search 개선, (3) order-service도 동일 install
- **스킵 결정**: `eval` 벤치마크는 저자 fixture 전용이라 claim2/order엔 무의미

---

## 1. 배경

- 마이크로서비스 정적 분석 워크플로우는 이미 **Graphify + `prompts/service-analysis`** 조합으로 돌아감 ([handoff.md](./handoff.md) 참조)
- handoff.md 라인 24에 "Graphify + code-review-graph 중 Graphify 선택"이라는 과거 결정 있음 — 이번에 CRG를 재평가하는 이유:
  - 토큰 최적화 리포 리스트(사용자 공유)에서 "49x 토큰 감소" 주장을 본 뒤 실효성 검증 필요
  - Graphify는 **분석 단계에서 한 번 구조 추출** → 이후 Claude 세션은 여전히 파일을 많이 읽음
  - CRG는 **리뷰 단계에서 컨텍스트를 축소**하는 다른 층위의 도구 → 상호 보완 가능성
- 현재 이해: 본질 목적은 **"CRG의 최적 사용법 + 진짜 유용성 발견"** (Graphify 대체 여부가 아님)

---

## 2. 실행 로그 (시간순)

### 2026-04-21

#### 2.1 claim2-service 인덱스 첫 빌드

```bash
cd /Users/kakao/workspace/claim2-service
code-review-graph build
```

| 지표 | 값 |
|---|---|
| 소요 시간 | < 10초 |
| 파싱 파일 | 950 (src/ Kotlin 951개 중 1개 제외) |
| 노드 | 5,185 (Class 1,289 / Function 2,593 / Test 353 / File 950) |
| 엣지 | 28,096 (CALLS 12,184 / CONTAINS 4,413 / IMPORTS_FROM 7,992 / INHERITS 1,661 / TESTED_BY 1,846) |
| FTS5 인덱스 | 5,185 rows |
| 커뮤니티 탐지 | file-based fallback (`igraph` 미설치) |
| DB 크기 | 47MB (`.code-review-graph/graph.db`) |
| 스키마 | v1 → v9 마이그레이션 자동 수행 |

**발견**:
- `find src -type f` 결과 `.java 0 / .kt 951` → **순수 Kotlin 레포**. 처음 1,925로 셌던 건 `build/` 하위 생성물 포함이었음.
- 브랜치/커밋 스탬프: `analysis/graphify` @ `17f8fe404c25` — 이후 브랜치 변경 시 재빌드 필요한지 확인 필요 (→ 오픈 질문)

#### 2.2 order-service 인덱스 빌드 + 멀티레포 등록

```bash
cd /Users/kakao/workspace/order-service
code-review-graph build

code-review-graph register /Users/kakao/workspace/claim2-service --alias claim2
code-review-graph register /Users/kakao/workspace/order-service  --alias order
```

| 레포 | alias | files | nodes | edges | lang |
|---|---|---|---|---|---|
| claim2-service | claim2 | 950 | 5,185 | 28,096 | kotlin |
| order-service | order | 2,373 | 11,474 | 82,162 | java |

레지스트리 위치: `~/.code-review-graph/registry.json` (유저 전역)

#### 2.3 MCP stdio 직접 handshake로 tool 인벤토리 확보

저자의 자동 `install`(CLAUDE.md 자동 주입 등)을 피하려고 Python 스크립트로 JSON-RPC 직접 호출:

- `initialize` → `notifications/initialized` → `tools/list`
- 총 **30개 MCP tool** 확인 (README는 28; v2.14.7 기준 증가)
- **멀티레포 전용 tool은 2개뿐**: `list_repos_tool`, `cross_repo_search_tool`
- 나머지 28개는 current graph 하나에서만 동작

`cross_repo_search_tool` 스키마: `query` (필수), `kind` (File/Class/Function/Type/Test), `limit`
설명 원문: *"Runs hybrid search on each registered repo's graph database and merges the results by score."*
→ **각 레포 그래프에 독립 검색 → 스코어로 머지**. 통합 그래프가 아니므로 **cross-repo 호출 체인 traversal 구조적으로 불가능**.

#### 2.4 멀티레포 질의 실측 — 🎯 핵심 발견

| query | kind | 결과 | 의미 |
|---|---|---|---|
| `Order` | (any) | 10 hits, 양 레포 모두 | 정상 |
| `Claim` | (any) | 10 hits, 양 레포 모두 — **order-service에 `ClaimHandler.java` 발견** | 🎯 서비스 간 호출 증거 |
| `KafkaListener` | Class | 0 hits | ❌ 어노테이션 심볼 못 잡음 |
| `RestTemplate` | (any) | 0 hits | ❌ import된 프레임워크 타입 못 잡음 |
| `WebClient` | (any) | 0 hits | ❌ 동일 |

**🎯 유즈케이스 발견**: order-service의 `ClaimHandler.java` 생성자가:

```java
(@Value("${msa.claim.url}") String domain,
 @Value("${msa.claim.internal-api-key}") String internalKey,
 RetrofitFactory<InternalClaimService> factory)
```

→ **order-service가 Retrofit으로 claim 서비스 internal API 호출**하는 증거. 같은 쿼리에서 claim2-service의 `OrderHandler.kt`도 등장 → **양방향 호출 관계가 심볼 이름만으로 자동 노출**. Graphify는 레포 단위라 이 연결 포착 불가.

**⚠️ 한계 발견**:
1. **프레임워크 심볼 미인덱싱** — CRG는 "이 레포에서 정의된 node"만 저장. `@KafkaListener`, `RestTemplate` 같은 third-party 참조는 별개 node로 기록 안 함. 어노테이션 스캔은 `grep` 영역.
2. **스코어 랭킹 품질 의심** — 모든 결과 score가 `0.016393`으로 균일. 사실상 substring match. 의미 검색은 `embed_graph_tool` 선행 필요.
3. **naming convention 의존성** — `XxxHandler` 같은 일관된 이름이 서비스 경계를 타고 재사용돼야 의미 있게 걸림. 다행히 해당 팀 코드엔 존재.

#### 2.5 claim2-service에 MCP + skills만 선택적 install

```bash
cd /Users/kakao/workspace/claim2-service
code-review-graph install --platform claude-code --no-hooks --no-instructions -y
```

생성된 파일 (flag 정확히 존중됨):

| 경로 | 생성 여부 |
|---|---|
| `.mcp.json` | ✅ |
| `.claude/skills/*.md` (debug-issue, explore-codebase, refactor-safely, review-changes) | ✅ |
| `.gitignore` append (`.code-review-graph/`) | ✅ |
| `CLAUDE.md` | ❌ (`--no-instructions`) |
| `.claude/settings.json` | ❌ (`--no-hooks`) |
| `.git/hooks/pre-commit` | ❌ (`--no-hooks`) |

옵션 결정 근거: [guide §5.6](./code-review-graph-guide.md).

#### 2.6 `.mcp.json` 수동 패치 — `--repo` 절대경로 고정

install이 만든 기본 `.mcp.json`은 `serve`를 `--repo` 없이 실행해서 **cwd 의존**. Claude Code 런타임에서 "그래프 등록 안 됨" 에러 발생. 절대경로 명시로 수정:

```json
"args": ["code-review-graph", "serve", "--repo", "/Users/kakao/workspace/claim2-service"]
```

**검증**: `cwd=/tmp`에서 stdio handshake 후 `list_graph_stats_tool` 호출 → claim2 그래프 정확히 반환 (950 files / 5,185 nodes).

상세는 [guide §5.5](./code-review-graph-guide.md).

---

## 3. 다음 실험 큐 (우선순위 순)

1. [ ] **Claude Code에서 실사용** — claim2-service에서 재시작 후 "ClaimService 호출자 찾아줘" 등 실제 세션에서 CRG tool이 사용되는지 관찰
2. [ ] **`embed_graph_tool`** — 임베딩 빌드 후 semantic_search_nodes_tool 품질 재측정 (score 랭킹 문제 해소되나)
3. [ ] **`detect-changes`** — 최근 커밋 하나 잡아 blast radius 파일 수 측정 (리뷰 유즈케이스 직결)
4. [ ] **order-service에 동일 install** — multi-repo 워크플로우 완성 (`--repo` 절대경로 주의)
5. [ ] **`wiki` + `visualize`** — 커뮤니티 기반 wiki 자동 생성 / HTML 그래프, 발표 자료 재료
6. [ ] **Graphify 출력과 중복 판단** — `graphify-out/`과 CRG 그래프가 정보 중복인지 보완인지
7. [ ] **`prompts/service-analysis`의 11개 dimension vs CRG tool 매핑** — 어느 관점이 CRG로 가속되고 어느 것은 tree-walking 필요한지

**스킵 결정**: `eval` 벤치마크 — 저자가 번들한 6개 fixture repo (express/fastapi/flask/gin/httpx/nextjs) + 13개 지정 커밋 전용. claim2/order에서 재현 시도는 무의미 (직접 ground-truth 작성해야 함).

---

## 4. 오픈 질문 / 미해결 사항

- [ ] **브랜치 스위칭 시 증분 동작**: `update`가 branch diff를 감지하는지, 아니면 파일 mtime만 보는지
- [ ] **커뮤니티 탐지 fallback vs igraph 차이**: 어느 쪽이 wiki/visualize 품질에 유의미한 차이를 만드나
- [ ] **Kotlin tree-sitter 커버리지**: DSL·Gradle script(`.gradle.kts`)는 파싱되나 (build.gradle.kts는 대상에서 빠진 듯)
- [ ] **semantic search vs substring match**: 임베딩 빌드 후 실제 ranking 품질이 어떻게 달라지나
- [ ] **CRG MCP 연결 상태 검증 방법**: Claude Code 세션에서 "MCP 살아있다"를 확인할 표준 절차

---

## 5. 시행착오 메모 (실험 중 발생 건 누적)

> 도구 자체의 일반 팁(예: `--repo` 절대경로 수정)은 guide 쪽으로 이동. 여기는 **실험 진행 중 헛발질·되돌린 결정** 기록.

### 5.1 "eval 벤치마크 먼저 돌리자" 제안을 스스로 철회 (2026-04-21)

**상황**: 초기 실험 큐에서 `eval --all`을 1순위로 제안했음.
**반성**: 확인해보니 `eval`은 저자의 curated fixture repo 6개 + 13개 지정 커밋 전용. 임의 레포에 돌리면 의미 있는 수치 안 나옴.
**수정**: 큐에서 제거, `detect-changes`·`cross_repo_search` 같이 실제 claim2/order에 적용 가능한 실험으로 교체.
**교훈**: 벤치마크 툴의 "fixture 의존성"을 먼저 확인할 것.

---

## 6. 팀 발표 초안 (후반부에 누적)

> 탐색이 어느 정도 끝나면 아래를 채움. 현재는 스캐폴드만.

### 6.1 문제 정의
- (TBD)

### 6.2 CRG가 하는 일 (1줄)
- (TBD)

### 6.3 claim2-service 실측치
- (TBD — MCP 실사용 + detect-changes 후 채움)

### 6.4 Graphify + service-analysis 워크플로우와의 관계
- (TBD)

### 6.5 도입 권장 여부 & 조건
- (TBD)

### 6.6 운영 리스크
- 빠른 릴리스 주기 (7주에 47버전)
- `install` 자동 주입의 CLAUDE.md 오염 가능성 → `--no-hooks --no-instructions`로 회피 ([guide §5.6](./code-review-graph-guide.md))
- 기본 `.mcp.json`의 cwd 의존 — `--repo` 절대경로 수동 수정 필요 ([guide §5.5](./code-review-graph-guide.md))

---

## 참고

- [code-review-graph-guide.md](./code-review-graph-guide.md) — 도구 설명 · 설치 · 운영 팁
- [CRG GitHub](https://github.com/tirth8205/code-review-graph)
- [CLAUDE.md](../CLAUDE.md) — 이 repo의 운영 규약
- [handoff.md](./handoff.md) — 2026-04-20 세션 핸드오프 (Graphify 분석 지점)

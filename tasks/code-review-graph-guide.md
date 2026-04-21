# Code Review Graph — 도구 설명 · 설치 · 운영 가이드

> CRG 자체에 대한 설명, 설치 방법, 운영 팁.
> 실험 진행 기록과 유즈케이스 탐색은 [code-review-graph-eval.md](./code-review-graph-eval.md) 참조.

---

## 1. 한 줄 요약

Tree-sitter로 레포를 AST 그래프로 인덱싱해 SQLite에 저장하고, Claude Code가 MCP로 "필요한 파일만 딱딱" 찾아 읽도록 해주는 **로컬 도구**.

- 공식 저장소: <https://github.com/tirth8205/code-review-graph> (MIT, v2.14.7 @ 2026-04-21)
- PyPI: `code-review-graph`
- 본질 용도: **PR/커밋 리뷰 시 컨텍스트 축소**, 편집 중 blast radius 질의
- 서비스 1개를 통째로 이해 · 리버스 엔지니어링 용도는 아님 (Graphify가 더 적합)

---

## 2. 동작 구조

3단계:

| 단계 | 하는 일 | 저장 |
|---|---|---|
| Parse | Tree-sitter로 AST 생성 | — |
| Store | 노드(Class/Function/Test 등) + 엣지(CALLS/IMPORTS_FROM/INHERITS/TESTED_BY) 저장 | `.code-review-graph/graph.db` (SQLite, 로컬) |
| Query | 변경/질문 → caller/dependent 체인 → 최소 파일 집합 | MCP tool로 노출 |

지원 언어 23개 + Jupyter: Python, TypeScript/TSX, JavaScript, Vue, Svelte, Go, Rust, **Java**, Scala, C#, Ruby, **Kotlin**, Swift, PHP, Solidity, C/C++, Dart, R, Perl, Lua, Zig, PowerShell, Julia.

---

## 3. 타 도구와의 포지셔닝

| 축 | Graphify | Code Review Graph |
|---|---|---|
| 실행 시점 | 분석 시작 전 1회 | Claude 세션 중 실시간 |
| 산출물 | 정적 파일 (`graph.json`, 리포트) | 라이브 SQLite + 28~30개 MCP tool |
| 소비 주체 | 사람이 Claude에 컨텍스트로 붙여줌 | Claude가 필요할 때마다 MCP 호출 |
| 업데이트 | 수동 재실행 | 파일 저장/커밋 시 증분 (~2초) |
| 멘탈 모델 | 구조를 덤프 | 구조에 대해 질의 |

둘 다 AST 그래프를 만들지만 **용도가 다름**. 서비스 분석 워크플로우(`prompts/service-analysis`)는 Graphify가 맞고, CRG는 리뷰/편집 단계 보완.

---

## 4. 안전성 체크 (2026-04-21 기준)

| 항목 | 값 | 판단 |
|---|---|---|
| GitHub stars / forks / contributors | 11.9k / 1.3k / 64 | 높음 |
| License | MIT | OK |
| PyPI 최신 | v2.3.2 (2026-04-14) | — |
| serve 런타임 버전 | v2.14.7 (내부) | — |
| 릴리스 횟수 / 기간 | 47 / 7주 | 공격적 — breaking change 주시 |
| 핵심 의존성 | mcp, fastmcp, tree-sitter, tree-sitter-language-pack, networkx, watchdog | 표준 |

공급망 공격 패턴 없음. 빠른 릴리스 주기 때문에 버전 올릴 때 주의.

---

## 5. 설치 가이드

### 5.1 CLI 바이너리 — 격리 설치 권장

```bash
uv tool install code-review-graph
```

- 전용 venv (`~/.local/share/uv/tools/code-review-graph/`), 유저 사이트 오염 없음
- 실행파일: `~/.local/bin/code-review-graph`
- `pipx install code-review-graph`도 동등
- 일반 `pip install --user`는 다른 패키지와 충돌 가능 → 비추

### 5.2 첫 그래프 빌드

```bash
cd <repo>
code-review-graph build
```

- `.code-review-graph/graph.db` 생성, 자동 `.gitignore` 추가
- 950~2300 파일 기준 10~30초
- `build/`, `target/` 등 기본 제외. 추가 제외는 `.code-review-graphignore`

### 5.3 멀티 레포 레지스트리 등록

```bash
code-review-graph register <path> --alias <name>
code-review-graph repos
```

- 레지스트리 위치: `~/.code-review-graph/registry.json` (**유저 전역**)
- 등록 후 MCP의 `cross_repo_search_tool`이 모든 레포 대상 연합 검색

### 5.4 MCP 서버 등록 (Claude Code)

**권장 커맨드** — hooks/CLAUDE.md 자동 주입은 꺼둠:

```bash
cd <repo>
code-review-graph install --platform claude-code --no-hooks --no-instructions -y
```

생성되는 파일 (전부 프로젝트 로컬, 전역 오염 없음):

| 경로 | 내용 |
|---|---|
| `<repo>/.mcp.json` | MCP 서버 등록 — ⚠️ **5.5에서 반드시 수정** |
| `<repo>/.claude/skills/*.md` | 4개 skill: debug-issue, explore-codebase, refactor-safely, review-changes |
| `<repo>/.gitignore` | `.code-review-graph/` append |

끄는 것 (`--no-hooks --no-instructions`):
- `<repo>/CLAUDE.md` append (5.6.2 참고)
- `<repo>/.claude/settings.json` hooks (5.6.1 참고)
- `<repo>/.git/hooks/pre-commit` (5.6.1 참고)

재시작: install 후 Claude Code를 해당 프로젝트에서 재오픈해야 config 반영.

### 5.5 `.mcp.json`의 `--repo` 절대경로 고정 — **필수 수정**

install이 만든 기본 `.mcp.json`:

```json
{"command": "uvx", "args": ["code-review-graph", "serve"], "type": "stdio"}
```

`serve`가 `--repo` 없이 실행되면 **현재 cwd의 `.code-review-graph/graph.db`**를 찾음. Claude Code 런타임 cwd가 레포 루트와 다르거나 외부에서 MCP 호출 시 즉시 "그래프 없음" 에러.

**직접 편집**해서 `--repo` 절대경로 추가:

```json
{
  "mcpServers": {
    "code-review-graph": {
      "command": "uvx",
      "args": [
        "code-review-graph",
        "serve",
        "--repo",
        "/Users/kakao/workspace/<repo-name>"
      ],
      "type": "stdio"
    }
  }
}
```

검증: 임의 cwd(예: `/tmp`)에서 stdio handshake 후 `list_graph_stats_tool` 호출 시 정확한 레포 stats 반환되면 OK.

이 수정은 저자 README에 명시 안 됨. 실제 세션에서 반드시 밟게 되는 함정.

### 5.6 install 옵션 상세 — 무엇을 켜고 끄나

`install --platform claude-code`가 건드릴 수 있는 4개 대상과 우리 권장:

| 대상 | 기본 | 권장 | 플래그 | 이유 |
|---|---|---|---|---|
| `.mcp.json` | ✅ | ✅ | (기본) | MCP 서버 등록 — install의 본체. 스코프는 프로젝트 로컬. |
| `.claude/skills/*.md` | ✅ | ✅ | (기본) | 트리거 시점에만 로드 → 세션 토큰 비용 0. 워크플로우 힌트로 유용. |
| `CLAUDE.md` append | ✅ | ❌ | `--no-instructions` | 사용자가 관리 중인 파일 자동 편집. 롤백 경로 불명확. |
| `.claude/settings.json` + `.git/hooks/pre-commit` | ✅ | ❌ | `--no-hooks` | 아래 5.6.1 상세. |

#### 5.6.1 hooks를 끄는 구체적 이유

install이 기본으로 주입하는 hook 3종 (`skills.py:420-492`):

| hook | 트리거 | 실행 명령 | 문제 |
|---|---|---|---|
| `PostToolUse` | Edit / Write / Bash tool 호출 직후 | `code-review-graph update --skip-flows` (timeout 30s) | **매 편집마다 SQLite 재파싱 오버헤드**. 큰 레포에서 누적. 30초 초과 시 silent 실패. |
| `SessionStart` | 세션 시작 | `code-review-graph status` (timeout 10s) | 매 세션 ~100토큰 상시 비용. 상태 수시 필요 없으면 낭비. |
| `pre-commit` | 로컬 `git commit` | `code-review-graph detect-changes --brief` | CRG 바이너리가 커밋 쉘 PATH에 있어야 작동. 환경별 깨지기 쉬움. |

**결정적 문제**: hook은 **자동 실행**이라 CRG를 안 쓰고 싶은 세션/커밋에서도 무조건 돈다. off/on을 세션별로 제어 불가. 수동 `code-review-graph update`는 필요할 때 한 번 치면 되는데, hook이면 **디폴트가 항상 ON**.

#### 5.6.2 `CLAUDE.md` 자동 주입을 끄는 이유

- 프로젝트의 `CLAUDE.md`는 사람이 직접 쓴 **운영 규약 문서** — LLM이 append하면 규약과 충돌 위험 (예: "wiki 수동 편집 금지" 같은 invariant 옆에 CRG 지시문이 섞임)
- 업데이트 시 이전 주입 블록 제거 로직 불확실 → 여러 번 install하면 중복 누적 가능성
- 필요한 지시는 이미 skill 파일이 담음 → `CLAUDE.md` 중복 주입은 이중 관리
- 정말 필요한 힌트만 **사람이 직접 한 줄 추가**하는 게 관리하기 쉬움 (예: "코드 리뷰 시 먼저 `get_minimal_context_tool` 호출")

#### 5.6.3 skills를 켜두는 이유

- 트리거 keyword 매칭 시에만 로드 → **세션당 상시 토큰 비용 0**
- skill 파일 내용은 "먼저 X tool 호출, 다음 Y"처럼 **워크플로우 힌트**라 실질 도움
- 파일로 존재 → 수정·삭제 쉬움 (CLAUDE.md append와 달리 격리됨)
- 단점: "CRG tool 먼저 써" 편향 주입 → grep이면 충분한 상황에도 CRG 호출 유도 가능. 지나치면 해당 skill 파일 삭제하면 됨.

#### 5.6.4 각 레포 반복 설치 / register는 1회

- `.mcp.json`, `.claude/skills/`는 **프로젝트 로컬** → 서비스 레포마다 `install` 반복
- `register`는 **유저 전역** → 한 번만 등록하면 모든 레포의 MCP 서버가 공유

---

## 6. 운영 팁

### 6.1 의미 검색 활성화 — `embed_graph_tool` 선행 필요

기본 `cross_repo_search_tool`은 substring match 기반이라 **결과 score가 모두 균일(예: 0.016)** → 랭킹 품질 낮음. 의미 검색 활성화:

```bash
uv tool install --reinstall "code-review-graph[embeddings]"
# 이후 Claude 세션에서 embed_graph_tool 또는 CLI 대응 명령 호출
```

옵션 의존성: `sentence-transformers`.

### 6.2 CRG의 명확한 한계

- **프로젝트 정의 심볼만 인덱싱** — `@KafkaListener`, `RestTemplate`, `WebClient` 같은 프레임워크/third-party 참조는 node로 저장 안 됨 → grep / ripgrep 영역
- **서비스 경계 호출 체인**은 심볼 이름이 일치해야 감지됨 (`XxxHandler` naming convention에 의존)
- `cross_repo_search`는 **연합 검색**이지 통합 그래프 아님 → cross-repo traversal 구조적으로 불가능

### 6.3 제거 / 롤백

| 대상 | 명령 |
|---|---|
| CLI 바이너리 | `uv tool uninstall code-review-graph` |
| 그래프 DB | `rm -rf <repo>/.code-review-graph` |
| 프로젝트 MCP 연동 | `rm <repo>/.mcp.json; rm -rf <repo>/.claude/skills` |
| 레지스트리 | `rm ~/.code-review-graph/registry.json` |
| (hook 있으면) | `rm <repo>/.claude/settings.json` + `.git/hooks/pre-commit`에서 CRG 섹션 제거 |

### 6.4 MCP tool 전체 목록 확인

30개 tool을 직접 나열:

```bash
python3 - <<'PY'
import json, subprocess
p = subprocess.Popen(["code-review-graph","serve","--repo","<repo>"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
def send(o): p.stdin.write(json.dumps(o)+"\n"); p.stdin.flush()
send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"m","version":"0"}}})
p.stdout.readline()
send({"jsonrpc":"2.0","method":"notifications/initialized"})
send({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})
for t in json.loads(p.stdout.readline())["result"]["tools"]:
    print(t["name"])
PY
```

카테고리:
- **단일 레포 분석**: `get_minimal_context_tool`, `get_impact_radius_tool`, `detect_changes_tool`, `query_graph_tool`, `traverse_graph_tool`
- **의미 검색**: `semantic_search_nodes_tool`, `embed_graph_tool`
- **구조 탐색**: `list_flows_tool`, `list_communities_tool`, `get_hub_nodes_tool`, `get_bridge_nodes_tool`, `get_architecture_overview_tool`
- **리팩토링**: `refactor_tool`, `apply_refactor_tool`
- **Wiki**: `generate_wiki_tool`, `get_wiki_page_tool`
- **멀티 레포**: `list_repos_tool`, `cross_repo_search_tool`

---

## 7. 참고

- 공식 문서: <https://github.com/tirth8205/code-review-graph/tree/main/docs>
- PyPI: <https://pypi.org/project/code-review-graph/>
- 실험 저널: [code-review-graph-eval.md](./code-review-graph-eval.md)

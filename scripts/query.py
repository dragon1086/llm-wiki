"""LLM Wiki — Query Engine

wiki 탐색 → claude CLI 합성 → output/ 저장 → findings/ 파일링
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from utils import (
    append_log,
    call_claude,
    extract_slugs_from_index,
    extract_wikilinks,
    read_agents_md,
    read_index_md,
    read_wiki_pages,
    slugify,
    update_index,
    vault_path,
)


# ── Wiki 컨텍스트 수집 ────────────────────────────────────────────────────────

def collect_wiki_context(question: str, char_budget: int = 18000) -> str:
    """
    질문과 관련된 wiki 페이지를 읽어 컨텍스트 문자열로 반환.

    3단계 전략 (graphify BFS 패턴):
    1. 키워드 매칭으로 시드 slug 선택 (상위 10개)
    2. 시드 페이지의 [[wikilinks]] 따라 1홉 이웃 확장
    3. 연결도(wikilink 수) 높은 순 정렬 후 char_budget 내 포함
    """
    index_content = read_index_md()
    all_slugs = extract_slugs_from_index()
    valid_slugs = set(all_slugs)

    # 1단계: 키워드 기반 시드 선택
    question_words = set(re.findall(r"\w+", question.lower()))
    scored: list[tuple[int, str]] = []
    for slug in all_slugs:
        slug_words = set(re.split(r"[-_]", slug.lower()))
        score = len(question_words & slug_words)
        scored.append((score, slug))
    scored.sort(key=lambda x: -x[0])

    seed_slugs = [s for sc, s in scored[:10] if sc > 0] or [s for _, s in scored[:10]]
    seed_set = set(seed_slugs)

    # 2단계: BFS 1홉 확장 — 시드 페이지의 [[wikilinks]] 수집
    seed_pages = read_wiki_pages(seed_slugs)
    neighbors: set[str] = set()
    for content in seed_pages.values():
        for link in extract_wikilinks(content):
            if link in valid_slugs and link not in seed_set:
                neighbors.add(link)

    # 3단계: 후보 전체 읽기 + 연결도 기반 정렬
    all_pages = {**seed_pages, **read_wiki_pages(list(neighbors))}

    def connectivity(content: str) -> int:
        return len(extract_wikilinks(content))

    ranked = sorted(
        all_pages.items(),
        key=lambda kv: (1 if kv[0] in seed_set else 0, connectivity(kv[1])),
        reverse=True,
    )

    # 4단계: char_budget 내에서 페이지 포함
    parts = [f"## wiki/index.md\n{index_content}"]
    used = len(parts[0])
    for slug, content in ranked:
        entry = f"## wiki page: {slug}\n{content}"
        if used + len(entry) > char_budget:
            break
        parts.append(entry)
        used += len(entry)

    return "\n\n---\n\n".join(parts)


# ── 프롬프트 빌드 ─────────────────────────────────────────────────────────────

_OUTPUT_FORMAT_INSTRUCTIONS = {
    "text": "텍스트 마크다운 파일 (output/<slug>.md)",
    "slides": "Marp 슬라이드 파일 (output/<slug>.marp.md) — marp: true frontmatter 포함",
    "diagram": "Mermaid 다이어그램 마크다운 파일 (output/<slug>.md) — ```mermaid 코드블록 포함, flowchart/sequence/ER 등 적절히 선택",
    "chart": "matplotlib Python 코드 파일 (output/<slug>.py) — plt.savefig('{png_path}') 마지막 줄에 포함, plt.show() 금지",
}


def build_query_prompt(
    question: str,
    wiki_context: str,
    agents_md: str,
    output_format: str,
    output_slug: str,
) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    png_abs = str(vault_path() / "output" / f"{output_slug}.png")

    if output_format == "slides":
        output_path = f"output/{output_slug}.marp.md"
    elif output_format == "chart":
        output_path = f"output/{output_slug}.py"
    else:
        # text, diagram 모두 .md
        output_path = f"output/{output_slug}.md"

    fmt_raw = _OUTPUT_FORMAT_INSTRUCTIONS.get(output_format, _OUTPUT_FORMAT_INSTRUCTIONS["text"])
    fmt_desc = fmt_raw.replace("{png_path}", png_abs)

    return f"""## 출력 형식 (최우선 규칙)

지금 즉시 `===FILE:` 로 시작하는 블록만 출력하라.
설명, 요약, 확인 문구 등 일체의 다른 텍스트 금지.
첫 번째 문자는 반드시 `=` 이어야 한다.

형식:
===FILE: {output_path}===
<답변 내용 — {fmt_desc}>
===END===
===FINDING: {output_slug} | <질문 한 줄 요약> | <한 줄 설명>===
===LOG: "<질문 요약>" → {output_path}===

FINDING 블록은 답변이 재사용 가치가 있을 때만 포함 (선택).

---

## Wiki 스키마 (AGENTS.md)

{agents_md}

---

## Wiki 컨텍스트

{wiki_context}

---

## 질문

{question}

---

## 지시사항

위 wiki 컨텍스트를 탐색하여 질문에 답하라:
1. index.md에서 관련 페이지 파악
2. 해당 페이지 내용을 종합해 답변 구성
3. 모든 언급 개념/엔티티에 [[wikilink]] 삽입
4. 출력 형식: {fmt_desc}
5. 오늘 날짜: {today}

지금 `===FILE:` 로 시작하는 출력을 즉시 생성하라.
"""


# ── 응답 파싱 ─────────────────────────────────────────────────────────────────

_FILE_PATTERN = re.compile(r"===FILE:\s*(.+?)===(.*?)===END===", re.DOTALL)
_FINDING_PATTERN = re.compile(
    r"===FINDING:\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)==="
)
_LOG_PATTERN = re.compile(r"===LOG:\s*(.+?)===")


def parse_query_output(output: str) -> dict:
    pages = []
    for m in _FILE_PATTERN.finditer(output):
        pages.append({"path": m.group(1).strip(), "content": m.group(2).strip()})

    findings = []
    for m in _FINDING_PATTERN.finditer(output):
        findings.append({
            "slug": m.group(1).strip(),
            "query_summary": m.group(2).strip(),
            "description": m.group(3).strip(),
        })

    log_match = _LOG_PATTERN.search(output)
    log_message = log_match.group(1).strip() if log_match else f"query 완료"

    return {"pages": pages, "findings": findings, "log_message": log_message}


# ── 파일 쓰기 ─────────────────────────────────────────────────────────────────

def write_output_pages(pages: list) -> list:
    """output/ 파일 쓰기. 생성된 파일 경로 목록 반환."""
    base = vault_path()
    written = []
    for page in pages:
        file_path = base / page["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(page["content"], encoding="utf-8")
        written.append(str(file_path))
    return written


def write_finding(finding: dict, output_files: list) -> None:
    """findings/ 에 finding 페이지 저장."""
    today = datetime.now().strftime("%Y-%m-%d")
    slug = finding["slug"]
    w = vault_path() / "wiki" / "findings"
    w.mkdir(parents=True, exist_ok=True)

    frontmatter = (
        f"---\n"
        f"type: finding\n"
        f"query: \"{finding['query_summary']}\"\n"
        f"date: \"{today}\"\n"
        f"output_files: {output_files}\n"
        f"---\n\n"
    )

    # output 파일 임베드
    embeds = "\n".join(
        f"![[{Path(f).name}]]" if Path(f).suffix in {".png", ".jpg"} else f"[[{Path(f).name}]]"
        for f in output_files
    )

    content = frontmatter + f"# {finding['query_summary']}\n\n{embeds}\n"
    (w / f"{slug}.md").write_text(content, encoding="utf-8")

    update_index("findings", slug, finding["description"])


# ── 차트 실행 ─────────────────────────────────────────────────────────────────

def execute_chart(py_path: str, png_path: str) -> None:
    """생성된 matplotlib 코드를 실행하여 PNG를 저장."""
    proc = subprocess.Popen(
        [sys.executable, py_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _, stderr = proc.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise RuntimeError(f"차트 실행 타임아웃 (60s): {py_path}")

    if proc.returncode != 0:
        raise RuntimeError(
            f"차트 실행 실패 (returncode={proc.returncode}):\n{stderr.decode()}"
        )

    if not Path(png_path).exists():
        raise RuntimeError(f"PNG 파일이 생성되지 않았습니다: {png_path}")


# ── 메인 오케스트레이터 ───────────────────────────────────────────────────────

def run_query(
    question: str,
    output_format: str = "text",
    debug: bool = False,
) -> dict:
    """
    wiki 질의 실행.
    반환: {question, output_files, findings_created, log_message}
    """
    output_slug = slugify(question[:60])
    agents_md = read_agents_md()
    wiki_context = collect_wiki_context(question)

    prompt = build_query_prompt(
        question=question,
        wiki_context=wiki_context,
        agents_md=agents_md,
        output_format=output_format,
        output_slug=output_slug,
    )

    print(f"[query] '{question[:50]}...' 처리 중... (claude CLI 호출)")
    raw_output = call_claude(prompt, debug=debug)

    parsed = parse_query_output(raw_output)

    if not parsed["pages"]:
        raise RuntimeError(
            f"claude 응답에서 FILE 블록을 찾을 수 없습니다.\n응답 미리보기:\n{raw_output[:500]}"
        )

    written = write_output_pages(parsed["pages"])

    if output_format == "chart":
        png_path = str(vault_path() / "output" / f"{output_slug}.png")
        py_files = [f for f in written if f.endswith(".py")]
        if py_files:
            print(f"[query] 차트 실행 중: {py_files[0]}")
            execute_chart(py_files[0], png_path)
            written.append(png_path)

    findings_created = 0
    for finding in parsed["findings"]:
        write_finding(finding, written)
        findings_created += 1

    append_log("QUERY", parsed["log_message"])

    return {
        "question": question,
        "output_files": written,
        "findings_created": findings_created,
        "log_message": parsed["log_message"],
    }

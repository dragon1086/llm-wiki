"""LLM Wiki — Ingest Pipeline

raw/ 소스 파일 → claude CLI → wiki 페이지 생성/갱신
"""

import re
import subprocess
from pathlib import Path

from utils import (
    append_log,
    get_claude_bin,
    list_wiki_pages,
    read_agents_md,
    update_index,
    vault_path,
)


# ── 프롬프트 빌드 ─────────────────────────────────────────────────────────────

def build_ingest_prompt(
    source_filename: str,
    source_content: str,
    agents_md: str,
    existing_pages: dict[str, list[str]],
) -> str:
    existing_summary = "\n".join(
        f"  {subdir}/: {', '.join(slugs) if slugs else '(없음)'}"
        for subdir, slugs in existing_pages.items()
    )

    return f"""## 출력 형식 (최우선 규칙)

지금 즉시 `===FILE:` 로 시작하는 블록만 출력하라.
설명, 요약, 목록, 확인 문구 등 일체의 다른 텍스트 금지.
첫 번째 문자는 반드시 `=` 이어야 한다.

형식:
===FILE: wiki/<subdir>/<slug>.md===
<YAML frontmatter + 최소 300자 본문>
===END===
===INDEX_UPDATE: <Summaries|Concepts|Entities|Findings> | <slug> | <한 줄 설명>===
===LOG: {source_filename} → <N>개 페이지 갱신===

---

## Wiki 스키마 (AGENTS.md)

{agents_md}

---

## 현재 Wiki 상태

{existing_summary}

---

## 처리할 소스

파일명: {source_filename}

{source_content}

---

## 지시사항

위 소스를 처리하여 wiki 페이지를 생성/갱신하라:
1. summaries/ 에 소스 요약 1개 생성
2. 언급된 entity마다 entities/ 페이지 생성/갱신
3. 언급된 concept마다 concepts/ 페이지 생성/갱신
4. 모든 페이지에 [[wikilink]] 삽입
5. 각 페이지 본문 최소 300자
6. 기존 페이지(위 목록 참조)는 upsert (내용 보강)

지금 `===FILE:` 로 시작하는 출력을 즉시 생성하라.
"""


# ── Claude CLI 호출 ───────────────────────────────────────────────────────────

def call_claude(prompt: str, timeout: int = 300, debug: bool = False) -> str:
    """
    claude CLI subprocess 호출.
    - Popen + communicate(timeout) 패턴으로 고아 프로세스 방지
    - timeout 초과 시 명시적 kill 후 예외 발생
    """
    claude_bin = get_claude_bin()
    proc = subprocess.Popen(
        [claude_bin, "--dangerously-skip-permissions", "-p", prompt],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()  # 파이프 비우기 (좀비 방지)
        raise RuntimeError(
            f"claude CLI가 {timeout}초 내에 응답하지 않아 종료했습니다."
        )

    if debug:
        debug_path = Path("/tmp/llm-wiki-debug.txt")
        debug_path.write_text(f"=== STDOUT ===\n{stdout}\n=== STDERR ===\n{stderr}", encoding="utf-8")
        print(f"[debug] raw 응답 저장: {debug_path}")

    if proc.returncode != 0:
        raise RuntimeError(
            f"claude CLI 오류 (returncode={proc.returncode}):\n{stderr}"
        )

    return stdout


# ── 응답 파싱 ─────────────────────────────────────────────────────────────────

_FILE_PATTERN = re.compile(
    r"===FILE:\s*(.+?)===(.*?)===END===",
    re.DOTALL,
)
_INDEX_PATTERN = re.compile(
    r"===INDEX_UPDATE:\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)==="
)
_LOG_PATTERN = re.compile(r"===LOG:\s*(.+?)===")


def parse_claude_output(output: str) -> dict:
    """
    Claude 응답에서 FILE 블록, INDEX_UPDATE, LOG 추출.
    반환: {pages, index_updates, log_message}
    """
    pages = []
    for m in _FILE_PATTERN.finditer(output):
        path = m.group(1).strip()
        content = m.group(2).strip()
        pages.append({"path": path, "content": content})

    index_updates = []
    for m in _INDEX_PATTERN.finditer(output):
        index_updates.append({
            "section": m.group(1).strip().lower(),  # → summaries / concepts / ...
            "slug": m.group(2).strip(),
            "description": m.group(3).strip(),
        })

    log_match = _LOG_PATTERN.search(output)
    log_message = log_match.group(1).strip() if log_match else "ingest 완료"

    return {
        "pages": pages,
        "index_updates": index_updates,
        "log_message": log_message,
    }


# ── 파일 쓰기 ─────────────────────────────────────────────────────────────────

def write_pages(pages: list[dict]) -> tuple[int, int]:
    """
    wiki 페이지 파일 쓰기.
    반환: (created_count, updated_count)
    """
    base = vault_path()
    created = updated = 0

    for page in pages:
        file_path = base / page["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists():
            file_path.write_text(page["content"], encoding="utf-8")
            updated += 1
        else:
            file_path.write_text(page["content"], encoding="utf-8")
            created += 1

    return created, updated


# ── 메인 오케스트레이터 ───────────────────────────────────────────────────────

def run_ingest(source_file: str, debug: bool = False) -> dict:
    """
    단일 소스 파일 ingest.
    반환: {source, pages_created, pages_updated, log_message}
    """
    source_path = Path(source_file)

    # raw/ 기준 상대경로 처리
    if not source_path.is_absolute():
        source_path = vault_path() / source_path

    if not source_path.exists():
        raise FileNotFoundError(f"소스 파일을 찾을 수 없습니다: {source_path}")

    source_content = source_path.read_text(encoding="utf-8")
    source_filename = source_path.name

    agents_md = read_agents_md()
    existing_pages = list_wiki_pages()

    prompt = build_ingest_prompt(
        source_filename=source_filename,
        source_content=source_content,
        agents_md=agents_md,
        existing_pages=existing_pages,
    )

    print(f"[ingest] {source_filename} 처리 중... (claude CLI 호출)")
    raw_output = call_claude(prompt, debug=debug)

    parsed = parse_claude_output(raw_output)

    if not parsed["pages"]:
        raise RuntimeError(
            f"claude 응답에서 FILE 블록을 찾을 수 없습니다.\n응답 미리보기:\n{raw_output[:500]}"
        )

    created, updated = write_pages(parsed["pages"])

    for upd in parsed["index_updates"]:
        update_index(
            page_type=upd["section"],
            slug=upd["slug"],
            description=upd["description"],
        )

    append_log("INGEST", parsed["log_message"])

    return {
        "source": source_filename,
        "pages_created": created,
        "pages_updated": updated,
        "log_message": parsed["log_message"],
    }

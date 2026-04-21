"""LLM Wiki — Ingest Pipeline

raw/ 소스 파일 → claude CLI → wiki 페이지 생성/갱신
"""

import re
import sys
from pathlib import Path

from utils import (
    append_log,
    call_claude,
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


# ── 응답 파싱 ─────────────────────────────────────────────────────────────────

_FILE_PATTERN = re.compile(
    r"===FILE:\s*(.+?)===(.*?)===END===",
    re.DOTALL,
)
# Claude가 파일명에 HTML 태그/공백 등을 환각하는 사례 차단 — 허용 경로 화이트리스트
_ALLOWED_PATH = re.compile(
    r"^wiki/(summaries|entities|concepts|findings)/[a-z0-9][a-z0-9_-]*\.md$"
)
_INDEX_PATTERN = re.compile(
    r"===INDEX_UPDATE:\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)==="
)
# INDEX_UPDATE의 slug도 파일명 규약과 같은 형식이어야 — sanitizer가 차단한 파일이
# index에 남는 dangling 방지
_ALLOWED_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
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
        if not _ALLOWED_PATH.match(path):
            print(f"⚠ 비정상 경로 스킵: {path!r}", file=sys.stderr)
            continue
        pages.append({"path": path, "content": content})

    index_updates = []
    for m in _INDEX_PATTERN.finditer(output):
        slug = m.group(2).strip()
        if not _ALLOWED_SLUG.match(slug):
            print(f"⚠ 비정상 slug 스킵 (INDEX_UPDATE): {slug!r}", file=sys.stderr)
            continue
        index_updates.append({
            "section": m.group(1).strip().lower(),  # → summaries / concepts / ...
            "slug": slug,
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
    raw_output = call_claude(prompt, timeout=900, debug=debug)

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

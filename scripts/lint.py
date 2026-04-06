"""LLM Wiki — Lint Engine

정적 검사:
  1. dead_links  — [[slug]]가 실제 파일 없음
  2. orphans     — 어떤 페이지에서도 참조되지 않는 페이지
  3. index_drift — wiki 파일과 index.md 불일치

LLM 검사 (--deep):
  4. contradictions — 연관 페이지 간 모순 탐지
"""

import re
from pathlib import Path
from utils import (
    append_log,
    call_claude,
    read_agents_md,
    read_index_md,
    wiki_dir,
)

_WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")

SUBDIRS = ["summaries", "entities", "concepts", "findings"]


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _all_wiki_files() -> dict[str, Path]:
    """wiki/ 하위 모든 .md 파일 → {slug: path}"""
    w = wiki_dir()
    result: dict[str, Path] = {}
    for subdir in SUBDIRS:
        for p in (w / subdir).glob("*.md") if (w / subdir).exists() else []:
            result[p.stem] = p
    return result


_FILE_SLUG_RE = re.compile(r"\.[a-zA-Z]{1,5}$|/")  # 확장자 또는 경로 포함 → 파일 임베드


def _load_lint_ignore() -> set[str]:
    """wiki/lint_ignore.txt 에서 무시할 slug 목록 로드."""
    p = wiki_dir() / "lint_ignore.txt"
    if not p.exists():
        return set()
    lines = p.read_text(encoding="utf-8").splitlines()
    return {l.strip() for l in lines if l.strip() and not l.startswith("#")}


def _extract_wikilinks(content: str) -> set[str]:
    """wiki slug 링크만 추출 (파일 임베드 및 경로 포함 링크 제외)."""
    return {
        s for s in _WIKILINK_PATTERN.findall(content)
        if not _FILE_SLUG_RE.search(s)
    }


def _all_wikilinks_in_wiki() -> dict[str, set[str]]:
    """각 페이지가 참조하는 wikilink 집합. {slug: {ref_slug, ...}}"""
    result: dict[str, set[str]] = {}
    for slug, path in _all_wiki_files().items():
        content = path.read_text(encoding="utf-8")
        result[slug] = _extract_wikilinks(content)
    return result


# ── 검사 1: dead links ────────────────────────────────────────────────────────

def check_dead_links() -> list[dict]:
    """
    [[slug]] 참조 중 실제 파일이 없는 항목 탐지.
    반환: [{page, dead_slug}, ...]
    """
    all_slugs = set(_all_wiki_files().keys())
    ignore = _load_lint_ignore()
    links_map = _all_wikilinks_in_wiki()
    # index.md도 포함
    index_links = _extract_wikilinks(read_index_md())

    issues = []
    for page_slug, refs in links_map.items():
        for ref in refs:
            if ref not in all_slugs and ref not in ignore:
                issues.append({"page": page_slug, "dead_slug": ref})

    for ref in index_links:
        if ref not in all_slugs and ref not in ignore:
            issues.append({"page": "index.md", "dead_slug": ref})

    return issues


# ── 검사 2: orphan pages ──────────────────────────────────────────────────────

def check_orphans() -> list[str]:
    """
    어떤 페이지에서도 [[slug]] 참조되지 않는 페이지 탐지.
    index.md 참조 포함.
    반환: [slug, ...]
    """
    all_slugs = set(_all_wiki_files().keys())
    links_map = _all_wikilinks_in_wiki()
    index_links = _extract_wikilinks(read_index_md())

    # 어딘가에서 참조된 slug 집합
    referenced: set[str] = set()
    for refs in links_map.values():
        referenced.update(refs)
    referenced.update(index_links)

    return sorted(all_slugs - referenced)


# ── 검사 3: index drift ───────────────────────────────────────────────────────

def check_index_drift() -> dict:
    """
    index.md와 실제 wiki 파일 간 불일치 탐지.
    반환: {missing_from_index: [slug], dangling_in_index: [slug]}
    """
    all_slugs = set(_all_wiki_files().keys())
    ignore = _load_lint_ignore()
    index_slugs = set(_extract_wikilinks(read_index_md())) - ignore

    missing_from_index = sorted(all_slugs - index_slugs)
    dangling_in_index = sorted(index_slugs - all_slugs)

    return {
        "missing_from_index": missing_from_index,
        "dangling_in_index": dangling_in_index,
    }


# ── 검사 4: LLM 모순 탐지 (--deep) ───────────────────────────────────────────

def _build_contradiction_prompt(pages: dict[str, str], agents_md: str) -> str:
    page_blocks = "\n\n---\n\n".join(
        f"### [{slug}]\n{content[:2000]}" for slug, content in pages.items()
    )
    return f"""## 출력 형식 (최우선 규칙)

지금 즉시 `===LINT:` 로 시작하는 블록만 출력하라.
설명, 요약, 확인 문구 등 일체의 다른 텍스트 금지.
첫 번째 문자는 반드시 `=` 이어야 한다.

형식:
===LINT: contradictions===
<발견된 모순 목록. 없으면 "(없음)" 한 줄만>
- [slug-A] vs [slug-B]: <모순 내용 한 줄>
===END===
===LOG: contradiction check 완료 — <N>개 모순 발견===

---

## Wiki 스키마 (AGENTS.md)

{agents_md}

---

## 검사할 Wiki 페이지

{page_blocks}

---

## 지시사항

위 wiki 페이지들을 검토하여 서로 모순되는 내용을 찾아라:
1. 동일 개념에 대한 상반된 정의나 설명
2. 날짜/버전/수치 불일치
3. 한 페이지가 "A는 X다"라고 하고 다른 페이지가 "A는 Y다"라고 하는 경우

지금 `===LINT:` 로 시작하는 출력을 즉시 생성하라.
"""


_LINT_PATTERN = re.compile(r"===LINT:\s*(.+?)===(.*?)===END===", re.DOTALL)


def check_contradictions(debug: bool = False) -> list[str]:
    """
    LLM을 사용해 wiki 페이지 간 모순 탐지.
    반환: [모순 설명 문자열, ...]
    """
    all_files = _all_wiki_files()
    if not all_files:
        return []

    # 모든 페이지 내용 로드 (최대 30개, 각 2000자 truncate)
    pages: dict[str, str] = {}
    for slug, path in list(all_files.items())[:30]:
        pages[slug] = path.read_text(encoding="utf-8")

    agents_md = read_agents_md()
    prompt = _build_contradiction_prompt(pages, agents_md)

    print("[lint] 모순 탐지 중... (claude CLI 호출)")
    raw = call_claude(prompt, debug=debug)

    contradictions = []
    for m in _LINT_PATTERN.finditer(raw):
        block = m.group(2).strip()
        if block != "(없음)":
            for line in block.splitlines():
                line = line.strip()
                if line and line.startswith("-"):
                    contradictions.append(line[1:].strip())

    return contradictions


# ── 보고서 출력 ───────────────────────────────────────────────────────────────

def _print_section(title: str, items: list) -> int:
    count = len(items)
    marker = "✓" if count == 0 else "⚠"
    print(f"\n{marker} {title}: {count}개")
    for item in items:
        print(f"  - {item}")
    return count


# ── 자동 수정: dangling index entries ─────────────────────────────────────────

def fix_dangling_index(dangling: list[str]) -> None:
    """index.md에서 파일 없는 [[slug]] 항목 제거."""
    index_path = wiki_dir() / "index.md"
    content = index_path.read_text(encoding="utf-8")
    for slug in dangling:
        # "- [[slug]] — ..." 행 제거
        content = re.sub(rf"^- \[\[{re.escape(slug)}\]\][^\n]*\n?", "", content, flags=re.MULTILINE)
    index_path.write_text(content, encoding="utf-8")
    print(f"[lint --fix] index.md에서 {len(dangling)}개 dangling 항목 제거")


# ── 메인 오케스트레이터 ───────────────────────────────────────────────────────

def run_lint(fix: bool = False, deep: bool = False, debug: bool = False) -> dict:
    """
    전체 lint 실행.
    반환: {dead_links, orphans, missing_from_index, dangling_in_index, contradictions}
    """
    print("\n=== LLM Wiki Lint ===")

    dead = check_dead_links()
    orphans = check_orphans()
    drift = check_index_drift()

    dead_items = [f"{d['page']} → [[{d['dead_slug']}]]" for d in dead]
    _print_section("Dead wikilinks", dead_items)
    _print_section("Orphan pages", orphans)
    _print_section("Index에서 누락 (파일은 있음)", drift["missing_from_index"])
    _print_section("Index에 있지만 파일 없음", drift["dangling_in_index"])

    contradictions = []
    if deep:
        contradictions = check_contradictions(debug=debug)
        _print_section("LLM 모순 탐지", contradictions)

    total_issues = len(dead) + len(orphans) + len(drift["missing_from_index"]) + len(drift["dangling_in_index"]) + len(contradictions)
    print(f"\n{'✓ 이상 없음' if total_issues == 0 else f'총 {total_issues}개 이슈 발견'}\n")

    if fix and drift["dangling_in_index"]:
        fix_dangling_index(drift["dangling_in_index"])

    log_msg = f"lint 완료 — {total_issues}개 이슈"
    append_log("LINT", log_msg)

    return {
        "dead_links": dead,
        "orphans": orphans,
        "missing_from_index": drift["missing_from_index"],
        "dangling_in_index": drift["dangling_in_index"],
        "contradictions": contradictions,
        "total_issues": total_issues,
    }

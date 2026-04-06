"""LLM Wiki — 공통 유틸리티"""

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import yaml


# ── 경로 헬퍼 ────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent


def load_config() -> dict:
    """config.yaml 로드"""
    config_path = REPO_ROOT / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def vault_path() -> Path:
    return Path(load_config()["vault_path"])


def raw_dir() -> Path:
    cfg = load_config()
    return Path(cfg["vault_path"]) / cfg["raw_dir"]


def wiki_dir() -> Path:
    cfg = load_config()
    return Path(cfg["vault_path"]) / cfg["wiki_dir"]


def output_dir() -> Path:
    cfg = load_config()
    return Path(cfg["vault_path"]) / cfg["output_dir"]


# ── 텍스트 유틸 ──────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """텍스트 → kebab-case 슬러그"""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# ── AGENTS.md 읽기 ───────────────────────────────────────────────────────────

def read_agents_md() -> str:
    """AGENTS.md 전문 반환 (LLM system prompt용)"""
    agents_path = REPO_ROOT / "AGENTS.md"
    with open(agents_path, "r", encoding="utf-8") as f:
        return f.read()


# ── Wiki 상태 스캔 ───────────────────────────────────────────────────────────

def list_wiki_pages() -> dict[str, list[str]]:
    """현재 wiki/ 파일 목록 반환. {subdir: [slug, ...]}"""
    w = wiki_dir()
    result: dict[str, list[str]] = {}
    for subdir in ["summaries", "entities", "concepts", "findings"]:
        d = w / subdir
        slugs = [p.stem for p in d.glob("*.md")] if d.exists() else []
        result[subdir] = slugs
    return result


def list_raw_files() -> list[Path]:
    """raw/ 내 .md 파일 목록"""
    return sorted(raw_dir().glob("*.md"))


def is_ingested(source_stem: str) -> bool:
    """summaries/ 에 동일 slug가 있으면 이미 인게스트됨"""
    summary_path = wiki_dir() / "summaries" / f"{slugify(source_stem)}.md"
    return summary_path.exists()


# ── log.md ───────────────────────────────────────────────────────────────────

def append_log(log_type: str, message: str) -> None:
    """wiki/log.md에 타임스탬프 엔트리 추가 (append-only)"""
    log_path = wiki_dir() / "log.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n[{timestamp}] [{log_type}] {message}"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


# ── index.md ─────────────────────────────────────────────────────────────────

_SECTION_MAP = {
    "summaries": "Summaries",
    "concepts": "Concepts",
    "entities": "Entities",
    "findings": "Findings",
}


def update_index(page_type: str, slug: str, description: str) -> None:
    """wiki/index.md의 해당 섹션에 새 항목 추가 (중복 방지)"""
    index_path = wiki_dir() / "index.md"
    section = _SECTION_MAP.get(page_type, page_type.capitalize())
    new_line = f"- [[{slug}]] — {description}"

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 이미 등록된 경우 스킵
    if f"[[{slug}]]" in content:
        return

    # 섹션 헤더 찾아 그 다음 줄에 삽입
    section_header = f"## {section}"
    if section_header in content:
        content = content.replace(
            section_header,
            f"{section_header}\n{new_line}",
        )
    else:
        content += f"\n\n{section_header}\n{new_line}"

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)

    # frontmatter의 total_pages 카운터 갱신
    _increment_index_counter(index_path, page_type)


def _increment_index_counter(index_path: Path, page_type: str) -> None:
    """index.md frontmatter의 total_* 카운터 +1"""
    key = f"total_{page_type}"
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    def replacer(m: re.Match) -> str:
        return f"{m.group(1)}{int(m.group(2)) + 1}"

    content = re.sub(rf"({key}: )(\d+)", replacer, content)

    # total_pages도 +1
    content = re.sub(r"(total_pages: )(\d+)", replacer, content)

    # updated 날짜 갱신
    today = datetime.now().strftime("%Y-%m-%d")
    content = re.sub(r"(updated: )\S+", f"\\g<1>{today}", content)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)


# ── claude CLI ───────────────────────────────────────────────────────────────

def get_claude_bin() -> str:
    """claude 실행 파일 경로 반환. 없으면 RuntimeError."""
    claude = shutil.which("claude")
    if not claude:
        raise RuntimeError(
            "claude CLI를 찾을 수 없습니다. Claude Code가 설치되어 있는지 확인하세요."
        )
    return claude


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
        debug_path.write_text(
            f"=== STDOUT ===\n{stdout}\n=== STDERR ===\n{stderr}",
            encoding="utf-8",
        )
        print(f"[debug] raw 응답 저장: {debug_path}")

    if proc.returncode != 0:
        raise RuntimeError(
            f"claude CLI 오류 (returncode={proc.returncode}):\n{stderr}"
        )

    return stdout


# ── Wiki 페이지 읽기 ──────────────────────────────────────────────────────────

_WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")


def read_wiki_pages(slugs: list) -> dict:
    """
    slug 목록에 해당하는 wiki 페이지 전문 반환.
    {slug: content} — 파일 없는 slug는 조용히 스킵.
    """
    w = wiki_dir()
    subdirs = ["concepts", "entities", "summaries", "findings"]
    result = {}

    for slug in slugs:
        for subdir in subdirs:
            path = w / subdir / f"{slug}.md"
            if path.exists():
                result[slug] = path.read_text(encoding="utf-8")
                break

    return result


def extract_slugs_from_index() -> list:
    """index.md에서 모든 [[slug]] 추출"""
    index_path = wiki_dir() / "index.md"
    if not index_path.exists():
        return []
    content = index_path.read_text(encoding="utf-8")
    return _WIKILINK_PATTERN.findall(content)


def read_index_md() -> str:
    """wiki/index.md 전문 반환"""
    index_path = wiki_dir() / "index.md"
    return index_path.read_text(encoding="utf-8") if index_path.exists() else ""

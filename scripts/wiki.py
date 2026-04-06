#!/usr/bin/env python3
"""LLM Wiki — CLI 진입점

Usage:
  python scripts/wiki.py ingest raw/<file>.md
  python scripts/wiki.py ingest --all
  python scripts/wiki.py status
  python scripts/wiki.py list-raw
"""

import sys
from pathlib import Path
from typing import Optional

import click

# scripts/ 디렉토리를 sys.path에 추가 (상대 import용)
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    is_ingested,
    list_raw_files,
    vault_path,
    wiki_dir,
)


@click.group()
def cli():
    """LLM Wiki 운영 CLI"""


# ── ingest ────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("source_file", required=False)
@click.option("--all", "ingest_all", is_flag=True, help="raw/ 미처리 파일 전체 ingest")
@click.option("--debug", is_flag=True, help="raw Claude 응답을 /tmp/llm-wiki-debug.txt에 저장")
def ingest(source_file: Optional[str], ingest_all: bool, debug: bool):
    """소스 파일을 wiki로 컴파일합니다."""
    from ingest import run_ingest  # 지연 import (CLI 응답성 유지)

    if ingest_all:
        raw_files = list_raw_files()
        pending = [f for f in raw_files if not is_ingested(f.stem)]

        if not pending:
            click.echo("처리할 새 파일이 없습니다. (모두 이미 ingest됨)")
            return

        click.echo(f"[ingest --all] {len(pending)}개 파일 처리 시작...")
        for i, f in enumerate(pending, 1):
            click.echo(f"\n[{i}/{len(pending)}] {f.name}")
            _run_single(run_ingest, str(f), debug=debug)

    elif source_file:
        path = Path(source_file)
        if not path.is_absolute() and not path.exists():
            candidate = vault_path() / source_file
            if candidate.exists():
                path = candidate
        _run_single(run_ingest, str(path), debug=debug)

    else:
        click.echo("파일을 지정하거나 --all 플래그를 사용하세요.", err=True)
        click.echo("예: wiki ingest raw/article.md", err=True)
        sys.exit(1)


def _run_single(run_ingest_fn, source_file: str, debug: bool = False):
    try:
        result = run_ingest_fn(source_file, debug=debug)
        click.echo(
            f"✓ {result['source']} — "
            f"생성 {result['pages_created']}개, "
            f"갱신 {result['pages_updated']}개"
        )
    except FileNotFoundError as e:
        click.echo(f"✗ 파일 없음: {e}", err=True)
        sys.exit(1)
    except RuntimeError as e:
        click.echo(f"✗ 오류: {e}", err=True)
        sys.exit(1)


# ── query ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("question")
@click.option("--slides", "output_format", flag_value="slides", help="Marp 슬라이드로 출력")
@click.option("--image", "output_format", flag_value="image", help="matplotlib 이미지 코드로 출력")
@click.option("--text", "output_format", flag_value="text", default=True, help="텍스트 마크다운으로 출력 (기본)")
@click.option("--debug", is_flag=True, help="raw Claude 응답을 /tmp/llm-wiki-debug.txt에 저장")
def query(question: str, output_format: str, debug: bool):
    """wiki를 탐색하여 질문에 답합니다."""
    from query import run_query  # 지연 import

    try:
        result = run_query(question, output_format=output_format, debug=debug)
        click.echo(f"\n✓ 답변 저장: {', '.join(result['output_files'])}")
        if result["findings_created"]:
            click.echo(f"✓ Findings 파일링: {result['findings_created']}개")
        click.echo(f"  로그: {result['log_message']}")
    except RuntimeError as e:
        click.echo(f"✗ 오류: {e}", err=True)
        sys.exit(1)


# ── status ────────────────────────────────────────────────────────────────────

@cli.command()
def status():
    """wiki 현황 요약을 출력합니다."""
    w = wiki_dir()

    counts = {}
    for subdir in ["summaries", "entities", "concepts", "findings"]:
        d = w / subdir
        counts[subdir] = len(list(d.glob("*.md"))) if d.exists() else 0

    total = sum(counts.values())
    click.echo("\n=== LLM Wiki 현황 ===")
    click.echo(f"  summaries : {counts['summaries']:>4}개")
    click.echo(f"  concepts  : {counts['concepts']:>4}개")
    click.echo(f"  entities  : {counts['entities']:>4}개")
    click.echo(f"  findings  : {counts['findings']:>4}개")
    click.echo(f"  {'합계':8}: {total:>4}개")

    # 최근 로그 5개
    log_path = w / "log.md"
    if log_path.exists():
        lines = [
            l for l in log_path.read_text(encoding="utf-8").splitlines()
            if l.strip() and l.startswith("[")
        ]
        click.echo("\n=== 최근 로그 ===")
        for line in lines[-5:]:
            click.echo(f"  {line}")
    click.echo()


# ── list-raw ──────────────────────────────────────────────────────────────────

@cli.command("list-raw")
def list_raw():
    """raw/ 파일 목록과 ingest 여부를 출력합니다."""
    files = list_raw_files()
    if not files:
        click.echo("raw/ 폴더가 비어 있습니다.")
        return

    click.echo(f"\n=== raw/ 파일 ({len(files)}개) ===")
    for f in files:
        status_mark = "✓" if is_ingested(f.stem) else "○"
        click.echo(f"  {status_mark} {f.name}")
    click.echo(f"\n  ✓ = 처리됨  ○ = 미처리\n")


if __name__ == "__main__":
    cli()

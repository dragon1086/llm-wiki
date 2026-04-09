#!/usr/bin/env python3
"""LLM Wiki — Discord Bot

사용법:
  DISCORD_TOKEN=your_token ./wiki discord

명령어:
  !query <질문> [--slides|--diagram|--chart|--archive]
  !ingest [파일경로]
  !status
  !help
"""

import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path

import discord
from discord.ext import commands

REPO_ROOT = Path(__file__).parent.parent
WIKI_BIN = REPO_ROOT / "wiki"

# 허용 채널 ID (비어있으면 모든 채널 허용)
# .env에 DISCORD_CHANNEL_IDS=123456,789012 형식으로 설정
_raw_ids = os.environ.get("DISCORD_CHANNEL_IDS", "")
ALLOWED_CHANNELS: set[int] = {int(i) for i in _raw_ids.split(",") if i.strip()}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def run_wiki(*args: str, timeout: int = 300) -> tuple[str, int]:
    """./wiki 실행 후 (stdout, returncode) 반환."""
    result = subprocess.run(
        [str(WIKI_BIN), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO_ROOT),
    )
    output = result.stdout + (f"\n⚠️ {result.stderr}" if result.returncode != 0 else "")
    return output.strip(), result.returncode


def parse_output_path(stdout: str) -> Path | None:
    """stdout에서 '✓ 답변 저장: /path/to/file' 경로 추출."""
    m = re.search(r"✓ 답변 저장: (.+?)(?:\n|$)", stdout)
    if m:
        # 여러 파일이면 첫 번째만
        return Path(m.group(1).split(",")[0].strip())
    return None


def channel_allowed(ctx) -> bool:
    return not ALLOWED_CHANNELS or ctx.channel.id in ALLOWED_CHANNELS


async def send_result(ctx, stdout: str, returncode: int):
    """결과를 Discord로 전송. 길면 파일 첨부."""
    if returncode != 0:
        await ctx.send(f"❌ 오류:\n```\n{stdout[:1800]}\n```")
        return

    output_path = parse_output_path(stdout)

    # PNG 이미지 (--chart)
    if output_path:
        png = output_path.with_suffix(".png")
        if png.exists():
            await ctx.send(
                f"📊 차트 생성 완료",
                file=discord.File(str(png), filename=png.name),
            )
            return

    # .md 파일 내용 전송
    if output_path and output_path.exists() and output_path.suffix == ".md":
        content = output_path.read_text(encoding="utf-8")
        if len(content) <= 1900:
            await ctx.send(f"```markdown\n{content}\n```")
        else:
            # 2000자 초과 → 파일 첨부
            await ctx.send(
                f"📄 결과 파일",
                file=discord.File(str(output_path), filename=output_path.name),
            )
        return

    # fallback: stdout 그대로
    msg = stdout[:1900] if stdout else "✅ 완료"
    await ctx.send(msg)


# ── 이벤트 ────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"[discord_bot] 로그인: {bot.user} (ID: {bot.user.id})")
    if ALLOWED_CHANNELS:
        print(f"[discord_bot] 허용 채널: {ALLOWED_CHANNELS}")
    else:
        print("[discord_bot] 모든 채널에서 응답")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"❌ {error}")


# ── 명령어 ────────────────────────────────────────────────────────────────────

@bot.command(name="query", aliases=["q"])
async def cmd_query(ctx, *, args: str = ""):
    """wiki 질의. 예: !query 트랜스포머 어텐션이 뭐야? --diagram"""
    if not channel_allowed(ctx):
        return
    if not args:
        await ctx.send("사용법: `!query <질문> [--slides|--diagram|--chart|--archive]`")
        return

    # 플래그와 질문 분리
    flags = []
    question_parts = []
    for token in args.split():
        if token.startswith("--"):
            flags.append(token)
        else:
            question_parts.append(token)
    question = " ".join(question_parts)

    if not question:
        await ctx.send("질문을 입력해주세요.")
        return

    msg = await ctx.send(f"🔍 `{question[:60]}` 탐색 중...")
    try:
        stdout, rc = await asyncio.get_event_loop().run_in_executor(
            None, lambda: run_wiki("query", question, *flags)
        )
    except subprocess.TimeoutExpired:
        await msg.edit(content="⏱️ 타임아웃 (300초 초과)")
        return

    await msg.delete()
    await send_result(ctx, stdout, rc)


@bot.command(name="ingest", aliases=["i"])
async def cmd_ingest(ctx, filepath: str = ""):
    """raw/ ingest. 예: !ingest  또는  !ingest raw/article.md"""
    if not channel_allowed(ctx):
        return

    args = [filepath] if filepath else []
    msg = await ctx.send("⚙️ ingest 중...")
    try:
        stdout, rc = await asyncio.get_event_loop().run_in_executor(
            None, lambda: run_wiki("ingest", *args)
        )
    except subprocess.TimeoutExpired:
        await msg.edit(content="⏱️ 타임아웃")
        return

    await msg.delete()
    icon = "✅" if rc == 0 else "❌"
    await ctx.send(f"{icon} {stdout[:1800]}")


@bot.command(name="status", aliases=["s"])
async def cmd_status(ctx):
    """wiki 현황 요약."""
    if not channel_allowed(ctx):
        return

    stdout, rc = await asyncio.get_event_loop().run_in_executor(
        None, lambda: run_wiki("status")
    )
    icon = "📚" if rc == 0 else "❌"
    await ctx.send(f"{icon}\n```\n{stdout[:1800]}\n```")


@bot.command(name="help", aliases=["h"])
async def cmd_help(ctx):
    """명령어 목록."""
    if not channel_allowed(ctx):
        return

    embed = discord.Embed(title="LLM Wiki Bot", color=0x5865F2)
    embed.add_field(
        name="질의",
        value=(
            "`!query <질문>` — 텍스트 답변\n"
            "`!query <질문> --slides` — Marp 슬라이드\n"
            "`!query <질문> --diagram` — Mermaid 다이어그램\n"
            "`!query <질문> --chart` — 차트 PNG\n"
            "`!query <질문> --archive` — 결과를 wiki에 자동 편입\n"
        ),
        inline=False,
    )
    embed.add_field(
        name="관리",
        value=(
            "`!ingest` — raw/ 미처리 파일 전체 ingest\n"
            "`!ingest raw/file.md` — 단일 파일 ingest\n"
            "`!status` — wiki 페이지 수 + 최근 로그\n"
        ),
        inline=False,
    )
    await ctx.send(embed=embed)


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("DISCORD_TOKEN", "")
    if not token:
        # .env에서 로드 시도
        env_file = REPO_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("DISCORD_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break

    if not token:
        print("오류: DISCORD_TOKEN 환경변수를 설정하세요.", file=sys.stderr)
        print("  export DISCORD_TOKEN=your_bot_token", file=sys.stderr)
        print("  또는 .env 파일에 DISCORD_TOKEN=your_bot_token 추가", file=sys.stderr)
        sys.exit(1)

    print(f"[discord_bot] 시작 중... (wiki: {WIKI_BIN})")
    bot.run(token)


if __name__ == "__main__":
    main()

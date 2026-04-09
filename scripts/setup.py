#!/usr/bin/env python3
"""LLM Wiki — 초기 설정 스크립트

config.yaml.example을 복사하고 vault_path를 대화형으로 설정합니다.
vault_path 디렉토리 구조도 자동으로 생성합니다.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CONFIG_EXAMPLE = REPO_ROOT / "config.yaml.example"
CONFIG_PATH = REPO_ROOT / "config.yaml"


def main():
    print("=== LLM Wiki 초기 설정 ===\n")

    # config.yaml 이미 존재하면 확인
    if CONFIG_PATH.exists():
        ans = input("config.yaml이 이미 존재합니다. 덮어쓰시겠습니까? [y/N] ").strip().lower()
        if ans != "y":
            print("설정을 유지합니다.")
            return

    # vault_path 입력
    default_vault = Path.home() / "obsidian-vault_path" / "llm-wiki"
    print(f"Obsidian vault_path 경로를 입력하세요.")
    print(f"기본값: {default_vault}")
    user_input = input("vault_path [Enter = 기본값]: ").strip()
    vault_path = Path(user_input).expanduser() if user_input else default_vault

    # config.yaml 생성
    with open(CONFIG_EXAMPLE, "r", encoding="utf-8") as f:
        config_text = f.read()

    # vault_path 라인 교체 (주석 제거)
    lines = []
    for line in config_text.splitlines():
        if line.startswith("vault_path:"):
            lines.append(f"vault_path: {vault_path}")
        else:
            lines.append(line)
    config_text = "\n".join(lines) + "\n"

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(config_text)
    print(f"\n✓ config.yaml 생성 완료")

    # vault_path 디렉토리 구조 생성
    subdirs = [
        "raw",
        "raw/trending",
        "wiki",
        "wiki/concepts",
        "wiki/entities",
        "wiki/summaries",
        "wiki/findings",
        "output",
    ]
    for d in subdirs:
        (vault_path / d).mkdir(parents=True, exist_ok=True)
    print(f"✓ vault_path 디렉토리 생성: {vault_path}")

    # wiki/index.md, wiki/log.md 초기화
    index_path = vault_path / "wiki" / "index.md"
    if not index_path.exists():
        index_path.write_text(
            "---\ntotal_pages: 0\ntotal_summaries: 0\ntotal_concepts: 0\n"
            "total_entities: 0\ntotal_findings: 0\nupdated: \"\"\n---\n\n"
            "# LLM Wiki Index\n\n## Summaries\n\n## Concepts\n\n## Entities\n\n## Findings\n",
            encoding="utf-8",
        )
        print("✓ wiki/index.md 초기화")

    log_path = vault_path / "wiki" / "log.md"
    if not log_path.exists():
        log_path.write_text("# LLM Wiki Log\n", encoding="utf-8")
        print("✓ wiki/log.md 초기화")

    # venv 확인
    venv_path = REPO_ROOT / ".venv"
    if not venv_path.exists():
        print("\n.venv가 없습니다. 가상환경을 생성합니다...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        pip = venv_path / "bin" / "pip"
        subprocess.run([str(pip), "install", "-r", str(REPO_ROOT / "requirements.txt")], check=True)
        print("✓ .venv 생성 및 패키지 설치 완료")

    print(f"""
=== 설정 완료 ===

다음 단계:
  1. Obsidian 앱 → Open folder as vault_path → {vault_path}
  2. 자료를 {vault_path / 'raw'}/ 에 넣기
  3. ./wiki ingest       ← wiki 생성
  4. ./wiki query "질문" ← 질의
""")


if __name__ == "__main__":
    main()

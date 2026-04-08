#!/usr/bin/env python3
"""README용 이미지 생성 — gemini-3.1-flash-image-preview"""

import base64
import json
import os
import sys
from pathlib import Path

import requests

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-3.1-flash-image-preview"
BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
OUT_DIR = Path(__file__).parent.parent / "assets" / "images"

IMAGES = [
    {
        "name": "hero-banner.png",
        "prompt": (
            "Create a wide hero banner (1200x400px) for an open-source project called 'LLM Wiki'. "
            "Dark navy/black background. Left side: elegant glowing knowledge graph with interconnected nodes "
            "(some nodes labeled: Concepts, Entities, Summaries, Findings) in electric blue and purple. "
            "Center: bold clean sans-serif text 'LLM Wiki' in white with a subtle blue glow. "
            "Below the title: smaller text 'AI-Powered Personal Knowledge Base'. "
            "Right side: stylized document icons flowing into a brain/graph. "
            "Overall: sleek, modern, minimal tech aesthetic. No busy backgrounds."
        ),
    },
    {
        "name": "architecture.png",
        "prompt": (
            "Create a clean system architecture diagram (1200x600px) for a personal knowledge base pipeline. "
            "Dark background (#1a1a2e). Left-to-right data flow with labeled boxes and arrows: "
            "Step 1 (blue): '📄 Source' box — Web articles, PDFs, notes dropped into raw/ folder. "
            "Arrow → Step 2 (purple): '🤖 Ingest (Claude AI)' box — AI reads and compiles. "
            "Arrow → Step 3 (teal): '🗂 Obsidian Vault' box — structured wiki pages: "
            "Summaries, Concepts, Entities with [[wikilinks]] forming a graph. "
            "Arrow → Step 4 (orange): '🔍 Query' box — ask questions in natural language. "
            "Arrow → Step 5 (green): '📊 Output' box — Markdown answers, slides, charts, findings. "
            "Each box has an icon and label. Arrows show data direction. "
            "Bottom: small note 'log.md tracks all operations'. "
            "Professional infographic style, high information density, clean fonts."
        ),
    },
    {
        "name": "query-improvement.png",
        "prompt": (
            "Create a technical comparison diagram (1200x500px) showing query retrieval improvement. "
            "Dark background. Two panels side by side with a 'VS' divider: "
            "LEFT panel labeled 'Before: Keyword Slug Matching' (red tint): "
            "A flat list of 15 document icons, 5 highlighted as matched (green checkmark), "
            "10 grayed out as missed. Shows text: 'score = keywords ∩ slug_name'. "
            "Small label: 'Misses pages with relevant content but wrong slug name'. "
            "RIGHT panel labeled 'After: BFS Graph Traversal' (green tint): "
            "A node graph — 8 blue seed nodes matched by keyword, "
            "with dashed expansion arrows reaching 12+ green neighbor nodes via [[wikilinks]]. "
            "Nodes sorted by connection count (degree). Shows text: "
            "'Seed → expand via [[wikilinks]] → rank by connectivity'. "
            "Small label: 'Finds related pages even without direct keyword match'. "
            "Bottom: char_budget bar showing dynamic token allocation. "
            "Clean technical illustration, informative, readable fonts."
        ),
    },
]


def generate_image(name: str, prompt: str) -> bool:
    print(f"  → 생성 중: {name} ...", end="", flush=True)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "thinkingConfig": {"thinkingBudget": 1024},
        },
    }
    try:
        r = requests.post(
            f"{BASE_URL}?key={API_KEY}",
            json=payload,
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.HTTPError as e:
        print(f" FAIL — {e}")
        print(f"     응답: {e.response.text[:300]}")
        return False
    except Exception as e:
        print(f" FAIL — {e}")
        return False

    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            img_bytes = base64.b64decode(part["inlineData"]["data"])
            out_path = OUT_DIR / name
            out_path.write_bytes(img_bytes)
            print(f" OK ({len(img_bytes)//1024}KB → {out_path.relative_to(Path.cwd())})")
            return True

    print(f" FAIL — 이미지 없음. 응답:\n{json.dumps(data, ensure_ascii=False)[:400]}")
    return False


def main():
    if not API_KEY:
        print("GEMINI_API_KEY 환경변수를 설정하세요.")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"이미지 생성 시작 ({len(IMAGES)}개) → {OUT_DIR}\n")

    results = []
    for img in IMAGES:
        ok = generate_image(img["name"], img["prompt"])
        results.append((img["name"], ok))

    print(f"\n{'='*40}")
    for name, ok in results:
        mark = "✓" if ok else "✗"
        print(f"  {mark} {name}")
    failed = sum(1 for _, ok in results if not ok)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

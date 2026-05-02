#!/usr/bin/env python3
"""
Narrator layer: rewrites why_picked blurbs in Emily's voice using Claude.

Makes a single batched Anthropic API call for all restaurants in a response,
so latency cost is one round-trip regardless of how many results are returned.
Falls back silently to the raw template-generated 'why' on any error.
"""

import json
import os
from typing import Optional

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

_client: Optional[AsyncAnthropic] = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _client = AsyncAnthropic(api_key=api_key)
    return _client


SYSTEM_PROMPT = (
    "You write short restaurant recommendation blurbs for a personal app called "
    "'Curated for You'. The voice is Emily's — warm, casual, first-person, like a "
    "text from a food-obsessed friend. Rules:\n"
    "- ≤15 words per blurb\n"
    "- First-person when it adds authenticity ('I loved the pasta here'), "
    "third-person vibe otherwise ('perfect for a low-key date night')\n"
    "- Draw only from the raw_why and personal note — don't invent facts\n"
    "- No filler: 'a great match', 'you'll love it', 'highly recommend'\n"
    "- If status is 'want_to_try', keep it honest ('on my list forever')\n"
    "- End without a period so it reads like a caption, not a sentence"
)


async def narrate_results(results: list[dict], query: str) -> list[dict]:
    """
    Rewrite the 'why' field for each result in Emily's voice.

    Accepts the enriched result dicts (must have 'name', 'why', 'status';
    optionally 'your_note'). Returns a new list with 'why' and 'why_picked'
    updated. Falls back to the original values on any error.
    """
    if not results:
        return results

    client = _get_client()

    # Build compact input for the prompt
    items = [
        {
            "index": i,
            "name": r.get("name", ""),
            "raw_why": r.get("why", "") or "",
            "note": (r.get("your_note") or r.get("note") or "").strip(),
            "status": r.get("status", ""),
        }
        for i, r in enumerate(results)
    ]

    user_prompt = (
        f'User query: "{query}"\n\n'
        "Rewrite each restaurant's blurb in Emily's voice using the raw_why and note "
        "as your only source material.\n\n"
        f"Restaurants:\n{json.dumps(items, indent=2)}\n\n"
        'Return ONLY a JSON array: [{"index": 0, "why_picked": "..."}]'
    )

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = response.content[0].text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(
                line for line in lines if not line.startswith("```")
            ).strip()

        narrated: list[dict] = json.loads(text)
        idx_map = {item["index"]: item["why_picked"] for item in narrated}

        updated = []
        for i, r in enumerate(results):
            if i in idx_map and idx_map[i]:
                narrated_why = idx_map[i]
                updated.append({**r, "why": narrated_why, "why_picked": narrated_why})
            else:
                updated.append(r)

        return updated

    except Exception as exc:
        print(f"[narrator] fallback (error: {exc})")
        return results

"""Run a local route request through the FastAPI app.

Use a login shell when checking real Qwen routing so VLM_* variables from
~/.zshrc are available, for example:
zsh -lic 'python scripts/check_vlm_route.py 400A 429B'
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.app.main import app


async def request_route(args: argparse.Namespace) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://local") as client:
        response = await client.post(
            "/api/v1/route",
            json={
                "from_location": args.start,
                "to_location": args.destination,
                "language": args.language,
                "accessible_only": args.accessible_only,
            },
        )
    print(f"status={response.status_code}")
    body = response.json()
    if response.status_code >= 400:
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return
    summary = {
        "planner": body.get("planner"),
        "from_id": body.get("from_id"),
        "to_id": body.get("to_id"),
        "total_distance_m": body.get("total_distance_m"),
        "confidence": body.get("confidence"),
        "announcement": body.get("announcement"),
        "steps_count": len(body.get("steps", [])),
        "assumptions": body.get("assumptions", []),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for index, step in enumerate(body.get("steps", [])[:6], 1):
        print(
            f"{index}. {step.get('from_id')} -> {step.get('to_id')} "
            f"({step.get('distance_m')}m): {step.get('instruction')}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("start", help="Start location, node ID or alias, for example 400A")
    parser.add_argument("destination", help="Destination, node ID or alias, for example 429B")
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    parser.add_argument("--accessible-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    asyncio.run(request_route(parse_args()))


if __name__ == "__main__":
    main()

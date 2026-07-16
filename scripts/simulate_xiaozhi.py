"""Simulate the Xiaozhi museum tools without a physical development board."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default="")
    parser.add_argument("--device-id", default="SIMULATED-XIAOZHI-001")
    parser.add_argument("--client-id", default="simulator")
    parser.add_argument("--image", type=Path)
    parser.add_argument("--floor", type=int)
    parser.add_argument("--visual-text", default="李政道科学与艺术大奖赛历年主题画展")
    parser.add_argument("--destination", default="LB-3F-ROOM-300")
    args = parser.parse_args()

    headers = {
        "Device-Id": args.device_id,
        "Client-Id": args.client_id,
        "Firmware-Version": "simulator-1.0",
    }
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    with httpx.Client(base_url=args.base_url, headers=headers, timeout=60) as client:
        capability = client.get("/api/device/v1/capabilities")
        capability.raise_for_status()
        print("CAPABILITIES", json.dumps(capability.json(), ensure_ascii=False))

        if args.image:
            content_type = "image/png" if args.image.suffix.lower() == ".png" else "image/jpeg"
            with args.image.open("rb") as file:
                localized = client.post(
                    "/api/device/v1/localize/image",
                    files={"image": (args.image.name, file, content_type)},
                    data={} if args.floor is None else {"floor_hint": str(args.floor)},
                )
        else:
            localized = client.post(
                "/api/device/v1/localize/visual",
                json={
                    "recognized_texts": [args.visual_text],
                    "floor_hint": args.floor,
                },
            )
        localized.raise_for_status()
        print("LOCALIZE", json.dumps(localized.json(), ensure_ascii=False))
        if localized.json().get("status") != "matched":
            return

        route = client.post(
            "/api/device/v1/route",
            json={"to_location": args.destination, "language": "zh"},
        )
        route.raise_for_status()
        print("ROUTE", json.dumps(route.json(), ensure_ascii=False))
        print("SPEAK", route.json()["announcement"])


if __name__ == "__main__":
    main()

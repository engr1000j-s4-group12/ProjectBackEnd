"""Import the unique Lee science-and-art exhibition photos from DevData.

Floor-directory photographs are intentionally excluded. Images are attached to
the seeded 3F exhibition record and processed once by the configured VLM.
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.app.main import app


EXHIBITION_MESSAGE_IDS = {
    "127483001822761347",
    "3980914653975395355",
    "2796655239934525457",
    "109603720975071387",
    "1104641841252668056",
    "1060686457226783358",
    "8898803811118357204",
    "1661103641822275303",
}


def exhibition_images() -> list[Path]:
    images: list[Path] = []
    seen: set[bytes] = set()
    for path in sorted((ROOT / "DevData").glob("*.jpg")):
        if not any(f"MsgID={message_id}" in path.name for message_id in EXHIBITION_MESSAGE_IDS):
            continue
        content = path.read_bytes()
        if content in seen:
            continue
        seen.add(content)
        images.append(path)
    return images


async def main() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://local") as client:
        bootstrap = (await client.get("/api/admin/bootstrap")).json()
        record = next(
            item
            for item in bootstrap["entries"]
            if item["node_id"] == "LB-3F-EVENT-LEE-ART"
        )
        images = exhibition_images()
        print(f"record_id={record['id']} images={len(images)}")
        for index, path in enumerate(images, 1):
            content = path.read_bytes()
            response = await client.post(
                f"/api/admin/entries/{record['id']}/media",
                params={"run_vlm": True},
                files={"file": (path.name, content, "image/jpeg")},
            )
            if response.status_code == 409:
                digest = hashlib.sha256(content).hexdigest()
                existing = (
                    await client.get(f"/api/admin/entries/{record['id']}/media")
                ).json()["media"]
                media = next(item for item in existing if item["sha256"] == digest)
                response = await client.post(
                    f"/api/admin/media/{media['id']}/retry-vlm"
                )
                response.raise_for_status()
                media = response.json()["media"]
                print(
                    f"{index}/{len(images)} media_id={media['id']} "
                    f"vlm={media['vlm_status']} retried"
                )
                continue
            response.raise_for_status()
            media = response.json()["media"]
            print(f"{index}/{len(images)} media_id={media['id']} vlm={media['vlm_status']}")


if __name__ == "__main__":
    asyncio.run(main())

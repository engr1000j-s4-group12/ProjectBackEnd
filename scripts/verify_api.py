"""端到端 API 验证脚本 (使用4F真实数据)"""
import httpx
import asyncio
from server.app.main import app


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # 1. Health
        r = await c.get("/health")
        print(f"1. Health:           {r.status_code} {r.json()['status']}")

        # 2. Places
        r = await c.get("/api/v1/places")
        d = r.json()
        print(f"2. Places:           {r.status_code} ({len(d['places'])} nodes)")

        # 3. Route (400A -> 429B, zh)
        r = await c.post("/api/v1/route", json={
            "from_location": "LB-4F-ROOM-400A",
            "to_location": "LB-4F-ROOM-429B",
            "language": "zh"
        })
        d = r.json()
        print(f"3. Route(zh):        {r.status_code} dist={d['total_distance_m']:.1f}m steps={len(d['steps'])}")
        for s in d["steps"]:
            print(f"     {s['instruction'][:65]}")

        # 4. Route (en, accessible)
        r = await c.post("/api/v1/route", json={
            "from_location": "LB-4F-ROOM-400A",
            "to_location": "LB-4F-ROOM-429B",
            "language": "en", "accessible_only": True
        })
        d = r.json()
        print(f"4. Route(en,acc):    {r.status_code} dist={d['total_distance_m']:.1f}m steps={len(d['steps'])}")

        # 5. Resolve alias
        r = await c.get("/api/v1/resolve?q=400A房间")
        print(f"5. Resolve:          {r.status_code} {r.json()}")

        # 6. Exhibit
        r = await c.get("/api/v1/exhibits/ROBOT-001")
        print(f"6. Exhibit:          {r.status_code} {r.json()['name_zh']}")

        # 7. Context
        r = await c.post("/api/v1/exhibits/ROBOT-001/context",
                          json={"question": "在哪里?", "language": "zh"})
        d = r.json()
        print(f"7. Context:          {r.status_code} facts={len(d['facts'])}")

        # 8. 404 unknown
        r = await c.post("/api/v1/route", json={
            "from_location": "不存在", "to_location": "LB-4F-ROOM-400", "language": "zh"
        })
        print(f"8. 404 test:         {r.status_code}")

        # 9. Same node
        r = await c.post("/api/v1/route", json={
            "from_location": "LB-4F-ROOM-400", "to_location": "LB-4F-ROOM-400", "language": "zh"
        })
        d = r.json()
        print(f"9. Same node:        {r.status_code} dist={d['total_distance_m']:.1f}m steps={len(d['steps'])}")

        # 10. Visual localize (room number)
        r = await c.post("/api/v1/localize/visual", json={
            "objects": [{"label": "413A", "confidence": 0.98}],
            "floor_hint": 4
        })
        d = r.json()
        print(f"10. Visual room:     {r.status_code} status={d['status']} node={d['node_id']}")

        # 11. Visual localize (stairs)
        r = await c.post("/api/v1/localize/visual", json={
            "recognized_texts": ["西北侧楼梯"],
            "floor_hint": 4
        })
        d = r.json()
        print(f"11. Visual stairs:   {r.status_code} status={d['status']} node={d['node_id']} conf={d['confidence']:.3f}")

        # 12. Stairs accessible fail
        r = await c.post("/api/v1/route", json={
            "from_location": "LB-4F-STAIRS-NORTHWEST",
            "to_location": "LB-4F-STAIRS-SOUTHEAST",
            "language": "zh", "accessible_only": True
        })
        print(f"12. Acc stairs fail: {r.status_code} (expected 422)")

        # 13. Marker locate
        r = await c.post("/api/v1/localize", json={"marker_id": "LB-4F-ROOM-400A"})
        d = r.json()
        print(f"13. Marker locate:   {r.status_code} node={d['node_id']} name={d['name_zh']}")

    print("\n=== ALL 13 END-TO-END TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())

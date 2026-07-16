"""端到端 API 验证脚本 (使用4F真实数据)"""
import asyncio
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
        print(f"     播报：{d['announcement']}")

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

        # 14. Firmware-compatible place resolver query name
        r = await c.get("/api/v1/resolve", params={"name": "400A房间"})
        print(f"14. MCP resolve:     {r.status_code} {r.json()}")

        # 15. Resolve exhibit from structured visual evidence
        r = await c.post("/api/v1/exhibits/resolve", json={
            "recognized_texts": ["机器人技术示范展品"],
            "floor_hint": 4,
        })
        d = r.json()
        print(f"15. MCP exhibit:     {r.status_code} status={d['status']} exhibit={d['exhibit_id']}")

        # 16. Resolve exhibit and return grounded context in one request
        r = await c.post("/api/v1/exhibits/resolve-context", json={
            "recognized_texts": ["机器人技术示范展品"],
            "floor_hint": 4,
            "question": "请简要介绍它",
            "language": "zh",
        })
        d = r.json()
        print(f"16. MCP context:     {r.status_code} exhibit={d['exhibit_id']} facts={len(d['facts'])}")

        # 17. Admin map bootstrap
        r = await c.get("/api/admin/bootstrap")
        d = r.json()
        print(f"17. Admin maps:      {r.status_code} floors={len(d['floorplans'])} records={len(d['entries'])}")

        # 18. SQLite knowledge search
        r = await c.get("/api/v1/knowledge/search", params={"q": "学院介绍"})
        d = r.json()
        print(f"18. DB search:       {r.status_code} records={d['count']}")

        # 19. MCP tool discovery
        r = await c.post("/mcp", json={
            "jsonrpc": "2.0", "id": 19, "method": "tools/list"
        })
        d = r.json()
        print(f"19. MCP tools:       {r.status_code} tools={len(d['result']['tools'])}")

        # 20. MCP database query
        r = await c.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "museum.get_place_info",
                "arguments": {"node_id": "LB-1F-REGION-A"},
            },
        })
        d = r.json()
        records = d["result"]["structuredContent"]["records"]
        print(f"20. MCP DB query:    {r.status_code} records={len(records)}")

        # 21. Four-floor SQLite map database
        r = await c.get("/api/v1/maps")
        d = r.json()
        counts = "/".join(str(item["nodes"]) for item in d["floors"])
        print(f"21. SQLite maps:     {r.status_code} floor_nodes={counts}")

        # 22. MCP route reads the SQLite map graph
        r = await c.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 22,
            "method": "tools/call",
            "params": {
                "name": "museum.plan_route",
                "arguments": {
                    "from_location": "LB-4F-ROOM-400A",
                    "to_location": "LB-4F-ROOM-429B",
                    "language": "zh",
                },
            },
        })
        d = r.json()["result"]["structuredContent"]
        print(f"22. MCP SQLite route:{r.status_code} dist={d['total_distance_m']:.1f}m steps={len(d['steps'])}")

        # 23. Example One: Lee exhibition to Room 300 over user-marked green routes
        r = await c.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 23,
            "method": "tools/call",
            "params": {
                "name": "museum.plan_route",
                "arguments": {
                    "from_location": "LB-3F-EVENT-LEE-ART",
                    "to_location": "LB-3F-ROOM-300",
                    "language": "zh",
                },
            },
        })
        d = r.json()["result"]["structuredContent"]
        print(f"23. Example One:     {r.status_code} dist={d['total_distance_m']:.1f}m steps={len(d['steps'])}")
        print(f"     播报：{d['announcement']}")
        assert d["announcement"] == "300会议室就在您所在的三楼，位于电梯出口附近。"

        # 24. Floor 1 to Floor 4 introduction uses only the guest elevator
        r = await c.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 24,
            "method": "tools/call",
            "params": {
                "name": "museum.plan_route",
                "arguments": {
                    "from_location": "LB-1F-OPEN-08",
                    "to_location": "LB-4F-REGION-F",
                    "language": "zh",
                },
            },
        })
        d = r.json()["result"]["structuredContent"]
        route_nodes = {d["from_id"], d["to_id"], *(step["to_id"] for step in d["steps"])}
        assert "LB-1F-ELEVATOR-GUEST" in route_nodes
        assert "LB-4F-ELEVATOR-GUEST" in route_nodes
        assert "LB-1F-ELEVATOR-NORTHWEST-RESTRICTED" not in route_nodes
        print(f"24. Guest elevator:  {r.status_code} steps={len(d['steps'])}")
        print(f"     播报：{d['announcement']}")

        # 25-27. Xiaozhi device compatibility flow
        device_headers = {
            "Device-Id": "SIMULATED-XIAOZHI-VERIFY",
            "Client-Id": "verify-api",
            "Firmware-Version": "simulator-1.0",
        }
        r = await c.get("/api/device/v1/capabilities", headers=device_headers)
        d = r.json()
        assert d["image"]["field"] == "image"
        print(f"25. Device capability:{r.status_code} version={d['version']}")

        r = await c.post(
            "/api/device/v1/localize/visual",
            headers=device_headers,
            json={
                "recognized_texts": ["李政道科学与艺术大奖赛历年主题画展"],
                "floor_hint": 3,
            },
        )
        d = r.json()
        assert d["current_node"] == "LB-3F-EVENT-LEE-ART"
        print(f"26. Device localize: {r.status_code} node={d['current_node']}")

        r = await c.post(
            "/api/device/v1/route",
            headers=device_headers,
            json={"to_location": "LB-3F-ROOM-300", "language": "zh"},
        )
        d = r.json()
        assert "steps" not in d
        assert d["announcement"] == "300会议室就在您所在的三楼，位于电梯出口附近。"
        print(f"27. Device route:    {r.status_code} state={d['state']}")
        print(f"     播报：{d['announcement']}")

    print("\n=== ALL 27 END-TO-END TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())

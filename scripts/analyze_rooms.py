"""分析4F房间位置分布"""
import json

d = json.load(open("data/building_map.json", "r", encoding="utf-8"))
rooms = [n for n in d["nodes"] if n.get("source") == "龙宾楼4楼楼层索引图" and n["kind"] == "room"]

# Sort by position
rooms.sort(key=lambda r: (r["position"]["y_m"], r["position"]["x_m"]))

print("=== 北侧房间 (y < 16) ===")
for r in rooms:
    y = r["position"]["y_m"]
    if y < 16:
        print(f"  {r['id']:25s} ({r['position']['x_m']:6.1f}, {y:6.1f})")

print("\n=== 中部房间 (16 <= y < 40) ===")
for r in rooms:
    y = r["position"]["y_m"]
    if 16 <= y < 40:
        print(f"  {r['id']:25s} ({r['position']['x_m']:6.1f}, {y:6.1f})")

print("\n=== 中南部房间 (40 <= y < 60) ===")
for r in rooms:
    y = r["position"]["y_m"]
    if 40 <= y < 60:
        print(f"  {r['id']:25s} ({r['position']['x_m']:6.1f}, {y:6.1f})")

print("\n=== 南侧房间 (y >= 60) ===")
for r in rooms:
    y = r["position"]["y_m"]
    if y >= 60:
        print(f"  {r['id']:25s} ({r['position']['x_m']:6.1f}, {y:6.1f})")

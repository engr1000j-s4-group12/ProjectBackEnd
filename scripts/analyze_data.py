"""分析 building_map.json 数据"""
import json
from pathlib import Path

d = json.load(open(Path(__file__).resolve().parent.parent / "data" / "building_map.json", "r", encoding="utf-8"))
nodes = d["nodes"]
edges = d["edges"]

# 节点类型统计
kinds = {}
for n in nodes:
    k = n["kind"]
    kinds[k] = kinds.get(k, 0) + 1

print("=== 节点类型统计 ===")
for k, v in sorted(kinds.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

print(f"\n总节点: {len(nodes)}, 总边: {len(edges)}")

# 真实节点
real = [n for n in nodes if n.get("source") == "龙宾楼4楼楼层索引图"]
print(f"\n=== 4F真实节点: {len(real)} ===")

# Demo节点
demo = [n for n in nodes if isinstance(n.get("remark"), str) and n["remark"].startswith("演示数据")]
print(f"\n=== Demo节点: {len(demo)} ===")
for n in demo:
    print(f"  {n['id']} floor={n['floor']} kind={n['kind']}")

# 所有边
print(f"\n=== 所有边 ({len(edges)}) ===")
for e in edges:
    print(f"  {e['from']} -> {e['to']} ({e['distance_m']}m, acc={e.get('accessible', True)})")

# 4F 关键节点 (非room类型)
print("\n=== 4F 非房间节点 (用于构建路径) ===")
for n in nodes:
    if n.get("source") == "龙宾楼4楼楼层索引图" and n["kind"] != "room":
        pos = n.get("position", {})
        print(f"  {n['id']} kind={n['kind']} pos=({pos.get('x_m','?')}, {pos.get('y_m','?')})")

# 房间节点按位置分布
print("\n=== 4F 房间节点的y坐标分布 ===")
rooms = [n for n in nodes if n.get("source") == "龙宾楼4楼楼层索引图" and n["kind"] == "room"]
y_buckets = {}
for r in rooms:
    y = r.get("position", {}).get("y_m", 0)
    bucket = round(y / 10) * 10
    y_buckets.setdefault(bucket, []).append(r["id"])
for b in sorted(y_buckets.keys()):
    print(f"  y~{b}: {len(y_buckets[b])} rooms - {y_buckets[b][:5]}...")

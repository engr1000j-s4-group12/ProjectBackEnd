from __future__ import annotations

import argparse

from common import load_map, matches


def score_node(node: dict, observations: list[str], floor_hint: int | None) -> tuple[float, list[str]]:
    if floor_hint is not None and node["floor"] != floor_hint:
        return 0.0, []
    landmarks = node.get("visual_landmarks", [])
    if not landmarks:
        return 0.0, []

    total_weight = sum(float(item.get("weight", 1)) for item in landmarks)
    matched_weight = 0.0
    matched_features: list[str] = []
    for landmark in landmarks:
        aliases = landmark["aliases"]
        for observation in observations:
            if any(matches(alias, observation) for alias in aliases):
                matched_weight += float(landmark.get("weight", 1))
                matched_features.append(observation)
                break
    return matched_weight / total_weight if total_weight else 0.0, matched_features


def main() -> None:
    parser = argparse.ArgumentParser(description="用文字证据模拟视觉定位。")
    parser.add_argument("--text", action="append", default=[], help="VLM/OCR 识别出的文字或物体")
    parser.add_argument("--floor", type=int, default=4)
    args = parser.parse_args()

    observations = args.text or ["413A"]
    map_data = load_map()
    candidates = []
    for node in map_data["nodes"]:
        score, matched = score_node(node, observations, args.floor)
        if score > 0:
            candidates.append((score, node, matched))
    candidates.sort(key=lambda item: (-item[0], item[1]["id"]))

    print("observations:", observations)
    print("floor_hint:", args.floor)
    print("top candidates:")
    for score, node, matched in candidates[:5]:
        print(
            f"- {node['id']} | {node['name_zh']} | score={score:.3f} | matched={matched}"
        )

    if not candidates:
        print("not_found: 视觉证据没有匹配到任何节点")
    elif len(candidates) > 1 and candidates[1][0] >= candidates[0][0] * 0.8:
        print("ambiguous: 前两个候选太接近，应该让用户确认")
    else:
        print("matched:", candidates[0][1]["id"])


if __name__ == "__main__":
    main()

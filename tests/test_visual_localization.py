import unittest

from server.app.repository import GuideRepository
from server.app.schemas import VisualLocalizeRequest, VisualObject
from server.app.visual_localization import VisualLocalizer
from server.app.vlm import VlmClient


class VisualLocalizationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.localizer = VisualLocalizer(GuideRepository())

    def test_room_number_matches(self) -> None:
        """通过识别到的房间号匹配唯一房间。"""
        evidence = VisualLocalizeRequest(
            recognized_texts=["413A"],
            floor_hint=4,
        )
        result = self.localizer.locate(evidence)
        self.assertEqual(result.status, "matched")
        self.assertEqual(result.node_id, "LB-4F-ROOM-413A")

    def test_shared_stairs_feature_is_ambiguous(self) -> None:
        """4F 有 4 处楼梯，仅凭'楼梯'特征应产生歧义。"""
        evidence = VisualLocalizeRequest(
            objects=[VisualObject(label="楼梯", confidence=0.95)]
        )
        result = self.localizer.locate(evidence)
        # 多个楼梯节点都有"楼梯" landmark，应匹配到多个候选
        self.assertGreater(len(result.candidates), 1,
                           "多个节点共享'楼梯'特征，应产生多个候选")

    def test_stairs_with_floor_hint_narrows_down(self) -> None:
        """加上楼层提示后应在 4F 楼梯中匹配。"""
        evidence = VisualLocalizeRequest(
            objects=[VisualObject(label="楼梯", confidence=0.95)],
            floor_hint=4,
        )
        result = self.localizer.locate(evidence)
        self.assertEqual(result.status, "ambiguous")  # 4F 仍有多个楼梯
        self.assertGreater(len(result.candidates), 1)

    def test_unique_stairs_name_matches(self) -> None:
        """使用唯一名称（西北侧楼梯）在4F多个楼梯中应产生候选并包含NW楼梯。"""
        evidence = VisualLocalizeRequest(
            recognized_texts=["西北侧楼梯"],
            floor_hint=4,
        )
        result = self.localizer.locate(evidence)
        # "西北侧楼梯" 包含 "楼梯"，4F 有多个楼梯共享此特征 → 歧义
        self.assertGreater(len(result.candidates), 1)
        candidate_ids = {c.node_id for c in result.candidates}
        self.assertIn("LB-4F-STAIRS-NORTHWEST", candidate_ids)

    def test_unknown_scene_is_not_found(self) -> None:
        evidence = VisualLocalizeRequest(
            objects=[VisualObject(label="绿色盆栽", confidence=0.99)]
        )
        result = self.localizer.locate(evidence)
        self.assertEqual(result.status, "not_found")
        self.assertIsNone(result.node_id)

    def test_vlm_json_extraction_accepts_code_fence(self) -> None:
        client = VlmClient()
        value = client._extract_json(
            '```json\n{"objects":[],"recognized_texts":[],"scene_description":""}\n```'
        )
        self.assertEqual(value["objects"], [])


if __name__ == "__main__":
    unittest.main()

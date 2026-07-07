import unittest

from server.app.repository import GuideRepository
from server.app.schemas import VisualLocalizeRequest, VisualObject
from server.app.visual_localization import VisualLocalizer
from server.app.vlm import VlmClient


class VisualLocalizationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.localizer = VisualLocalizer(GuideRepository())

    def test_unique_landmarks_match_lobby(self) -> None:
        evidence = VisualLocalizeRequest(
            objects=[
                VisualObject(label="红色前台", confidence=0.95),
                VisualObject(label="大厅沙发", confidence=0.90),
            ],
            recognized_texts=["学院标志墙"],
            floor_hint=1,
        )
        result = self.localizer.locate(evidence)
        self.assertEqual(result.status, "matched")
        self.assertEqual(result.node_id, "LB-1F-LOBBY")
        self.assertGreater(result.confidence, 0.8)

    def test_shared_feature_is_ambiguous(self) -> None:
        evidence = VisualLocalizeRequest(
            objects=[VisualObject(label="银色电梯门", confidence=0.95)]
        )
        result = self.localizer.locate(evidence)
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.node_id)
        self.assertTrue(result.needs_confirmation)

    def test_floor_hint_resolves_shared_elevator_feature(self) -> None:
        evidence = VisualLocalizeRequest(
            objects=[VisualObject(label="银色电梯门", confidence=0.95)],
            floor_hint=2,
        )
        result = self.localizer.locate(evidence)
        self.assertEqual(result.status, "matched")
        self.assertEqual(result.node_id, "LB-2F-ELEVATOR")
        self.assertTrue(result.needs_confirmation)

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

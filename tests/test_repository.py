import unittest

from server.app.errors import LocationNotFoundError
from server.app.repository import GuideRepository


class RepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = GuideRepository()

    def test_resolves_id_and_alias(self) -> None:
        self.assertEqual(
            self.repository.resolve_location("LB-4F-ROOM-400A"),
            "LB-4F-ROOM-400A",
        )
        self.assertEqual(
            self.repository.resolve_location("400A房间"),
            "LB-4F-ROOM-400A",
        )

    def test_unknown_location_raises(self) -> None:
        with self.assertRaises(LocationNotFoundError):
            self.repository.resolve_location("不存在的地点")

    def test_exhibit_references_known_location(self) -> None:
        exhibit = self.repository.get_exhibit("ROBOT-001")
        self.assertIn(exhibit["location_id"], self.repository.data.nodes)


if __name__ == "__main__":
    unittest.main()

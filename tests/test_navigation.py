import unittest

from server.app.navigation import Navigator
from server.app.repository import GuideRepository


class NavigationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.navigator = Navigator(GuideRepository())

    def test_shortest_route_uses_stairs(self) -> None:
        route = self.navigator.plan("主入口", "机器人", language="zh")
        self.assertEqual(route.from_id, "LB-1F-ENTRANCE")
        self.assertEqual(route.to_id, "EXHIBIT-ROBOT")
        self.assertEqual(route.total_distance_m, 51)
        self.assertEqual(len(route.steps), 5)
        self.assertIn("楼梯", " ".join(step.instruction for step in route.steps))

    def test_accessible_route_uses_elevator(self) -> None:
        route = self.navigator.plan(
            "主入口",
            "机器人",
            language="en",
            accessible_only=True,
        )
        self.assertEqual(route.total_distance_m, 53)
        self.assertIn(
            "elevator",
            " ".join(step.instruction for step in route.steps).lower(),
        )

    def test_same_start_and_destination(self) -> None:
        route = self.navigator.plan("大厅", "大厅")
        self.assertEqual(route.total_distance_m, 0)
        self.assertEqual(route.steps, [])


if __name__ == "__main__":
    unittest.main()

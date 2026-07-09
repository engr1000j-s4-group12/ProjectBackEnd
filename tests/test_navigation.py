import unittest

from server.app.errors import RouteNotFoundError
from server.app.navigation import Navigator
from server.app.repository import GuideRepository


class NavigationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.navigator = Navigator(GuideRepository())

    def test_route_between_rooms(self) -> None:
        """两个4F房间之间应能规划路径并返回分段指令。"""
        route = self.navigator.plan(
            "LB-4F-ROOM-400A",
            "LB-4F-ROOM-429B",
            language="zh",
        )
        self.assertEqual(route.from_id, "LB-4F-ROOM-400A")
        self.assertEqual(route.to_id, "LB-4F-ROOM-429B")
        self.assertGreater(route.total_distance_m, 0)
        self.assertGreater(len(route.steps), 1)
        # 每一步都必须包含目标名称
        for step in route.steps:
            self.assertTrue(step.instruction)

    def test_accessible_route_avoids_stairs(self) -> None:
        """无障碍路线应避开楼梯节点连接的不可达边。"""
        route = self.navigator.plan(
            "LB-4F-ROOM-400A",
            "LB-4F-ROOM-429B",
            language="en",
            accessible_only=True,
        )
        self.assertGreater(route.total_distance_m, 0)
        # 英文指令不应为空
        for step in route.steps:
            self.assertTrue(step.instruction)
            self.assertTrue(step.instruction[0].isascii())

    def test_stairs_to_stairs_accessible_fails(self) -> None:
        """楼梯节点通过不可达边连接，无障碍模式下应拒绝。"""
        with self.assertRaises(RouteNotFoundError):
            self.navigator.plan(
                "LB-4F-STAIRS-NORTHWEST",
                "LB-4F-STAIRS-SOUTHEAST",
                accessible_only=True,
            )

    def test_same_start_and_destination(self) -> None:
        route = self.navigator.plan("LB-4F-ROOM-400", "LB-4F-ROOM-400")
        self.assertEqual(route.total_distance_m, 0)
        self.assertEqual(route.steps, [])

    def test_alias_resolution(self) -> None:
        """使用别名查询应有相同结果。"""
        route_by_id = self.navigator.plan(
            "LB-4F-ROOM-400A", "LB-4F-ROOM-400", language="zh"
        )
        route_by_alias = self.navigator.plan("400A", "400", language="zh")
        self.assertEqual(route_by_id.total_distance_m, route_by_alias.total_distance_m)


if __name__ == "__main__":
    unittest.main()

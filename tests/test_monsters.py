"""Cá Sấu (TICKET-02 mục 1.2): patrol, chase, chạm, recoil, mất hàng LIFO."""

import unittest

from chonoi.contract import load_contract
from chonoi.sim.monsters import MonsterSet

G = load_contract()["tuning"]["gather"]
FAR = [2.0, 0.0]  # người chơi ở bến, ngoài tầm mọi con


def croc(**kw):
    """Một Cá Sấu M1 tuần tra [60,24] <-> [64,24], ghi đè trường theo kw."""
    return dict({"id": "M1", "kind": "ca_sau", "pos": [60, 24], "waypoints": [[60, 24], [64, 24]]}, **kw)


class Spawns(unittest.TestCase):
    def test_day_layout(self):
        self.assertEqual([m["id"] for m in MonsterSet(G, day=1).items], ["M1"])
        self.assertEqual([m["id"] for m in MonsterSet(G, day=3).items], ["M1", "M2"])
        self.assertEqual(MonsterSet(G, fixtures=[]).items, [])

    def test_defaults(self):
        m = MonsterSet(G).items[0]
        self.assertEqual((m["target_idx"], m["state"], m["state_ticks_left"], m["recoil_dir"]), (1, "patrol", 0, None))


class Movement(unittest.TestCase):
    def test_patrol_speed_and_turn_at_waypoint(self):
        ms = MonsterSet(G, fixtures=[croc()])
        for _ in range(60):
            ms.step(FAR)
        self.assertAlmostEqual(ms.items[0]["pos"][0], 61.0)  # 1.0 m/s
        for _ in range(180):
            ms.step(FAR)
        m = ms.items[0]
        self.assertEqual((m["pos"], m["target_idx"]), ([64.0, 24.0], 0))  # tới nơi -> đổi mục tiêu

    def test_chase_when_deep_and_close_then_exit(self):
        ms = MonsterSet(G, fixtures=[croc()])
        ms.step([69.0, 24.0])  # cách 9 m, d ≥ 10
        m = ms.items[0]
        self.assertEqual(m["state"], "chase")
        self.assertAlmostEqual(m["pos"][0], 60 + 3.0 / 60)  # 3.0 m/s về phía người chơi
        ms.step([69.0, 5.0])  # người chơi lên d < 10
        self.assertEqual(ms.items[0]["state"], "patrol")

    def test_no_chase_when_shallow(self):
        ms = MonsterSet(G, fixtures=[croc()])
        ms.step([62.0, 9.0])
        self.assertEqual(ms.items[0]["state"], "patrol")

    def test_clamped_to_species_depth(self):
        ms = MonsterSet(G, fixtures=[croc(pos=[60, 10.0], waypoints=[[60, 10], [64, 10]], state="chase")])
        ms.step([60.0, 10.0 - 0.01])  # người chơi nông hơn dải loài -> không chase, vẫn kẹp d ≥ 10
        self.assertGreaterEqual(ms.items[0]["pos"][1], 10)


class Hit(unittest.TestCase):
    def test_hit_nearest_tie_by_id(self):
        ms = MonsterSet(G, fixtures=[croc(id="M2", pos=[61, 24]), croc(id="M1", pos=[59, 24])])
        hit = ms.step([60.0, 24.0])
        self.assertEqual(hit["id"], "M1")  # cùng khoảng cách sau di chuyển -> id nhỏ

    def test_apply_hit_lifo_and_recoil(self):
        ms = MonsterSet(G, fixtures=[croc()])
        kinds = ["ca_loc", "bong_sung", "ca_linh", "ca_linh", "ca_linh"]
        hold = [{"id": f"I{i + 1}", "kind": k, "u": 24000} for i, k in enumerate(kinds)]  # v1.2: cá thể nội bộ
        hit = ms.step([60.5, 24.0])
        lost = ms.apply_hit(hit, [60.5, 24.0], hold)
        # floor(5 × 0.5) = 2, vào giỏ sau mất trước; trả dạng public {id,kind,fresh}
        self.assertEqual(lost, [{"id": "I5", "kind": "ca_linh", "fresh": 100.0},
                                {"id": "I4", "kind": "ca_linh", "fresh": 100.0}])
        self.assertEqual([it["id"] for it in hold], ["I1", "I2", "I3"])
        m = ms.items[0]
        self.assertEqual((m["state"], m["state_ticks_left"]), ("recoil", 60))
        self.assertAlmostEqual(abs(m["recoil_dir"][0]), 1.0)  # lùi xa người chơi theo trục x

    def test_recoil_moves_2m_then_patrol_and_never_hits(self):
        ms = MonsterSet(G, fixtures=[croc(pos=[62, 24], state="recoil", state_ticks_left=60, recoil_dir=[1, 0])])
        hits = [ms.step([62.0, 24.0]) for _ in range(60)]
        m = ms.items[0]
        self.assertEqual(hits, [None] * 60)  # recoil không gây hit, kể cả bước vừa hết
        self.assertAlmostEqual(m["pos"][0], 64.0)  # 60 × 2/60 m
        self.assertEqual((m["state"], m["recoil_dir"]), ("patrol", None))
        self.assertIsNotNone(ms.step([64.0, 24.0]))  # bước kế mới xét chạm lại

    def test_coincident_center_recoils_plus_x(self):
        ms = MonsterSet(G, fixtures=[croc()])
        ms.apply_hit(ms.items[0], [60.0, 24.0], [])
        self.assertEqual(ms.items[0]["recoil_dir"], [1.0, 0.0])

    def test_no_hit_when_player_shallow(self):
        ms = MonsterSet(G, fixtures=[croc(pos=[60, 10], waypoints=[[60, 10], [64, 10]])])
        self.assertIsNone(ms.step([60.0, 9.5]))


if __name__ == "__main__":
    unittest.main()

"""Kiểm scenario gather mâu thuẫn -> BadInput (mã 2), theo PRD-0 mục D."""

import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.scenario import load_scenario

from helpers import Workdir, write_json

TUNING = load_contract()["tuning"]


def _load(block):
    """Ghi khối gather ra file tạm rồi nạp qua load_scenario."""
    with Workdir() as w:
        path = write_json(w.path("s.json"), {"gather": block})
        return load_scenario(path, "gather", TUNING)


class ScenarioGatherTest(unittest.TestCase):
    def assertBad(self, block):
        """Kiểm khối scenario bị từ chối bằng BadInput."""
        with self.assertRaises(BadInput):
            _load(block)

    def test_prd_example_is_valid(self):
        block = {
            "player": {"pos": [20, 0], "heading_deg": 0},
            "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}, {"id": "I2", "kind": "bong_sung", "fresh": 97.5}],  # v1.2: cá thể
            "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [22, 0]}],
            "fish": [],
            "random_fish": False,
            "time_left_ticks": 120,
        }
        self.assertEqual(_load(block), block)

    def test_unknown_field_in_node_or_fish(self):
        self.assertBad({"nodes": [{"id": "N1", "kind": "bong_sung", "pos": [5, 0], "ready": True}]})
        self.assertBad({"fish": [{"id": "F1", "kind": "ca_loc", "pos": [5, 5], "speed": 1}]})

    def test_regrow_ticks_upper_bound(self):
        node = {"id": "N1", "kind": "bong_sung", "pos": [5, 0]}
        _load({"nodes": [dict(node, regrow_ticks=1200)]})  # đúng regrow_s × 60: hợp lệ
        self.assertBad({"nodes": [dict(node, regrow_ticks=1201)]})

    def test_catch_cd_ticks_upper_bound(self):
        _load({"player": {"catch_cd_ticks": 30}})  # đúng catch_cooldown_s × 60: hợp lệ
        self.assertBad({"player": {"catch_cd_ticks": 31}})

    def test_non_finite_numbers(self):
        self.assertBad({"player": {"pos": [float("nan"), 0]}})
        self.assertBad({"player": {"vel": [float("inf"), 0]}})
        self.assertBad({"fish": [{"id": "F1", "kind": "ca_loc", "pos": [5, 5], "heading_deg": float("nan")}]})


if __name__ == "__main__":
    unittest.main()

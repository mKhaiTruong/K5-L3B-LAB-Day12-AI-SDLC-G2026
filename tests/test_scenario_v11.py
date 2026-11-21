"""Scenario v1.1 (TICKET-02 mục 4.3): Cá Sấu fixture, age_ticks, invuln_ticks, khối day."""

import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.scenario import load_scenario

from helpers import Workdir, write_json

TUNING = load_contract()["tuning"]
M1 = {"id": "M1", "kind": "ca_sau", "pos": [60, 24], "waypoints": [[60, 24], [64, 24]]}


def _load(data, mode):
    """Ghi scenario ra file tạm rồi nạp qua load_scenario."""
    with Workdir() as w:
        return load_scenario(write_json(w.path("s.json"), data), mode, TUNING)


class GatherV11(unittest.TestCase):
    def assertBad(self, block):
        """Kiểm khối gather bị từ chối bằng BadInput."""
        with self.assertRaises(BadInput):
            _load({"gather": block}, "gather")

    def test_valid_monsters_and_fish_age(self):
        block = {"monsters": [M1, dict(M1, id="M2", state="recoil", state_ticks_left=60, recoil_dir=[1, 0])],
                 "fish": [{"id": "F1", "kind": "ca_keo", "pos": [30, 25], "age_ticks": 119}],
                 "player": {"invuln_ticks": 90}}
        self.assertEqual(_load({"gather": block}, "gather"), block)

    def test_monster_depth_and_fields(self):
        self.assertBad({"monsters": [dict(M1, pos=[60, 5])]})  # Cá Sấu chỉ ở d ∈ [10, 30]
        self.assertBad({"monsters": [dict(M1, waypoints=[[60, 24]])]})
        self.assertBad({"monsters": [dict(M1, kind="ran")]})  # mở rộng Rắn chưa bật
        self.assertBad({"monsters": [dict(M1, hp=3)]})
        self.assertBad({"monsters": [dict(M1, target_idx=2)]})

    def test_monster_state_timer_consistency(self):
        self.assertBad({"monsters": [dict(M1, state="recoil", recoil_dir=[1, 0])]})  # thiếu timer
        self.assertBad({"monsters": [dict(M1, state="recoil", state_ticks_left=61, recoil_dir=[1, 0])]})
        self.assertBad({"monsters": [dict(M1, state="recoil", state_ticks_left=10, recoil_dir=[1, 1])]})
        self.assertBad({"monsters": [dict(M1, state="patrol", recoil_dir=[1, 0])]})
        self.assertBad({"monsters": [dict(M1, state="stunned", state_ticks_left=10)]})  # Lao chưa bật

    def test_player_counters_v11(self):
        self.assertBad({"player": {"invuln_ticks": 91}})
        self.assertBad({"player": {"attack_cd_ticks": 0}})  # Lao chưa bật
        self.assertBad({"fish": [{"id": "F1", "kind": "ca_loc", "pos": [30, 10], "age_ticks": -1}]})


class DayScenario(unittest.TestCase):
    def assertBad(self, data):
        """Kiểm scenario day bị từ chối bằng BadInput."""
        with self.assertRaises(BadInput):
            _load(data, "day")

    def test_prd_example_is_valid(self):
        data = {"day": {"money": 200, "earned": 200},
                "gather": {"hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}, {"id": "I2", "kind": "bong_sung", "fresh": 100},
                                    {"id": "I3", "kind": "bong_sung", "fresh": 100}], "random_fish": False}}
        out = _load(data, "day")
        self.assertEqual(out, {"day": data["day"], "gather": data["gather"], "quan": {}})

    def test_no_file_gives_empty_blocks(self):
        self.assertEqual(load_scenario(None, "day", TUNING), {"day": {}, "gather": {}, "quan": {}})

    def test_money_earned_rules(self):
        self.assertBad({"day": {"money": 200}})  # có tiền đầu kỳ phải khai earned
        self.assertBad({"day": {"money": 300, "earned": 200}})
        self.assertBad({"day": {"money": -1, "earned": 0}})
        _load({"day": {"money": 0, "earned": 500}}, "day")

    def test_upgrades_and_plan(self):
        _load({"day": {"upgrades": {"oxygen": 2, "hp": 0},
                       "day_plan": [{"day": 1, "dishes": {"ca_keo_nuong": 2}, "ingredients": {"ca_keo": 4}}]}},
              "day")
        self.assertBad({"day": {"upgrades": {"oxygen": 3}}})
        self.assertBad({"day": {"upgrades": {"weapon": 1}}})  # mở rộng chưa bật
        self.assertBad({"day": {"day_plan": [{"day": 1, "dishes": {"ca_keo_nuong": 2}, "ingredients": {"ca_keo": 3}}]}})
        self.assertBad({"day": {"day_plan": [{"day": 6, "dishes": {"lau_mam": 1}}]}})
        self.assertBad({"day": {"day_plan": [{"day": 1, "dishes": {"pho": 1}}]}})

    def test_forbidden_quan_fields_in_day(self):
        self.assertBad({"quan": {"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]}})
        self.assertBad({"quan": {"reputation": 4.0}})
        self.assertBad({"day": {"cash": 1}})

    def test_day_block_rejected_in_single_modes(self):
        with self.assertRaises(BadInput):
            _load({"day": {}}, "gather")
        with self.assertRaises(BadInput):
            _load({"day": {}, "quan": {}}, "quan")


if __name__ == "__main__":
    unittest.main()

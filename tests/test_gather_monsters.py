"""Gather v1.1 (TICKET-02 mục 1.2, 4.5): Cá Sấu trong buổi sáng — chạm, mất hàng LIFO, bất tử, ngất."""

import json
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.rng import Streams
from chonoi.sim.gather import GatherSim
from helpers import Workdir, events
from test_gather_lat1 import ik, items, run_gather, snap_at, tuning_gather

HOLD4 = items("ca_loc", "bong_sung", "ca_linh", "bong_sung")  # I1..I4 (v1.2: cá thể)


def croc_at(x, d):
    return {"id": "M1", "kind": "ca_sau", "pos": [x, d], "waypoints": [[60, 24], [64, 24]]}


def deep(**player):
    """Người chơi đứng yên ở [62,24], Cá Sấu M1 trùng chỗ; không cá, giỏ 4 món."""
    return {"player": {"pos": [62, 24], **player}, "random_fish": False, "hold": list(HOLD4),
            "monsters": [croc_at(62, 24)]}


def names(rows):
    return [(e["tick"], e["name"]) for e in events(rows)]


class GatherMonsters(unittest.TestCase):
    def test_m01_default_monsters_day1(self):
        with Workdir() as w:
            ms = snap_at(run_gather(w, {}, ticks=0), 0)["monsters"]
            self.assertEqual([(m["id"], m["pos"], m["state"]) for m in ms], [("M1", [60.0, 24.0], "patrol")])

    def test_m02_day_param_enables_from_day(self):
        tuning = load_contract()["tuning"]
        for day, ids in ((1, ["M1"]), (2, ["M1"]), (3, ["M1", "M2"])):
            sim = GatherSim(tuning, {}, Streams(1), IdAllocator(), day=day)
            self.assertEqual([m["id"] for m in sim.snapshot()["monsters"]], ids, day)

    def test_m03_hit_loses_half_lifo_and_sets_invuln(self):
        t = tuning_gather()
        with Workdir() as w:
            rows = run_gather(w, deep(), ticks=1)
            hits = events(rows, "monster_hit")
            self.assertEqual([e["tick"] for e in hits], [1])
            d = hits[0]["data"]
            self.assertEqual((d["monster_id"], d["hp"], d["pos"]), ("M1", t["hp_max"] - 1, [62.0, 24.0]))
            self.assertEqual(ik(d["lost"]), [("I4", "bong_sung"), ("I3", "ca_linh")])  # LIFO theo thứ tự vào giỏ
            s = snap_at(rows, 1)
            self.assertEqual(ik(s["hold"]), [("I1", "ca_loc"), ("I2", "bong_sung")])
            self.assertEqual(s["player"]["hp"], t["hp_max"] - 1)
            self.assertEqual(s["player"]["invuln_ticks"], t["monsters"]["invuln_ticks"])
            self.assertEqual(s["monsters"][0]["state"], "recoil")

    def test_m04_invulnerable_blocks_hit(self):
        with Workdir() as w:
            rows = run_gather(w, deep(invuln_ticks=5), ticks=10)
            self.assertEqual([e["tick"] for e in events(rows, "monster_hit")], [5])

    def test_m05_faint_by_monster(self):
        with Workdir() as w:
            inv = w.path("inv.json")
            rows = run_gather(w, deep(hp=1), ticks=5, inventory_out=inv)
            self.assertEqual(names(rows), [(1, "monster_hit"), (1, "faint"), (1, "gather_end")])
            d = events(rows, "faint")[0]["data"]
            self.assertEqual((d["cause"], d["hp"]), ("monster", 0))
            self.assertEqual(ik(d["lost"]), [("I2", "bong_sung"), ("I1", "ca_loc")])
            self.assertEqual(events(rows, "gather_end")[0]["data"], {"reason": "fainted",
                                                                     "inventory": {"items": []}})
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})

    def test_m06_hit_before_catch_same_step(self):
        block = {**deep(), "fish": [{"id": "F1", "kind": "ca_keo", "pos": [63, 24]}]}
        with Workdir() as w:
            rows = run_gather(w, block, [{"tick": 0, "catch": True}], ticks=1)
            self.assertEqual(names(rows), [(1, "monster_hit"), (1, "fish_caught")])
            # id mới nối tiếp id lớn nhất trong giỏ (I4), kể cả khi I3, I4 vừa rơi
            self.assertEqual(ik(snap_at(rows, 1)["hold"]),
                             [("I1", "ca_loc"), ("I2", "bong_sung"), ("I5", "ca_keo"), ("I6", "ca_keo")])


if __name__ == "__main__":
    unittest.main()

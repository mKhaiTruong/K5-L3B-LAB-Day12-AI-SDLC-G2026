"""Lát 2 (gather): hái nút, bắt cá — test hộp đen qua headless_cmd (PRD-0 mục E, F)."""

import json
import unittest

from helpers import Workdir, events
from test_gather_lat1 import ik, items, run_gather, snap_at, tuning_gather

E0 = [{"tick": 0, "interact": True}]
BASE = {"player": {"pos": [20, 0]}, "fish": [], "random_fish": False}


def node(nid, kind, x, **extra):
    return {"id": nid, "kind": kind, "pos": [x, 0], **extra}


def ev_list(rows, *names):
    return [(e["tick"], e["name"], e["data"]) for e in events(rows) if not names or e["name"] in names]


def regrow_ticks():
    return int(round(tuning_gather()["regrow_s"] * 60))


class Lat2Gather(unittest.TestCase):
    def test_l2_01_gather_at_radius_edge(self):
        t = tuning_gather()
        r = t["interact_radius"]
        with Workdir() as w:
            rows = run_gather(w, {**BASE, "hold": items("ca_loc", "bong_sung"),
                                  "nodes": [node("N1", "bong_dien_dien", 20 + r)]}, E0, ticks=1)
            self.assertEqual(ev_list(rows), [(1, "gather", {"node_id": "N1", "kind": "bong_dien_dien",
                                                            "amount": t["node_yield"]})])
            s = snap_at(rows, 1)
            self.assertEqual(ik(s["hold"]), [("I1", "ca_loc"), ("I2", "bong_sung")]
                             + [(f"I{3 + i}", "bong_dien_dien") for i in range(t["node_yield"])])
            n1 = [n for n in s["nodes"] if n["id"] == "N1"][0]
            self.assertIs(n1["ready"], False)
            self.assertEqual(n1["regrow_ticks"], regrow_ticks())

    def test_l2_02_regrown_then_gather_same_step(self):
        with Workdir() as w:
            rows = run_gather(w, {**BASE, "nodes": [node("N1", "bong_sung", 21, regrow_ticks=1)]}, E0, ticks=1)
            self.assertEqual([(e["tick"], e["name"]) for e in events(rows)],
                             [(1, "node_regrown"), (1, "gather")])

    def test_l2_03_hold_full_keeps_node(self):
        cap = tuning_gather()["hold_capacity"]
        with Workdir() as w:
            rows = run_gather(w, {**BASE, "hold": items(*["ca_loc"] * cap), "nodes": [node("N1", "bong_sung", 21)]},
                              E0, ticks=1)
            self.assertEqual(ev_list(rows), [(1, "hold_full", {"action": "gather", "node_id": "N1",
                                                               "required": tuning_gather()["node_yield"],
                                                               "free": 0})])
            n1 = [n for n in snap_at(rows, 1)["nodes"] if n["id"] == "N1"][0]
            self.assertEqual(n1["regrow_ticks"], 0)

    def test_l2_04_tie_by_id_and_nearest(self):
        with Workdir() as w:
            rows = run_gather(w, {**BASE, "nodes": [node("N10", "bong_sung", 22), node("N2", "bong_dien_dien", 18)]},
                              E0, ticks=1)
            self.assertEqual(events(rows, "gather")[0]["data"]["node_id"], "N2")
        with Workdir() as w:
            rows = run_gather(w, {**BASE, "nodes": [node("N1", "bong_sung", 21.5),
                                                    node("N2", "bong_dien_dien", 20.5)]}, E0, ticks=1)
            self.assertEqual(events(rows, "gather")[0]["data"]["node_id"], "N2")

    def test_l2_05_no_gather_underwater_or_out_of_radius(self):
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [20, 1]}, "fish": [], "random_fish": False,
                                  "nodes": [node("N1", "bong_sung", 20)]}, E0, ticks=1)
            self.assertEqual(ev_list(rows, "gather", "hold_full"), [])
        with Workdir() as w:
            r = tuning_gather()["interact_radius"]
            rows = run_gather(w, {**BASE, "nodes": [node("N1", "bong_sung", 20 + r + 0.01)]}, E0, ticks=1)
            self.assertEqual(ev_list(rows, "gather", "hold_full"), [])

    def test_l2_06_gather_on_last_step_goes_to_inventory(self):
        with Workdir() as w:
            kho = w.path("kho.json")
            rows = run_gather(w, {**BASE, "time_left_ticks": 1, "nodes": [node("N1", "bong_sung", 21)]},
                              E0, ticks=5, inventory_out=kho)
            evs = ev_list(rows)
            self.assertEqual([(t, n) for t, n, _ in evs], [(1, "gather"), (1, "gather_end")])
            want = {"items": [{"id": "I1", "kind": "bong_sung", "fresh": 100.0}]}  # hái ở bước cuối: chưa hao
            self.assertEqual(evs[1][2], {"reason": "time", "inventory": want})
            with open(kho, encoding="utf-8") as f:
                self.assertEqual(json.load(f), want)

    def test_l2_07_second_press_on_regrowing_node(self):
        frames_in = [{"tick": 0, "interact": True}, {"tick": 1, "interact": False}, {"tick": 2, "interact": True}]
        with Workdir() as w:
            rows = run_gather(w, {**BASE, "nodes": [node("N1", "bong_sung", 21)]}, frames_in, ticks=3)
            self.assertEqual(len(events(rows, "gather")), 1)

    def test_l2_08_gather_then_dock_writes_inventory(self):
        frames_in = [{"tick": 0, "interact": True}, {"tick": 1, "interact": False, "move": [-1, 0]},
                     {"tick": 30, "interact": True}]
        with Workdir() as w:
            kho = w.path("kho.json")
            rows = run_gather(w, {"player": {"pos": [6, 0]}, "fish": [], "random_fish": False,
                                  "nodes": [node("N1", "bong_sung", 7)]}, frames_in, ticks=60, inventory_out=kho)
            evs = ev_list(rows, "gather", "gather_end")
            self.assertEqual([(t, n) for t, n, _ in evs], [(1, "gather"), (31, "gather_end")])
            # hái ở bước 0, hao ở 30 bước 1..30 (0.5/s = 1/120 mỗi tick) rồi cập bến ở bước 30
            want = {"items": [{"id": "I1", "kind": "bong_sung", "fresh": 99.75}]}
            self.assertEqual(evs[1][2], {"reason": "docked", "inventory": want})
            with open(kho, encoding="utf-8") as f:
                self.assertEqual(json.load(f), want)
            self.assertEqual(rows[-1]["reason"], "docked")


CB = {"player": {"pos": [20, 5]}, "random_fish": False, "nodes": []}


def fish(fid, kind, x, d):
    return {"id": fid, "kind": kind, "pos": [x, d]}


def caught(rows):
    return [(e["tick"], e["data"]["fish_id"]) for e in events(rows, "fish_caught")]


def catch_frames(*pairs):
    return [{"tick": k, "catch": v} for k, v in pairs]


class Lat2Catch(unittest.TestCase):
    def test_l2_09_catch_full_yield_and_cooldown(self):
        t = tuning_gather()
        y = t["fish_yield"]["ca_linh"]
        with Workdir() as w:
            rows = run_gather(w, {**CB, "fish": [fish("F1", "ca_linh", 21, 5)]}, catch_frames((0, True)), ticks=1)
            self.assertEqual(ev_list(rows), [(1, "fish_caught", {"fish_id": "F1", "kind": "ca_linh", "yield": y})])
            s = snap_at(rows, 1)
            self.assertEqual(s["hold"], [{"id": f"I{i + 1}", "kind": "ca_linh", "fresh": 100.0} for i in range(y)])
            self.assertEqual(s["fish"], [])
            self.assertEqual(s["player"]["catch_cd_ticks"], int(round(t["catch_cooldown_s"] * 60)))

    def _two_fish(self):
        return {**CB, "fish": [fish("F1", "ca_linh", 21, 5), fish("F2", "ca_loc", 19, 5)]}

    def test_l2_10_cooldown_blocks_before_L(self):
        L = int(round(tuning_gather()["catch_cooldown_s"] * 60))
        with Workdir() as w:
            rows = run_gather(w, self._two_fish(), catch_frames((0, True), (1, False), (L - 1, True)), ticks=L + 10)
            self.assertEqual(caught(rows), [(1, "F1")])

    def test_l2_11_cooldown_ready_at_L(self):
        L = int(round(tuning_gather()["catch_cooldown_s"] * 60))
        with Workdir() as w:
            rows = run_gather(w, self._two_fish(), catch_frames((0, True), (1, False), (L, True)), ticks=L + 10)
            self.assertEqual(caught(rows), [(1, "F1"), (L + 1, "F2")])

    def test_l2_12_no_catch_at_surface(self):
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [20, 0]}, "random_fish": False, "nodes": [],
                                  "fish": [fish("F1", "ca_linh", 21, 1)]}, catch_frames((0, True)), ticks=1)
            self.assertEqual(ev_list(rows, "fish_caught", "hold_full"), [])
            self.assertEqual(snap_at(rows, 1)["player"]["catch_cd_ticks"], 0)

    def test_l2_13_hold_full_keeps_fish_no_cooldown_no_retry(self):
        t = tuning_gather()
        y = t["fish_yield"]["ca_linh"]
        free = y - 1
        with Workdir() as w:
            rows = run_gather(w, {**CB, "hold": items(*["bong_sung"] * (t["hold_capacity"] - free)),
                                  "fish": [fish("F1", "ca_linh", 21, 5), fish("F2", "ca_loc", 18.5, 5)]},
                              catch_frames((0, True)), ticks=1)
            self.assertEqual(ev_list(rows), [(1, "hold_full", {"action": "catch", "fish_id": "F1",
                                                               "required": y, "free": free})])
            s = snap_at(rows, 1)
            self.assertEqual(s["player"]["catch_cd_ticks"], 0)
            self.assertEqual([f["id"] for f in s["fish"]], ["F1", "F2"])
            self.assertEqual(len(s["hold"]), t["hold_capacity"] - free)

    def test_l2_14_no_fish_in_range_no_cooldown(self):
        with Workdir() as w:
            rows = run_gather(w, {**CB, "fish": [fish("F1", "ca_linh", 30, 5)]}, catch_frames((0, True)), ticks=1)
            self.assertEqual(ev_list(rows), [])
            self.assertEqual(snap_at(rows, 1)["player"]["catch_cd_ticks"], 0)

    def test_l2_15_catch_at_radius_edge(self):
        t = tuning_gather()
        with Workdir() as w:
            rows = run_gather(w, {**CB, "fish": [fish("F1", "ca_loc", 20 + t["catch_radius"], 5)]},
                              catch_frames((0, True)), ticks=1)
            self.assertEqual(ev_list(rows), [(1, "fish_caught", {"fish_id": "F1", "kind": "ca_loc",
                                                                 "yield": t["fish_yield"]["ca_loc"]})])

    def test_l2_16_default_fish_when_random_fish_true(self):
        t = tuning_gather()
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [15, 4]}}, catch_frames((0, True)), ticks=1)
            evs = events(rows, "fish_caught")
            self.assertEqual(len(evs), 1)
            self.assertEqual(evs[0]["data"], {"fish_id": "F2", "kind": "ca_linh",       # cũ: "F1"
                                              "yield": t["fish_yield"]["ca_linh"]})
            self.assertEqual(len(snap_at(rows, 1)["fish"]), t["fish_initial"] - 1)  # cũ: 5


if __name__ == "__main__":
    unittest.main()

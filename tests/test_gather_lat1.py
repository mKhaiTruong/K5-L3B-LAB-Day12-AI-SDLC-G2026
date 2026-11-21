"""Lát 1 (gather): dive/surface, oxy, ngạt, Máu, ngất — test hộp đen qua headless_cmd (PRD-0 mục E, F)."""

import json
import os
import unittest

from helpers import ROOT, Workdir, close, events, frames, read_jsonl, run_headless, snapshots, write_json


def tuning_gather():
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return json.load(f)["tuning"]["gather"]


def run_gather(w, block, frame_list=None, ticks=10, inventory_out=None):
    """Chạy headless gather với scenario {"gather": block}; trả các dòng JSONL. Lỗi mã thoát → fail."""
    args = ["--mode", "gather", "--seed", "1", "--ticks", str(ticks), "--out", w.path("o.jsonl"),
            "--scenario", write_json(w.path("sc.json"), {"gather": block})]
    if frame_list is not None:
        args += ["--inputs", write_json(w.path("in.json"), frames(*frame_list))]
    if inventory_out is not None:
        args += ["--inventory-out", inventory_out]
    code, err = run_headless(*args)
    assert code == 0, err
    return read_jsonl(w.path("o.jsonl"))


def items(*kinds, start=1, fresh=100):
    """Cá thể fixture (contract v1.2): I{start}, I{start+1}, … theo thứ tự vào giỏ."""
    return [{"id": f"I{start + i}", "kind": k, "fresh": fresh} for i, k in enumerate(kinds)]


def ik(arr):
    """(id, kind) của mảng cá thể — dùng khi test không xét độ tươi."""
    return [(it["id"], it["kind"]) for it in arr]


def snap_at(rows, tick):
    return [s for s in snapshots(rows) if s["tick"] == tick][-1]


def oxy_max():
    return int(round(tuning_gather()["oxygen_max_s"] * 60))


class Lat1Oxygen(unittest.TestCase):
    def test_l1_01_dive_event_pos_and_oxygen_drain(self):
        sd = tuning_gather()["surface_depth"]
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [2, 0]}}, [{"tick": 0, "move": [0, 1]}], ticks=20)
            dives = events(rows, "dive")
            self.assertEqual(len(dives), 1)
            self.assertEqual(dives[0]["tick"], 11)
            self.assertGreater(dives[0]["data"]["pos"][1], sd)
            self.assertTrue(close(dives[0]["data"]["pos"][1], 0.567))
            self.assertTrue(close(dives[0]["data"]["pos"][0], 2.0))
            self.assertEqual(events(rows, "surface"), [])
            self.assertEqual(snap_at(rows, 20)["player"]["oxygen_ticks"], oxy_max() - 10)

    def test_l1_02_surface_event_and_refill(self):
        t = tuning_gather()
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [20, 1.0], "oxygen_ticks": 100}},
                              [{"tick": 0, "move": [0, -1]}], ticks=30)
            surf = events(rows, "surface")
            self.assertEqual(len(surf), 1)
            self.assertEqual(surf[0]["tick"], 11)
            self.assertLessEqual(surf[0]["data"]["pos"][1], t["surface_depth"])
            p = snap_at(rows, 30)["player"]
            self.assertEqual(p["oxygen_ticks"], 100 - 10 + 20 * t["oxygen_refill_per_tick"])
            self.assertIs(p["at_surface"], True)
            self.assertEqual(p["zero_oxy_ticks"], 0)

    def test_l1_03_refill_clamped_to_max(self):
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [20, 0], "oxygen_ticks": oxy_max() - 3}}, ticks=3)
            self.assertEqual(snap_at(rows, 3)["player"]["oxygen_ticks"], oxy_max())

    def test_l1_04_oxygen_empty_once(self):
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [50, 10], "oxygen_ticks": 1}}, ticks=30)
            self.assertEqual([(e["tick"], e["data"]) for e in events(rows, "oxygen_empty")],
                             [(1, {"oxygen_ticks": 0})])
            self.assertEqual(snap_at(rows, 30)["player"]["oxygen_ticks"], 0)

    def test_l1_05_no_oxygen_empty_when_already_zero(self):
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [50, 10], "oxygen_ticks": 0}}, ticks=5)
            self.assertEqual(events(rows, "oxygen_empty"), [])


class Lat1ChokeFaint(unittest.TestCase):
    def test_l1_06_first_choke_at_t_plus_59(self):
        t = tuning_gather()
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [50, 10], "oxygen_ticks": 1}}, ticks=60)
            empty = events(rows, "oxygen_empty")
            chokes = events(rows, "choke")
            self.assertEqual([e["tick"] for e in empty], [1])
            self.assertEqual(len(chokes), 1)
            self.assertEqual(chokes[0]["tick"], empty[0]["tick"] + t["choke_interval_ticks"] - 1)
            self.assertEqual(chokes[0]["tick"], 60)
            self.assertEqual(chokes[0]["data"], {"hp": t["hp_max"] - 1})
            self.assertEqual(snap_at(rows, 30)["player"]["zero_oxy_ticks"], 30)
            p = snap_at(rows, 60)["player"]
            self.assertEqual(p["hp"], t["hp_max"] - 1)
            self.assertEqual(p["zero_oxy_ticks"], 0)

    def test_l1_07_surface_on_choke_step_no_choke(self):
        t = tuning_gather()
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [50, 0.51], "oxygen_ticks": 0,
                                             "zero_oxy_ticks": t["choke_interval_ticks"] - 1}},
                              [{"tick": 0, "move": [0, -1]}], ticks=1)
            self.assertEqual([e["name"] for e in events(rows)], ["surface"])
            p = snap_at(rows, 1)["player"]
            self.assertEqual(p["oxygen_ticks"], t["oxygen_refill_per_tick"])
            self.assertEqual(p["zero_oxy_ticks"], 0)
            self.assertEqual(p["hp"], t["hp_max"])

    def test_l1_08_choke_without_surfacing(self):
        t = tuning_gather()
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [50, 0.51], "oxygen_ticks": 0,
                                             "zero_oxy_ticks": t["choke_interval_ticks"] - 1}}, ticks=1)
            evs = events(rows)
            self.assertEqual([e["name"] for e in evs], ["choke"])
            self.assertEqual(evs[0]["data"], {"hp": t["hp_max"] - 1})
            self.assertEqual(snap_at(rows, 1)["player"]["zero_oxy_ticks"], 0)

    def test_l1_09_faint_lifo_and_empty_inventory(self):
        t = tuning_gather()
        with Workdir() as w:
            inv = w.path("inv.json")
            rows = run_gather(w, {"player": {"pos": [50, 10], "oxygen_ticks": 0, "hp": 1,
                                             "zero_oxy_ticks": t["choke_interval_ticks"] - 1},
                                  "hold": items("ca_loc", "bong_sung")}, ticks=5, inventory_out=inv)
            evs = events(rows)
            self.assertEqual([e["name"] for e in evs], ["choke", "faint", "gather_end"])
            self.assertEqual({e["tick"] for e in evs}, {1})
            d = evs[1]["data"]
            self.assertEqual((d["cause"], d["hp"]), ("choke", 0))
            self.assertEqual(ik(d["lost"]), [("I2", "bong_sung"), ("I1", "ca_loc")])  # LIFO, cá thể (v1.2)
            self.assertEqual(evs[2]["data"], {"reason": "fainted", "inventory": {"items": []}})
            end = rows[-1]
            self.assertEqual(end["type"], "end")
            self.assertEqual(end["ticks"], 1)
            self.assertEqual(end["reason"], "fainted")
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})
            last = snapshots(rows)[-1]
            self.assertEqual(last["hold"], [])
            self.assertEqual(last["state"], "finished")

    def test_l1_10_three_chokes_then_faint(self):
        t = tuning_gather()
        k, hp = t["choke_interval_ticks"], t["hp_max"]
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [50, 10], "oxygen_ticks": 1}}, ticks=k * hp + 120)
            self.assertEqual([(e["tick"], e["data"]["hp"]) for e in events(rows, "choke")],
                             [(k * i, hp - i) for i in range(1, hp + 1)])
            faint = events(rows, "faint")
            self.assertEqual([e["tick"] for e in faint], [k * hp])
            self.assertEqual(faint[0]["data"]["lost"], [])
            self.assertEqual(rows[-1]["ticks"], k * hp)
            self.assertEqual(rows[-1]["reason"], "fainted")

    def test_l1_11_faint_beats_dock_same_step(self):
        t = tuning_gather()
        with Workdir() as w:
            rows = run_gather(w, {"player": {"pos": [3, 2], "oxygen_ticks": 0, "hp": 1,
                                             "zero_oxy_ticks": t["choke_interval_ticks"] - 1}},
                              [{"tick": 0, "interact": True}], ticks=1)
            evs = events(rows)
            self.assertEqual([e["name"] for e in evs], ["choke", "faint", "gather_end"])
            self.assertEqual(evs[2]["data"]["reason"], "fainted")


if __name__ == "__main__":
    unittest.main()

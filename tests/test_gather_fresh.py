"""Gather v1.2 (TICKET-03 mục 1): giỏ là mảng cá thể, hao tươi 0.5/s, spoiled, id I* nối tiếp, bàn giao kho."""

import json
import unittest

from chonoi.contract import load_contract
from chonoi.fresh import ItemIds
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.gather import GatherSim
from helpers import Workdir, events
from test_gather_lat1 import ik, items, run_gather, snap_at

QUIET = {"random_fish": False, "monsters": []}
STEP = 1 / 120  # 0.5 điểm/s ÷ 60 tick


def spoiled(rows):
    return [(e["tick"], e["data"]) for e in events(rows, "spoiled")]


class GatherFresh(unittest.TestCase):
    def test_fr01_prd_threshold_example(self):
        """Ví dụ PRD: fresh đúng 30, một bước không input -> spoiled ở tick 1, đúng một lần."""
        with Workdir() as w:
            rows = run_gather(w, {**QUIET, "hold": items("ca_linh", fresh=30)}, ticks=1)
            self.assertEqual([(e["tick"], e["name"], e["data"]) for e in events(rows)],
                             [(1, "spoiled", {"item_id": "I1", "kind": "ca_linh", "location": "hold"})])
            rows = run_gather(w, {**QUIET, "hold": items("ca_linh", fresh=30)}, ticks=20)
            self.assertEqual(len(events(rows, "spoiled")), 1)

    def test_fr02_decay_rate_half_per_second(self):
        with Workdir() as w:
            h = snap_at(run_gather(w, {**QUIET, "hold": items("ca_loc")}, ticks=60), 60)["hold"]
            self.assertEqual(h, [{"id": "I1", "kind": "ca_loc", "fresh": 99.5}])

    def test_fr03_above_threshold_not_spoiled(self):
        """30 + 1 bước hao vẫn >= 30 sau 1 bước, ươn ở bước thứ 2."""
        with Workdir() as w:
            rows = run_gather(w, {**QUIET, "hold": items("ca_linh", fresh=30.0125)}, ticks=3)  # 7203 đơn vị
            self.assertEqual([t for t, _ in spoiled(rows)], [2])

    def test_fr04_many_cross_same_tick_by_id(self):
        hold = [{"id": "I10", "kind": "ca_loc", "fresh": 30}, {"id": "I2", "kind": "bong_sung", "fresh": 30}]
        with Workdir() as w:
            self.assertEqual([d["item_id"] for _, d in spoiled(run_gather(w, {**QUIET, "hold": hold}, ticks=1))],
                             ["I2", "I10"])

    def test_fr05_clamped_at_zero_no_repeat(self):
        with Workdir() as w:
            rows = run_gather(w, {**QUIET, "hold": items("ca_loc", fresh=0)}, ticks=10)
            self.assertEqual(spoiled(rows), [])
            self.assertEqual(snap_at(rows, 10)["hold"][0]["fresh"], 0.0)

    def test_fr06_new_item_fresh_100_decays_from_next_step(self):
        frames = [{"tick": 0, "catch": True}]
        block = {**QUIET, "player": {"pos": [20, 5]}, "nodes": [],
                 "fish": [{"id": "F1", "kind": "ca_loc", "pos": [21, 5]}]}
        with Workdir() as w:
            self.assertEqual(snap_at(run_gather(w, block, frames, ticks=1), 1)["hold"],
                             [{"id": "I1", "kind": "ca_loc", "fresh": 100.0}])  # vừa bắt: chưa hao
            h = snap_at(run_gather(w, block, frames, ticks=10), 10)["hold"]
            self.assertEqual(ik(h), [("I1", "ca_loc")])
            self.assertAlmostEqual(h[0]["fresh"], 100 - 9 * STEP, places=9)  # bắt ở bước 0, hao bước 1..9

    def test_fr07_new_ids_continue_after_fixture_max(self):
        block = {**QUIET, "player": {"pos": [20, 5]}, "nodes": [], "hold": items("bong_sung", start=7),
                 "fish": [{"id": "F1", "kind": "ca_linh", "pos": [21, 5]}]}
        with Workdir() as w:
            h = snap_at(run_gather(w, block, [{"tick": 0, "catch": True}], ticks=1), 1)["hold"]
            self.assertEqual(ik(h), [("I7", "bong_sung"), ("I8", "ca_linh"), ("I9", "ca_linh"), ("I10", "ca_linh")])

    def test_fr08_spoiled_still_takes_slot(self):
        cap = load_contract()["tuning"]["gather"]["hold_capacity"]
        block = {**QUIET, "player": {"pos": [20, 0]}, "hold": items(*["ca_loc"] * cap, fresh=0),
                 "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [21, 0]}]}
        with Workdir() as w:
            rows = run_gather(w, block, [{"tick": 0, "interact": True}], ticks=1)
            self.assertEqual([e["name"] for e in events(rows)], ["hold_full"])

    def test_fr09_handoff_file_matches_gather_end(self):
        """Smoke bàn giao (PRD): fresh 100, cập bến ở frame 0 -> file kho theo id, hao đúng 1 bước."""
        with Workdir() as w:
            kho = w.path("kho.json")
            hold = [{"id": "I3", "kind": "ca_linh", "fresh": 100}, {"id": "I1", "kind": "ca_loc", "fresh": 97.5}]
            rows = run_gather(w, {**QUIET, "player": {"pos": [2, 0]}, "hold": hold},
                              [{"tick": 0, "interact": True}], ticks=1, inventory_out=kho)
            with open(kho, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(ik(saved["items"]), [("I1", "ca_loc"), ("I3", "ca_linh")])  # file theo id
            self.assertAlmostEqual(saved["items"][0]["fresh"], 97.5 - STEP, places=9)
            self.assertAlmostEqual(saved["items"][1]["fresh"], 100 - STEP, places=9)
            # gather_end cùng schema; JSONL làm tròn 3 chữ số (dung sai quan sát ±0.01), file giữ đủ chính xác
            inv = events(rows, "gather_end")[0]["data"]["inventory"]["items"]
            self.assertEqual(ik(inv), ik(saved["items"]))
            for a, b in zip(inv, saved["items"]):
                self.assertAlmostEqual(a["fresh"], b["fresh"], delta=0.01)

    def test_fr10_shared_item_ids_across_phases(self):
        """day giữ MỘT ItemIds: GatherSim dùng tiếp id đã cấp ở pha/Ngày trước."""
        shared = ItemIds()
        shared.reserve("I20")
        sim = GatherSim(load_contract()["tuning"],
                        {**QUIET, "player": {"pos": [20, 5]}, "nodes": [],
                         "fish": [{"id": "F1", "kind": "ca_loc", "pos": [21, 5]}]},
                        Streams(1), IdAllocator(), item_ids=shared)
        sim.step(InputState((0.0, 0.0), {}, {"catch"}))
        self.assertEqual(ik(sim.snapshot()["hold"]), [("I21", "ca_loc")])
        self.assertEqual(shared.new(), "I22")


if __name__ == "__main__":
    unittest.main()

"""Độ tươi + kho cá thể v1.2 (TICKET-03 mục 1): helper chonoi.fresh và file kho."""

import json
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.fresh import (Freshness, ItemIds, UNITS, decay, fresh_price, lifo_drop, new_item, parse_items,
                          public, reserve_recipe)
from chonoi.inventory import KINDS, hold_to_items, read_inventory, write_inventory

from helpers import Workdir, write_json

T = load_contract()["tuning"]
CFG = Freshness(T)


def it(i, kind="ca_linh", fresh=100):
    """Cá thể nội bộ cho test."""
    return {"id": i, "kind": kind, "u": round(fresh * UNITS)}


class Units(unittest.TestCase):
    def test_contract_v12_rates(self):
        self.assertEqual(load_contract()["contract_version"], "1.2")
        self.assertEqual((CFG.gather_per_tick, CFG.quan_per_tick, CFG.initial, CFG.spoiled_below),
                         (2, 1, 24000, 7200))  # 0.5/s, 0.25/s, 100, 30 với 240 đơn vị/điểm

    def test_spoiled_exactly_once_at_threshold_by_id(self):
        hold = [it("I10", fresh=30), it("I2", fresh=30), it("I3", fresh=31)]
        ev = decay(hold, CFG.gather_per_tick, CFG, "hold")  # fixture PRD: fresh 30 -> ươn ở bước đầu
        self.assertEqual([e[1]["item_id"] for e in ev], ["I2", "I10"])  # theo id, I2 trước I10
        self.assertEqual(ev[0], ("spoiled", {"item_id": "I2", "kind": "ca_linh", "location": "hold"}))
        self.assertEqual(decay(hold, CFG.gather_per_tick, CFG, "hold"), [])  # không phát lại
        self.assertAlmostEqual(public(hold[0])["fresh"], 30 - 2 * 2 / UNITS)

    def test_decay_clamps_at_zero(self):
        h = [it("I1", fresh=0)]
        decay(h, 2, CFG, "hold")
        self.assertEqual(h[0]["u"], 0)

    def test_ids_keep_growing(self):
        ids = ItemIds()
        ids.reserve_all([it("I7")])
        self.assertEqual([new_item(ids, "ca_loc", CFG)["id"] for _ in range(2)], ["I8", "I9"])


class ReserveAndPrice(unittest.TestCase):
    def test_reserve_freshest_tie_by_id_skip_spoiled(self):
        stock = [it("I1", "ca_linh", 80), it("I2", "ca_linh", 90), it("I3", "ca_linh", 90),
                 it("I4", "ca_linh", 29), it("I5", "bong_dien_dien", 50)]
        recipe = T["menu"]["lau_ca_linh_dien_dien"]["recipe"]  # ca_linh ×3 + bong_dien_dien ×1
        self.assertEqual(reserve_recipe(stock, recipe, CFG), ["I1", "I2", "I3", "I5"])
        self.assertEqual(reserve_recipe(stock, {"ca_linh": 2}, CFG), ["I2", "I3"])  # 90, 90 hòa -> id
        self.assertIsNone(reserve_recipe(stock, {"ca_linh": 4}, CFG))  # I4 ươn không tính
        self.assertIsNone(reserve_recipe(stock, {"ca_linh": 1}, CFG, exclude={"I1", "I2", "I3"}))

    def test_fresh_price_floor(self):
        self.assertEqual(fresh_price(120, [it("a", fresh=100), it("b", fresh=97.5)]), 118)  # floor(120 × 98.75%)
        self.assertEqual(fresh_price(60, [it("a", fresh=30)]), 18)

    def test_lifo_drop_public(self):
        hold = [it("I1", "ca_loc"), it("I2", "bong_sung"), it("I3", "ca_linh")]
        self.assertEqual([x["id"] for x in lifo_drop(hold, 2)], ["I3", "I2"])
        self.assertEqual([x["id"] for x in hold], ["I1"])


class InventoryFile(unittest.TestCase):
    PRD = {"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, {"id": "I2", "kind": "ca_loc", "fresh": 97.5}]}

    def test_read_prd_example_and_roundtrip_exact(self):
        with Workdir() as w:
            items = read_inventory(write_json(w.path("k.json"), self.PRD), "1.2")
            self.assertEqual([x["u"] for x in items], [24000, 23400])
            odd = [it("I3", fresh=30), it("I1")]
            decay(odd, 1, CFG, "stock")  # 29.99583… — không biểu diễn gọn ở 3 chữ số
            write_inventory(w.path("o.json"), odd)
            with open(w.path("o.json"), encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual([x["id"] for x in data["items"]], ["I1", "I3"])  # ghi theo id
            back = read_inventory(w.path("o.json"), "1.2")
            self.assertEqual({x["id"]: x["u"] for x in back}, {x["id"]: x["u"] for x in odd})  # giữ nhánh ngưỡng 30

    def test_v12_rejects_count_schema_and_bad_items(self):
        bad = [{"items": {"ca_loc": 1}},                                     # kho đếm cũ
               {"items": [{"id": "I1", "kind": "ca_tra", "fresh": 50}]},     # kind lạ
               {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 50}] * 2},  # id trùng
               {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100.5}]},  # ngoài miền
               {"items": [{"id": "", "kind": "ca_loc", "fresh": 50}]},
               {"items": [{"id": "I1", "kind": "ca_loc"}]},
               {"items": [], "money": 0}]
        with Workdir() as w:
            for i, data in enumerate(bad):
                with self.subTest(data=data), self.assertRaises(BadInput):
                    read_inventory(write_json(w.path(f"b{i}.json"), data), "1.2")
            self.assertEqual(read_inventory(write_json(w.path("e.json"), {"items": []}), "1.2"), [])

    def test_hold_to_items_public_sorted(self):
        self.assertEqual(hold_to_items([it("I10", "ca_loc"), it("I2", "bong_sung", 50)]),
                         [{"id": "I2", "kind": "bong_sung", "fresh": 50.0}, {"id": "I10", "kind": "ca_loc", "fresh": 100.0}])

    def test_parse_items_kinds(self):
        self.assertEqual(len(KINDS), 6)
        with self.assertRaises(BadInput):
            parse_items([{"id": "I1", "kind": "ca_loc", "fresh": float("nan")}], "x", KINDS)


if __name__ == "__main__":
    unittest.main()

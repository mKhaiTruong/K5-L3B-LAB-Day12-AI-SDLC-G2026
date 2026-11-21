"""Kiểm scenario quan mâu thuẫn -> BadInput / mã 2, theo PRD-0 mục D."""

import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.scenario import load_scenario

from helpers import Workdir, run_headless, write_json

TUNING = load_contract()["tuning"]
DISH = {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60}


def item(i, kind="ca_loc", fresh=100):
    """Cá thể v1.2 cho fixture."""
    return {"id": i, "kind": kind, "fresh": fresh}


def _load(block):
    """Ghi khối quan ra file tạm rồi nạp qua load_scenario."""
    with Workdir() as w:
        path = write_json(w.path("s.json"), {"quan": block})
        return load_scenario(path, "quan", TUNING)


def _customer(**kw):
    """Tạo khách C1 ở bàn T1 gọi cá lóc nướng trui, ghi đè trường theo kw."""
    return dict({"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}, **kw)


class ScenarioQuanStatic(unittest.TestCase):
    def assertBad(self, block):
        """Kiểm khối scenario quan bị từ chối bằng BadInput."""
        with self.assertRaises(BadInput):
            _load(block)

    def test_valid_fixtures_pass(self):
        _load({"stock": [item("I1")], "customers": [_customer()]})  # reserved mặc định (QuanSim cấp)
        _load({"stock": [item("I1"), item("I2")], "customers": [_customer(reserved=["I2"])]})
        _load({"customers": [_customer(order_status="assigned", reserved=[])],
               "stoves": [{"id": "B1", "state": "cooking", "dish": DISH, "cook_ticks_left": 360}]})
        _load({"customers": [_customer(order_status="assigned")], "hand": DISH})
        _load({"customers": [_customer(state="eating", order_status="served", eat_ticks_left=600,
                                       base_price=60, tip=12)]})
        _load({"customers": [_customer(order_status="unfulfillable")]})

    def test_unknown_fields_and_ids(self):
        self.assertBad({"customers": [_customer(mood="happy")]})
        self.assertBad({"stoves": [{"id": "B9"}]})  # v1.1 đã có B2 thật
        self.assertBad({"tables": [{"id": "T1", "seats": 2}]})
        self.assertBad({"customers": [_customer(dish_id="pho")]})

    def test_reserved_must_match_recipe(self):
        two = [item("I1"), item("I2")]
        self.assertBad({"stock": two, "customers": [_customer(reserved=["I1", "I2"])]})  # 2 cá lóc ≠ công thức
        self.assertBad({"stock": two, "customers": [_customer(order_status="unfulfillable", reserved=["I1"])]})

    def test_reserved_ids_v12(self):
        stock = [item("I1"), item("I2", fresh=29.5), item("I3", "bong_sung")]
        self.assertBad({"stock": stock, "customers": [_customer(reserved=["I9"])]})  # không có trong kho
        self.assertBad({"stock": stock, "customers": [_customer(reserved=["I2"])]})  # đã ươn
        self.assertBad({"stock": stock, "customers": [_customer(reserved=["I3"])]})  # sai loại
        self.assertBad({"stock": stock, "customers": [_customer(reserved=["I1"]),
                                                      _customer(id="C2", table_id="T2", reserved=["I1"])]})  # dùng chung
        self.assertBad({"customers": [_customer(reserved={"ca_loc": 1})]})  # dạng đếm cũ
        self.assertBad({"stock": {"ca_loc": 1}})  # kho đếm cũ

    def test_eating_needs_served_timer_and_price(self):
        self.assertBad({"customers": [_customer(state="eating", order_status="served", base_price=60, tip=0)]})
        self.assertBad({"customers": [_customer(state="eating", order_status="served", eat_ticks_left=600)]})
        self.assertBad({"customers": [_customer(state="waiting", order_status="served")]})

    def test_assigned_needs_exactly_one_matching_dish(self):
        self.assertBad({"customers": [_customer(order_status="assigned")]})  # không có món
        self.assertBad({"customers": [_customer(order_status="assigned")], "hand": DISH,
                        "stoves": [{"id": "B1", "state": "ready", "dish": DISH}]})  # bếp và tay cùng đơn
        self.assertBad({"customers": [_customer(order_status="assigned")],
                        "hand": dict(DISH, dish_id="goi_bong_sung")})  # món không khớp đơn
        self.assertBad({"hand": DISH})  # tham chiếu khách không có

    def test_stove_state_consistency(self):
        self.assertBad({"stoves": [{"id": "B1", "state": "idle", "cook_ticks_left": 5}]})
        self.assertBad({"customers": [_customer(order_status="assigned")],
                        "stoves": [{"id": "B1", "state": "cooking", "dish": DISH, "cook_ticks_left": 0}]})
        self.assertBad({"customers": [_customer(order_status="assigned")],
                        "stoves": [{"id": "B1", "state": "cooking", "dish": DISH, "cook_ticks_left": 361}]})

    def test_counters_and_reputation(self):
        self.assertBad({"customers": [_customer(patience_ticks_left=3601)]})
        self.assertBad({"customers": [_customer(patience_ticks_left=-1)]})
        self.assertBad({"reputation": 5.5})
        self.assertBad({"random_customers": "no"})


class ScenarioQuanStock(unittest.TestCase):
    def _code(self, block, inventory=None):
        """Chạy headless quan --ticks 0; trả mã thoát."""
        with Workdir() as w:
            args = ["--mode", "quan", "--seed", "1", "--ticks", "0", "--out", w.path("o.jsonl"),
                    "--scenario", write_json(w.path("s.json"), {"quan": block})]
            if inventory is not None:
                args += ["--inventory", write_json(w.path("inv.json"), {"items": inventory})]
            return run_headless(*args)[0]

    def test_reserved_over_stock_exit_2(self):
        self.assertEqual(self._code({"stock": [], "customers": [_customer()]}), 2)
        self.assertEqual(self._code({"customers": [_customer()]}, inventory=[]), 2)

    def test_reserved_within_stock_exit_0(self):
        self.assertEqual(self._code({"stock": [item("I1")], "customers": [_customer()]}), 0)
        self.assertEqual(self._code({"customers": [_customer()]}, inventory=[item("I1")]), 0)


if __name__ == "__main__":
    unittest.main()

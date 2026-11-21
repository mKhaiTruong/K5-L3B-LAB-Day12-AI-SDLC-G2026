"""Unit test luật quán (PRD-0 mục F, Quán): lát 3 (khách) + lát 4 (bếp, bưng, phục vụ, tiền)."""

import json
import unittest

from chonoi.inputs import InputState
from chonoi.runner import Session


def tuning():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)["tuning"]


def make(scn=None, seed=1, inventory=None):
    block = (scn or {}).get("quan", {})  # Session nhận đúng khối `quan` (như scenario.load_scenario trả về)
    return Session("quan", tuning(), block, seed, inventory)  # contract v1.1: preset đã có T1..T4


def stk(**counts):
    """Kho cá thể v1.2 từ số đếm: stk(ca_loc=2) -> [I1 ca_loc 100, I2 ca_loc 100]; id tăng theo thứ tự khai."""
    out, n = [], 0
    for kind, c in counts.items():
        for _ in range(c):
            n += 1
            out.append({"id": f"I{n}", "kind": kind, "fresh": 100})
    return out


def idle():
    return InputState((0.0, 0.0), {}, set())


def press():
    return InputState((0.0, 0.0), {}, {"interact"})


def run(sess, n, first=None):
    """Chạy n bước (bước đầu có thể nhấn E); trả list (tick, name, data)."""
    out = []
    for i in range(n):
        for e in sess.step(first if (i == 0 and first) else idle()):
            out.append((e["tick"], e["name"], e["data"]))
    return out


def names(ev):
    return [e[1] for e in ev]


class Customers(unittest.TestCase):
    def test_first_customer_at_tick_120_with_reservation(self):
        s = make({"quan": {"stock": stk(ca_loc=1)}})
        ev = run(s, 120)
        self.assertEqual(names(ev), ["customer_arrived"])
        self.assertEqual(ev[0][0], 120)
        self.assertEqual(ev[0][2], {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"})
        c = s.sim.customers[0]
        self.assertEqual(c["order_tick"], 120)
        self.assertEqual(c["patience_ticks_left"], 3600)
        self.assertEqual(c["reserved"], ["I1"])

    def test_no_dish_when_empty_stock(self):
        s = make()
        ev = run(s, 120)
        self.assertEqual(ev, [(120, "no_dish", {})])
        self.assertEqual(s.sim.customers, [])

    def test_no_free_table_skips_without_no_dish(self):
        # v1.1: preset có 4 bàn -> phải chiếm đủ T1..T4 thì lượt đến mới bị bỏ qua (không phát no_dish)
        cs = [{"id": f"C{i}", "table_id": f"T{i}", "dish_id": "ca_loc_nuong_trui"} for i in range(1, 5)]
        s = make({"quan": {"stock": stk(ca_loc=5), "customers": cs}})
        self.assertEqual(run(s, 120 + 900), [])

    def test_random_customers_false(self):
        s = make({"quan": {"stock": stk(ca_loc=1), "random_customers": False}})
        self.assertEqual(run(s, 300), [])

    def test_reservation_excludes_available_stock(self):
        # kho chỉ đủ 1 phần; khách 1 giữ chỗ, khách 2 (bàn khác) phải no_dish
        sc = {"quan": {"stock": stk(ca_loc=1)}}
        s = make(sc)
        ev = run(s, 120 + 900)
        self.assertEqual(names(ev), ["customer_arrived", "no_dish"])

    def test_patience_leave_cuts_reputation(self):
        sc = {"quan": {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}],
                       "stock": stk(ca_loc=1), "random_customers": False}}
        s = make(sc)
        ev = run(s, 3600)
        self.assertEqual(ev, [(3600, "customer_left",
                               {"order_id": "C1", "table_id": "T1", "reason": "patience", "reputation": 2.5})])
        self.assertEqual(s.sim.customers, [])


class Kitchen(unittest.TestCase):
    def scn(self, **extra):
        q = {"player": {"pos": [2, 8]}, "stock": stk(ca_loc=1), "random_customers": False,
             "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]}
        q.update(extra)
        return {"quan": q}

    def test_cook_pick_serve_pay_with_tip(self):
        s = make(self.scn())
        ev = run(s, 1, press())
        self.assertEqual(ev, [(1, "cook_started", {"stove_id": "B1", "order_id": "C1",
                                                    "dish_id": "ca_loc_nuong_trui", "items": [{"id": "I1", "kind": "ca_loc", "fresh": 100 - 1 / 240}],
                                                    "base_price": 59})])  # kho hao 1 đơn vị ở đầu bước: floor(60 × 99.996%)
        self.assertEqual(s.sim.stock, [])
        self.assertEqual(s.sim.customers[0]["order_status"], "assigned")
        ev = run(s, 360)  # cook_s = 6 -> 360 tick
        self.assertEqual(ev, [(361, "dish_ready", {"stove_id": "B1", "order_id": "C1", "dish_id": "ca_loc_nuong_trui"})])
        ev = run(s, 1, press())
        self.assertEqual(names(ev), ["dish_picked"])
        self.assertEqual(s.sim.hand["order_id"], "C1")
        s.sim.pos = [9.0, 2.0]  # dịch tới bàn
        ev = run(s, 1, press())
        # kiên nhẫn đã giảm 363 tick -> còn 3237/3600 >= 0.5 -> boa floor(59*0.2) = 11
        self.assertEqual(ev[0][1:], ("served", {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                                                "patience_ticks_left": 3237, "base_price": 59, "tip": 11}))
        ev = run(s, 600)  # eat_s = 10
        self.assertEqual(ev[0][1], "paid")
        self.assertEqual(ev[0][2]["amount"], 70)  # 59 + 11
        self.assertEqual((s.sim.money, s.sim.earned, s.sim.shift_earned), (70, 70, 70))
        self.assertAlmostEqual(s.sim.reputation, 3.2)

    def test_no_tip_below_ratio(self):
        s = make(self.scn(hand={"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
                          customers=[{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                                      "order_status": "assigned", "patience_ticks_left": 1799, "reserved": []}],
                          stock=[], player={"pos": [9, 2]}))
        ev = run(s, 1, press())
        self.assertEqual(ev[0][2]["tip"], 0)  # 1798/3600 < 0.5

    def test_tip_at_exact_ratio(self):
        s = make(self.scn(hand={"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
                          customers=[{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                                      "order_status": "assigned", "patience_ticks_left": 1801, "reserved": []}],
                          stock=[], player={"pos": [9, 2]}))
        ev = run(s, 1, press())
        self.assertEqual(ev[0][2]["patience_ticks_left"], 1800)
        self.assertEqual(ev[0][2]["tip"], 12)  # đúng 0.5 vẫn có boa (>=)

    def test_wrong_order_at_table_ignored(self):
        s = make(self.scn(hand={"order_id": "C9", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
                          player={"pos": [9, 2]}))
        self.assertEqual(run(s, 1, press()), [])

    def test_serve_on_tick_patience_zero_is_valid(self):
        s = make(self.scn(hand={"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
                          customers=[{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                                      "order_status": "assigned", "patience_ticks_left": 1, "reserved": []}],
                          stock=[], player={"pos": [9, 2]}))
        ev = run(s, 1, press())
        self.assertEqual(names(ev), ["served"])
        self.assertEqual(ev[0][2]["tip"], 0)

    def test_leaving_customer_discards_dish_in_hand(self):
        s = make(self.scn(hand={"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
                          customers=[{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                                      "order_status": "assigned", "patience_ticks_left": 1, "reserved": []}],
                          stock=[], player={"pos": [2, 8]}))
        ev = run(s, 1)
        self.assertEqual(names(ev), ["customer_left"])
        self.assertIsNone(s.sim.hand)

    def test_stove_before_table_on_tie(self):
        # bếp và bàn cùng khoảng cách: bếp trước. Đặt bàn T1 chồng lên bếp B1.
        s = make(self.scn(tables=[{"id": "T1", "pos": [2, 8]}], player={"pos": [2, 8]}))
        self.assertEqual(names(run(s, 1, press())), ["cook_started"])

    def test_closing_paying_and_leaving(self):
        sc = self.scn(time_left_ticks=2,
                      customers=[{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                                  "state": "eating", "order_status": "served", "eat_ticks_left": 500,
                                  "base_price": 60, "tip": 12, "reserved": []},
                                 {"id": "C2", "table_id": "T2", "dish_id": "goi_bong_sung"}],
                      stock=stk(bong_sung=2))
        s = make(sc)
        ev = run(s, 2)
        self.assertEqual(names(ev), ["paid", "customer_left", "quan_end"])
        self.assertEqual(ev[0][2]["reason"], "closing")
        self.assertEqual(ev[1][2]["reason"], "closing")
        self.assertEqual(ev[1][2]["reputation"], 3.2)  # chỉ cộng boa của C1, không trừ khi closing
        self.assertTrue(s.done)

    def test_deterministic_same_seed(self):
        a = run(make({"quan": {"stock": stk(ca_loc=3, bong_sung=4)}}, seed=5), 3000)
        b = run(make({"quan": {"stock": stk(ca_loc=3, bong_sung=4)}}, seed=5), 3000)
        self.assertEqual(a, b)


def fx(i, kind="ca_loc", fresh=100):
    return {"id": i, "kind": kind, "fresh": fresh}


CUST = {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}  # công thức: ca_loc ×1, giá 60


class FreshStock(unittest.TestCase):
    """Kho cá thể v1.2: hao 1 đơn vị/tick, spoiled một lần, giữ chỗ theo id, giá theo độ tươi."""

    def test_stock_decays_and_spoiled_once_by_id(self):
        s = make({"quan": {"stock": [fx("I10", fresh=30), fx("I2", fresh=30), fx("I3", fresh=31)],
                           "random_customers": False}})
        ev = run(s, 2)
        self.assertEqual(ev, [(1, "spoiled", {"item_id": "I2", "kind": "ca_loc", "location": "stock"}),
                              (1, "spoiled", {"item_id": "I10", "kind": "ca_loc", "location": "stock"})])
        self.assertEqual([x["fresh"] for x in s.sim.snapshot()["stock"]][:1], [30 - 2 / 240])  # I2 sau 2 tick
        self.assertEqual([x["id"] for x in s.sim.snapshot()["stock"]], ["I2", "I3", "I10"])

    def test_reserve_freshest_tie_by_id(self):
        s = make({"quan": {"stock": [fx("I1", fresh=80), fx("I2", fresh=90), fx("I3", fresh=90)]}})
        run(s, 120)
        self.assertEqual(s.sim.customers[0]["reserved"], ["I2"])

    def test_reserved_item_spoils_then_rereserve_once(self):
        # I1 (đang giữ) vừa ươn ở bước 1; I2 tươi nên giữ lại được
        sc = {"quan": {"stock": [fx("I1", fresh=30), fx("I2", fresh=80)], "random_customers": False,
                       "customers": [dict(CUST, reserved=["I1"])]}}
        s = make(sc)
        ev = run(s, 1)
        self.assertEqual(names(ev), ["spoiled"])
        c = s.sim.customers[0]
        self.assertEqual((c["order_status"], c["reserved"]), ("reserved", ["I2"]))

    def test_reserved_item_spoils_no_replacement_unfulfillable(self):
        sc = {"quan": {"stock": [fx("I1", fresh=30), fx("I2", fresh=29)], "random_customers": False,
                       "customers": [dict(CUST, reserved=["I1"])]}}
        s = make(sc)
        # I2 đã ươn từ đầu (fresh 29 < 30, không phát spoiled): chỉ I1 vừa ươn -> không còn cá tươi
        # (fixture reserved=I1 hợp lệ vì I1 fresh 30 chưa ươn lúc dựng)
        ev = run(s, 1)
        self.assertEqual(names(ev), ["spoiled"])
        c = s.sim.customers[0]
        self.assertEqual((c["order_status"], c["reserved"]), ("unfulfillable", []))
        self.assertEqual(run(s, 3000), [])  # không thử lại, không bàn giao; khách vẫn chờ tới hết kiên nhẫn

    def test_rereserve_releases_all_first(self):
        # C1 giữ I1 (sắp ươn), C2 giữ I2; I3 tươi hơn I2 nhưng tới tay C1 sau khi nhả vì C1 xét trước
        sc = {"quan": {"stock": [fx("I1", fresh=30), fx("I2", fresh=60), fx("I3", fresh=90)],
                       "random_customers": False,
                       "customers": [dict(CUST, reserved=["I1"]),
                                     dict(CUST, id="C2", table_id="T2", reserved=["I2"])]}}
        s = make(sc)
        run(s, 1)
        got = {c["id"]: (c["order_status"], c["reserved"]) for c in s.sim.customers}
        self.assertEqual(got, {"C1": ("reserved", ["I3"]), "C2": ("reserved", ["I2"])})

    def test_price_by_freshness_and_items_in_cook_started(self):
        sc = {"quan": {"player": {"pos": [2, 8]}, "stock": [fx("I1", fresh=50.5)], "random_customers": False,
                       "customers": [CUST]}}
        s = make(sc)
        ev = run(s, 1, press())
        d = ev[0][2]
        self.assertEqual(d["base_price"], 30)  # floor(60 × ~50.5%)
        self.assertEqual([x["id"] for x in d["items"]], ["I1"])
        self.assertEqual(s.sim.snapshot()["stock"], [])  # cá thể đã vào bếp, ra khỏi kho

    def test_cook_started_items_sorted_by_kind_then_id(self):
        # goi_bong_sung: bông súng ×? — dùng món nhiều loại: lẩu cá linh = ca_linh ×3 + bong_dien_dien ×1
        sc = {"quan": {"player": {"pos": [2, 8]}, "random_customers": False,
                       "stock": [fx("I1", "ca_linh"), fx("I2", "bong_dien_dien"), fx("I3", "ca_linh"), fx("I10", "ca_linh")],
                       "customers": [dict(CUST, dish_id="lau_ca_linh_dien_dien")]}}
        ev = run(make(sc), 1, press())
        self.assertEqual([(x["kind"], x["id"]) for x in ev[0][2]["items"]],
                         [("bong_dien_dien", "I2"), ("ca_linh", "I1"), ("ca_linh", "I3"), ("ca_linh", "I10")])

    def test_reserved_spoiled_or_unknown_in_fixture_exit_2(self):
        from chonoi.errors import BadInput
        for st, rs in (([fx("I1", fresh=20)], ["I1"]), ([fx("I1")], ["I9"])):
            with self.subTest(st=st), self.assertRaises(BadInput):
                make({"quan": {"stock": st, "random_customers": False, "customers": [dict(CUST, reserved=rs)]}})

    def test_unfulfillable_start_when_stock_cannot_cover(self):
        with self.assertRaises(Exception):
            make({"quan": {"stock": [], "random_customers": False, "customers": [CUST]}})  # reserved thiếu -> mã 2


if __name__ == "__main__":
    unittest.main()

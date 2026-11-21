"""Test chế độ day (contract v1.1, kho cá thể từ v1.2): vòng ngày, Shop, pause, scenario day, CLI --days."""

import json
import os
import tempfile
import unittest

from chonoi.errors import BadInput
from chonoi.headless import main
from chonoi.inputs import InputState
from chonoi.runner import Session
from chonoi.scenario import load_scenario


def tuning():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)["tuning"]


def hold_of(*kinds, fresh=100):
    """Giỏ cá thể v1.2: id I1, I2… theo thứ tự khai."""
    return [{"id": f"I{i}", "kind": k, "fresh": fresh} for i, k in enumerate(kinds, 1)]


def idle(**kw):
    edges = {k for k, v in kw.items() if v is True and k != "buy"}
    return InputState((0.0, 0.0), {}, edges, kw.get("buy"))


def fast(money=300, extra_gather=None, extra_quan=None, **day):
    """Scenario day: Út Sen đang ở bến (docked ở tick 1), giỏ có sẵn, không khách ngẫu nhiên."""
    g = {"hold": hold_of("ca_loc", "bong_sung", "bong_sung"), "random_fish": False, "player": {"pos": [2, 0]}}
    g.update(extra_gather or {})
    q = {"random_customers": False, "time_left_ticks": 5}
    q.update(extra_quan or {})
    d = {"money": money, "earned": money}
    d.update(day)
    return {"day": d, "gather": g, "quan": q}


def to_shop(s):
    """Chạy tới khi vào Shop; trả list event."""
    out = []
    first = True
    while s.sim.phase != "shop":
        out += s.step(idle(interact=True) if first else idle())
        first = False
    return out


class DayFlow(unittest.TestCase):
    def test_boot_events_and_first_phase(self):
        s = Session("day", tuning(), fast(), 1, days=1)
        boot = s.start_events()
        self.assertEqual([r["name"] for r in boot], ["day_start", "day_plan", "phase_start"])
        self.assertTrue(all(r["tick"] == 0 and r["phase"] == "gather" and r["day"] == 1 for r in boot))
        self.assertEqual(boot[1]["data"]["ingredients"], {"ca_loc": 3, "bong_sung": 6})

    def test_gather_to_quan_to_shop_and_stock_carried(self):
        s = Session("day", tuning(), fast(), 1, days=1)
        ev = s.step(idle(interact=True))
        self.assertEqual([e["name"] for e in ev], ["gather_end", "phase_start"])
        self.assertEqual((ev[0]["phase"], ev[1]["phase"]), ("gather", "quan"))
        # kho quán = giỏ lúc gather_end: cá thể nguyên vẹn (id giữ nguyên), hao 1 đơn vị/tick từ khi vào quán
        self.assertEqual([(it["id"], it["kind"]) for it in s.sim.sub.stock],
                         [("I1", "ca_loc"), ("I2", "bong_sung"), ("I3", "bong_sung")])
        # bước cập bến gather vẫn hao hàng có sẵn 1 lần (2 đơn vị) trước khi bàn giao; quán không trừ thêm lúc bàn giao
        self.assertEqual({it["u"] for it in s.sim.sub.stock}, {23998})
        snap = s.snapshot()
        self.assertEqual((snap["phase"], snap["phase_tick"], snap["day"]), ("quan", 0, 1))
        for _ in range(4):
            s.step(idle())
        ev = s.step(idle())
        self.assertEqual([e["name"] for e in ev], ["quan_end", "phase_start"])
        self.assertEqual((ev[0]["phase"], ev[1]["phase"]), ("quan", "shop"))
        stock = s.snapshot()["stock"]  # 2 đơn vị hao ở gather + 5 bước trong quán; Shop không hao
        self.assertEqual([x["id"] for x in stock], ["I1", "I2", "I3"])
        self.assertEqual({x["fresh"] for x in stock}, {100 - 7 / 240})

    def test_faint_gives_empty_stock(self):
        sc = fast(extra_gather={"hold": hold_of("ca_loc"), "player": {"pos": [50, 25], "hp": 1, "oxygen_ticks": 0}})
        s = Session("day", tuning(), sc, 1, days=1)
        ev = []
        while not ev or ev[-1]["name"] != "phase_start":
            ev = s.step(idle())
        self.assertEqual(s.sim.sub.stock, [])

    def test_money_earned_reputation_carry_over(self):
        sc = fast(money=150, reputation=4.0)
        s = Session("day", tuning(), sc, 1, days=1)
        to_shop(s)
        snap = s.snapshot()
        self.assertEqual((snap["money"], snap["earned"], snap["reputation"]), (150, 150, 4.0))

    def test_quan_menu_filtered_by_plan(self):
        # Ngày 1 chỉ có ca_loc_nuong_trui + goi_bong_sung; kho đủ lẩu cá linh nhưng khách không gọi
        sc = fast(extra_gather={"hold": hold_of("ca_linh", "ca_linh", "ca_linh", "bong_dien_dien")},
                  extra_quan={"random_customers": True, "time_left_ticks": 130})
        s = Session("day", tuning(), sc, 1, days=1)
        s.step(idle(interact=True))
        evs = []
        for _ in range(125):
            evs += s.step(idle())
        self.assertEqual([e["name"] for e in evs if e["name"] in ("customer_arrived", "no_dish")], ["no_dish"])


class ItemIdsAcrossDays(unittest.TestCase):
    def test_day2_prebuilt_hold_gets_new_ids_in_array_order(self):
        sc = fast(extra_gather={"hold": hold_of("ca_loc", "bong_sung")})
        s = Session("day", tuning(), sc, 1, days=2)
        d1 = [it["id"] for it in s.sim.sub.hold]
        to_shop(s)
        s.step(idle(shop_done=True))  # sang Ngày 2
        self.assertEqual(s.sim.day, 2)
        d2 = [it["id"] for it in s.sim.sub.hold]
        self.assertEqual(d1, ["I1", "I2"])
        self.assertEqual(d2, ["I3", "I4"])  # mới, theo thứ tự mảng, không trùng id Ngày 1
        self.assertEqual([it["kind"] for it in s.sim.sub.hold], ["ca_loc", "bong_sung"])


class Shop(unittest.TestCase):
    def shop(self, money, upgrades=None, days=2):
        sc = fast(money=money, **({"upgrades": upgrades} if upgrades else {}))
        s = Session("day", tuning(), sc, 1, days=days)
        to_shop(s)
        return s

    def test_buy_oxygen_then_hp(self):
        s = self.shop(700)
        ev = s.step(idle(buy="oxygen"))
        self.assertEqual(ev[0]["name"], "bought")
        self.assertEqual(ev[0]["data"], {"upgrade": "oxygen", "level": 1, "price": 200, "money": 500})
        ev = s.step(idle(buy="oxygen"))
        self.assertEqual(ev[0]["data"], {"upgrade": "oxygen", "level": 2, "price": 400, "money": 100})
        ev = s.step(idle(buy="oxygen"))
        self.assertEqual(ev[0]["name"], "buy_failed")
        self.assertEqual(ev[0]["data"], {"action": "oxygen", "reason": "max_level"})
        snap = s.snapshot()
        self.assertEqual((snap["money"], snap["earned"], snap["upgrades"]["oxygen"]), (100, 700, 2))
        self.assertEqual(snap["score"], 700 + 100 * 3)  # score dùng earned, không dùng money

    def test_buy_failed_funds_and_unknown_and_invalid_phase(self):
        s = self.shop(100)
        self.assertEqual(s.step(idle(buy="hp"))[0]["data"], {"action": "hp", "reason": "funds"})
        self.assertEqual(s.step(idle(buy="weapon"))[0]["data"], {"action": "weapon", "reason": "unknown"})
        self.assertEqual(s.sim.money, 100)

    def test_buy_ignored_outside_shop(self):
        s = Session("day", tuning(), fast(), 1, days=1)
        self.assertEqual([e["name"] for e in s.step(idle(buy="oxygen", interact=True))], ["gather_end", "phase_start"])

    def test_upgrade_active_from_next_day_only(self):
        s = self.shop(300)
        self.assertEqual(s.snapshot()["active_upgrades"], {"oxygen": 0, "hp": 0})
        s.step(idle(buy="oxygen"))
        snap = s.snapshot()
        self.assertEqual((snap["upgrades"]["oxygen"], snap["active_upgrades"]["oxygen"]), (1, 0))
        ev = s.step(idle(shop_done=True))
        self.assertEqual([e["name"] for e in ev], ["shop_end", "day_start", "day_plan", "phase_start"])
        self.assertEqual(ev[0]["data"], {"reason": "done"})
        self.assertEqual([e["day"] for e in ev], [1, 2, 2, 2])
        snap = s.snapshot()
        self.assertEqual((snap["day"], snap["phase"], snap["active_upgrades"]["oxygen"]), (2, "gather", 1))
        self.assertEqual(snap["player"]["oxygen_max_ticks"], 2700)  # 45 s
        self.assertEqual(s.sim.days_completed, 1)
        self.assertNotIn("days_completed", snap)  # chỉ có ở dòng end

    def test_hp_upgrade_applied_next_day(self):
        s = self.shop(300, upgrades={"hp": 1})
        s.step(idle(shop_done=True))
        p = s.snapshot()["player"]
        self.assertEqual((p["hp"], p["hp_max"]), (4, 4))

    def test_buy_before_shop_done_in_same_tick(self):
        s = self.shop(300)
        ev = s.step(idle(buy="oxygen", shop_done=True))
        self.assertEqual([e["name"] for e in ev][:2], ["bought", "shop_end"])
        self.assertEqual(s.snapshot()["upgrades"]["oxygen"], 1)

    def test_shop_closes_after_600_ticks(self):
        s = self.shop(0)
        for _ in range(599):
            self.assertEqual(s.step(idle()), [])
        ev = s.step(idle())
        self.assertEqual(ev[0]["name"], "shop_end")
        self.assertEqual(ev[0]["data"], {"reason": "time"})

    def test_last_day_ends_run(self):
        s = self.shop(0, days=1)
        ev = s.step(idle(shop_done=True))
        self.assertEqual([e["name"] for e in ev], ["shop_end"])
        self.assertTrue(s.done)
        end = s.end_row()
        self.assertEqual((end["reason"], end["days_completed"]), ("days_complete", 1))


class Pause(unittest.TestCase):
    def test_pause_freezes_sim_and_resume_runs_same_tick(self):
        s = Session("day", tuning(), fast(extra_gather={"player": {"pos": [30, 5]}}), 1, days=1)
        s.step(idle())
        t0 = s.sim.sub.time_left_ticks
        ev = s.step(idle(pause=True))
        self.assertEqual([(e["name"], e["tick"], e["day"]) for e in ev], [("paused", 2, 1)])
        self.assertEqual(s.snapshot()["state"], "paused")
        self.assertEqual(s.step(idle(interact=True)), [])  # còn pause: bỏ qua cạnh hành động
        self.assertEqual(s.sim.sub.time_left_ticks, t0)
        ev = s.step(idle(pause=True))
        self.assertEqual(ev[0]["name"], "resumed")
        self.assertEqual(s.sim.sub.time_left_ticks, t0 - 1)  # resumed -> gameplay chạy ngay trong bước đó
        snap = s.snapshot()
        self.assertEqual((snap["tick"], snap["sim_tick"], snap["state"]), (4, 2, "playing"))

    def test_pause_works_in_gather_and_quan_modes(self):
        for mode, blk in (("gather", {}), ("quan", {})):
            s = Session(mode, tuning(), blk, 1)
            self.assertEqual(s.step(idle(pause=True))[0]["name"], "paused")
            self.assertEqual(s.sim_tick, 0)
            self.assertEqual(s.step(idle(pause=True))[0]["name"], "resumed")
            self.assertEqual(s.sim_tick, 1)

    def test_shop_timer_frozen_while_paused(self):
        s = Session("day", tuning(), fast(), 1, days=1)
        to_shop(s)
        s.step(idle())
        s.step(idle(pause=True))
        for _ in range(700):
            self.assertEqual(s.step(idle()), [])
        self.assertEqual(s.sim.phase_tick, 1)


class Scenario(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return load_scenario(p, "day", tuning())

    def test_valid(self):
        self.assertIn("day", self.load(fast()))

    def test_forbidden_and_bad(self):
        bads = [
            {"quan": {"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]}},
            {"quan": {"reputation": 3.0}},
            {"day": {"money": 10, "earned": 5}},
            {"day": {"upgrades": {"oxygen": 3}}},
            {"day": {"upgrades": {"weapon": 1}}},
            {"day": {"day_plan": [{"day": 6, "dishes": {"lau_mam": 1}}]}},
            {"day": {"day_plan": [{"day": 1, "dishes": {"lau_mam": 1}, "ingredients": {"ca_loc": 1}}]}},
            {"day": {"bogus": 1}},
            {"gather": {"bogus": 1}},
        ]
        for b in bads:
            with self.subTest(b=b), self.assertRaises(BadInput):
                self.load(b)

    def test_day_plan_override_and_recompute(self):
        sc = self.load({"day": {"day_plan": [{"day": 1, "dishes": {"lau_mam": 2}}]}})
        s = Session("day", tuning(), sc, 1, days=1)
        self.assertEqual(s.sim.plan["ingredients"], {"ca_linh": 4, "ca_keo": 2, "keo_neo": 2, "bong_dien_dien": 2})


class PlanAndOrder(unittest.TestCase):
    def test_prefab_customer_must_be_in_plan(self):
        # Ngày 1 chỉ có ca_loc_nuong_trui + goi_bong_sung; lau_mam không thuộc kế hoạch -> mã 2
        c = [{"id": "C1", "table_id": "T1", "dish_id": "lau_mam", "order_status": "unfulfillable"}]
        with self.assertRaises(BadInput):
            Session("day", tuning(), fast(extra_quan={"customers": c}), 1, days=1)
        ok = [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung"}]
        Session("day", tuning(), fast(extra_quan={"customers": ok}), 1, days=1)

    def test_prefab_customer_checked_for_every_day_run(self):
        c = [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung"}]  # D2 không có goi_bong_sung
        with self.assertRaises(BadInput):
            Session("day", tuning(), fast(extra_quan={"customers": c}), 1, days=2)

    def test_start_events_written_before_tick0_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.jsonl")
            self.assertEqual(main(["--mode", "day", "--seed", "1", "--ticks", "0", "--out", out]), 0)
            with open(out, encoding="utf-8") as f:
                rows = [json.loads(x) for x in f]
        self.assertEqual([r.get("name", r["type"]) for r in rows],
                         ["day_start", "day_plan", "phase_start", "snapshot", "end"])


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.jsonl")
            code = main(["--seed", "1", "--ticks", "30", "--out", out, *args])
            rows = []
            if os.path.exists(out):
                with open(out, encoding="utf-8") as f:
                    rows = [json.loads(x) for x in f]
            return code, rows

    def test_day_runs_and_is_deterministic(self):
        a = self.run_cli("--mode", "day", "--days", "2")
        b = self.run_cli("--mode", "day", "--days", "2")
        self.assertEqual(a, b)
        code, rows = a
        self.assertEqual(code, 0)
        first_snap = next(r for r in rows if r["type"] == "snapshot")
        self.assertEqual((first_snap["mode"], first_snap["tick"], first_snap["phase"]), ("day", 0, "gather"))
        self.assertEqual(rows[-1]["type"], "end")
        self.assertEqual(rows[-1]["days_completed"], 0)

    def test_days_validation_exit_2(self):
        for args in (["--mode", "day", "--days", "0"], ["--mode", "day", "--days", "6"],
                     ["--mode", "gather", "--days", "1"], ["--mode", "day", "--inventory", "x.json"]):
            with self.subTest(args=args):
                self.assertEqual(self.run_cli(*args)[0], 2)

    def test_default_days_is_one(self):
        code, rows = self.run_cli("--mode", "day")
        self.assertEqual(code, 0)


class MonstersByDay(unittest.TestCase):
    def test_m2_appears_from_day_3(self):
        """Bố trí Cá Sấu theo Ngày: M1 từ Ngày 1, M2 từ Ngày 3 (spawns.from_day)."""
        s = Session("day", tuning(), fast(), 1, days=3)
        seen = {}
        for day in (1, 2, 3):
            seen[day] = [m["id"] for m in s.snapshot()["monsters"]]
            to_shop(s)
            s.step(idle(shop_done=True))
        self.assertEqual(seen, {1: ["M1"], 2: ["M1"], 3: ["M1", "M2"]})
        self.assertTrue(s.done)


if __name__ == "__main__":
    unittest.main()

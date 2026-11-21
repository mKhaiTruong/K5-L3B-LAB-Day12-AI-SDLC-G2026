"""Chế độ `day` (contract v1.1): chơi trọn vòng ngày gather -> quan -> shop, tối đa DAYS Ngày.

`DaySim` bọc `GatherSim` và `QuanSim` (KHÔNG nhân đôi luật), chỉ lo:
  - dựng sim từng pha (kho quán = giỏ lúc gather_end; tiền/earned/uy tín mang xuyên Ngày);
  - Shop (mua oxygen/hp, hiệu lực từ Ngày kế); kế hoạch ngày; đổi pha và Ngày.
Pause nằm ở `runner.Session` (dùng chung cho cả ba mode).

Giả định đã chốt (ghi ở docs/clarify.md):
  - mỗi pha dùng IdAllocator mới (id N1.., F1.., C1.. lặp lại mỗi Ngày); `Streams(seed)` dùng chung cả lượt chơi;
  - v1.2: id cá thể I1, I2… cấp từ MỘT `ItemIds` giữ ở đây, tăng liên tục xuyên pha và xuyên Ngày; giỏ lúc
    gather_end bàn giao nguyên cá thể (giữ id, độ tươi) sang kho quán; kho quán dư cuối Ngày không mang sang Ngày sau;
  - scenario gather/quan là mẫu khởi tạo ÁP DỤNG MỖI Ngày.
"""

import copy

from ..contract import DAYS, plan_ingredients
from ..errors import BadInput
from ..fresh import Freshness, ItemIds, by_id, public
from ..ids import IdAllocator
from .gather import GatherSim
from .quan import QuanSim

UPGRADES = ("oxygen", "hp")
FIELD = {"oxygen": "oxygen_max_s", "hp": "hp_max"}


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, days=1):
        if not 1 <= days <= DAYS:
            raise BadInput(f"--days phải trong [1, {DAYS}]")
        self.tuning = tuning
        self.rng = streams
        self.days = days
        self.menu = tuning["menu"]
        self.shop_t = tuning["shop"]
        d = scenario.get("day", {})
        self.gather_scn = scenario.get("gather", {})
        self.quan_scn = scenario.get("quan", {})
        self.money = d.get("money", 0)
        self.earned = d.get("earned", 0)
        self.reputation = d.get("reputation", tuning["quan"]["reputation_initial"])
        self.upgrades = {k: int(d.get("upgrades", {}).get(k, 0)) for k in UPGRADES}
        self.plans = self._build_plans(tuning["day_plan"], d.get("day_plan", []))
        self._check_customers_in_plan()
        self.day = 1
        self.days_completed = 0
        self.done = False
        self.reason = None
        self.sim_changed = False  # True ở tick vừa đổi pha: runner ghi snapshot (pha mới, phase_tick = 0)
        self.phase_tick = 0
        self.active = dict(self.upgrades)
        self.sub = None
        self.stock = []  # kho quán lúc vào Shop, dạng public (chỉ để snapshot)
        self.fresh = Freshness(tuning)
        self.item_ids = ItemIds()
        self._boot = []  # sự kiện tick 0
        self._start_gather(self._boot)

    # ---------- kế hoạch ----------

    def _build_plans(self, preset, overrides):
        plans = {p["day"]: {"dishes": dict(p["dishes"]), "ingredients": dict(p["ingredients"])} for p in preset}
        for o in overrides:
            ing = plan_ingredients(o["dishes"], self.menu)
            if "ingredients" in o and o["ingredients"] != ing:
                raise BadInput(f"day_plan[{o['day']}].ingredients không bằng tổng công thức × số suất")
            plans[o["day"]] = {"dishes": dict(o["dishes"]), "ingredients": ing}
        return plans

    def _check_customers_in_plan(self):
        """Khách dựng sẵn trong quan.customers phải gọi món thuộc kế hoạch của MỌI Ngày sẽ chạy (mã 2)."""
        for c in self.quan_scn.get("customers", []):
            for day in range(1, self.days + 1):
                if c["dish_id"] not in self.plans[day]["dishes"]:
                    raise BadInput(f"quan.customers.{c['id']}: món {c['dish_id']} không thuộc kế hoạch Ngày {day}")

    @property
    def plan(self):
        return self.plans[self.day]

    # ---------- giao diện cho runner ----------

    @property
    def phase(self):
        return self._phase

    @property
    def time_left_ticks(self):
        return self.sub.time_left_ticks if self._phase != "shop" else max(0, self.shop_t["max_ticks"] - self.phase_tick)

    def snapshot(self):
        snap = self.sub.snapshot() if self._phase != "shop" else {"stock": list(self.stock)}
        snap.update({"day": self.day, "day_plan": self.plan, "upgrades": dict(self.upgrades),
                     "active_upgrades": dict(self.active)})
        return snap

    def end_extra(self):
        return {"days_completed": self.days_completed}

    # ---------- dựng pha ----------

    def _day_tuning(self):
        """Tuning gather với cấp nâng cấp ĐANG ÁP DỤNG (đã sao ở đầu Ngày)."""
        t = copy.deepcopy(self.tuning)
        for up in UPGRADES:
            lvl = self.active[up]
            if lvl:
                t["gather"][FIELD[up]] = self.shop_t["upgrades"][up][lvl - 1][FIELD[up]]
        return t

    def _start_gather(self, events):
        self.active = dict(self.upgrades)
        self._phase = "gather"
        self.phase_tick = 0
        scn = self.gather_scn
        if self.day > 1 and scn.get("hold"):
            # từ Ngày 2 giỏ dựng sẵn là cá thể MỚI: id mới theo thứ tự mảng (PRD), id I* không lặp lại
            scn = dict(scn, hold=[dict(it, id=self.item_ids.new()) for it in scn["hold"]])
        self.sub = GatherSim(self._day_tuning(), scn, self.rng, IdAllocator(),
                              day=self.day, item_ids=self.item_ids)
        events += [("day_start", {}, "gather", self.day),
                   ("day_plan", copy.deepcopy(self.plan), "gather", self.day),
                   ("phase_start", {}, "gather", self.day)]

    def _hand_over(self):
        """Giỏ lúc gather_end -> kho quán: cá thể nguyên vẹn (id, độ tươi) do gather v1.2 cấp."""
        out = [dict(it) for it in self.sub.hold]
        self.item_ids.reserve_all(out)
        return out

    def _start_quan(self, items, events):
        self._phase = "quan"
        self.phase_tick = 0
        q = QuanSim(self.tuning, self.quan_scn, self.rng, IdAllocator(), inventory=items,
                    plan_dishes=set(self.plan["dishes"]), item_ids=self.item_ids)
        q.money, q.earned, q.reputation = self.money, self.earned, self.reputation
        self.sub = q
        events.append(("phase_start", {}, "quan", self.day))

    def _start_shop(self, events):
        self._phase = "shop"
        self.phase_tick = 0
        self.stock = [public(it) for it in by_id(self.sub.stock)]
        self.sub = None
        events.append(("phase_start", {}, "shop", self.day))

    # ---------- một bước ----------

    def step(self, inp):
        self.sim_changed = False
        self.phase_tick += 1
        if self._phase == "shop":
            return self._step_shop(inp)
        phase, day = self._phase, self.day
        events = [(n, d, phase, day) for n, d in self.sub.step(inp)]
        if not self.sub.done:
            return events
        self.sim_changed = True
        if phase == "gather":
            self._start_quan(self._hand_over(), events)
        else:
            q = self.sub
            self.money, self.earned, self.reputation = q.money, q.earned, q.reputation
            self._start_shop(events)
        return events

    def _step_shop(self, inp):
        events, day = [], self.day
        buy = getattr(inp, "buy", None)
        if buy is not None:
            events += self._buy(buy)
        closing = None
        if inp.pressed("shop_done"):
            closing = "done"
        elif self.phase_tick >= self.shop_t["max_ticks"]:
            closing = "time"
        if closing:
            events.append(("shop_end", {"reason": closing}, "shop", day))
            self.days_completed += 1
            self.sim_changed = True
            if self.day >= self.days:
                self.done, self.reason = True, "days_complete"
            else:
                self.day += 1
                self._start_gather(events)
        return events

    def _buy(self, action):
        day = self.day
        if action not in UPGRADES:
            return [("buy_failed", {"action": action, "reason": "unknown"}, "shop", day)]
        levels = self.shop_t["upgrades"][action]
        nxt = self.upgrades[action] + 1
        if nxt > len(levels):
            return [("buy_failed", {"action": action, "reason": "max_level"}, "shop", day)]
        price = levels[nxt - 1]["price"]
        if self.money < price:
            return [("buy_failed", {"action": action, "reason": "funds"}, "shop", day)]
        self.money -= price
        self.upgrades[action] = nxt
        return [("bought", {"upgrade": action, "level": nxt, "price": price, "money": self.money}, "shop", day)]

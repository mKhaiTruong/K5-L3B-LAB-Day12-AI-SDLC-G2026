"""Buổi sáng — Lặn & Hái (`gather`). KHUNG: bơi, chặn mép, đồng hồ, cập bến, xuất kho.

Mặt cắt dòng sông nhìn NGANG: vị trí `[x, d]` (x sang phải, `d` độ sâu hướng xuống, d = 0 là mặt nước).
`move = [x, d]`: thành phần thứ hai DƯƠNG = bơi xuống. Hướng mặt là góc từ +x, dương = xuống.

Đã làm sẵn để smoke test chạy được: bơi + tăng/giảm tốc, chặn mép (d không âm), đồng hồ và hết giờ,
cập bến (`interact` trong vùng bến -> `gather_end` reason `docked`), xuất kho, snapshot đầy đủ trường gather.

Nhóm viết tiếp (đúng thứ tự một bước trong PRD mục 13.8, "Gather"):
  TODO(nhóm, lát 1): bơi + oxy + biên + giỏ
      - oxy: dưới nước (d > surface_depth) trừ 1 tick/tick, mặt nước hồi oxygen_refill_per_tick, kẹp [0, max]
      - ngạt: oxy = 0 và đang dưới nước -> đếm zero_oxy_ticks, đủ choke_interval_ticks thì -1 Máu (choke)
      - Máu về 0 -> ngất (faint, gather_end reason `fainted`, mất toàn bộ giỏ, kho rỗng)
      - sự kiện dive / surface / oxygen_empty / choke / faint
      - giỏ: thứ tự nhặt (LIFO), sức chứa hold_capacity
  TODO(nhóm, lát 2): hái + bắt cá + cập bến + kho
      - hái nút ở mặt nước (gather, hold_full), nút mọc lại (node_regrown đã có phần đếm ngược)
      - bắt đàn cá bằng `catch` (fish_caught, hold_full, hồi chiêu catch_cd_ticks, chỉ khi dưới nước)
      - cập bến xét TRƯỚC hái (đã có); ghi kho đúng một lần do runner lo
Các tính năng của phase sau chưa nằm trong khung này.
"""

import math

from ..ids import id_key, sort_by_id
from ..fresh import Freshness, ItemIds, by_id, decay, lifo_drop, new_item, parse_items, public
from ..inventory import KINDS
from .monsters import MonsterSet
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, day=1, item_ids=None):
        t = tuning["gather"]
        self.t = t
        self.rng = streams
        self.ids = ids
        self.day = day
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_max = int(round(t["oxygen_max_s"] * TICK))
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", t["hp_max"])
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        # giỏ (v1.2): mảng cá thể nội bộ {id,kind,u} theo thứ tự vào giỏ, cuối mảng là mới nhất
        self.fresh = Freshness(tuning)
        self.item_ids = item_ids if item_ids is not None else ItemIds()  # day truyền MỘT ItemIds xuyên pha/Ngày
        self.hold = parse_items(scenario.get("hold", []), "gather.hold", KINDS)
        self.item_ids.reserve_all(self.hold)
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        # nút và đàn cá: scenario THAY THẾ danh sách mặc định; random_fish=false tắt cá mặc định
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        # cá (TICKET-02 1.1): random_fish=true -> cá bơi + sinh theo lịch; false -> cá fixture đứng yên
        self.phase_tick = 0
        self.fish_active = scenario.get("random_fish", True)
        src_fish = scenario.get("fish", [])
        self.fish = [{"id": f["id"], "kind": f["kind"], "pos": [float(c) for c in f["pos"]],
                      "heading_deg": float(f.get("heading_deg", 0)), "age_ticks": f.get("age_ticks", 0)}
                     for f in src_fish]
        for coll in (self.nodes, self.fish):
            for e in coll:
                ids.reserve(e["id"])
        if "fish" not in scenario and self.fish_active:
            for _ in range(int(t["fish_initial"])):
                self._spawn_one()
        # thủy quái (TICKET-02 1.2): scenario.monsters THAY danh sách mặc định; mặc định lọc theo from_day
        self.monsters = MonsterSet(t, scenario.get("monsters"), day)
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self) -> list:
        """Kho bàn giao (v1.2): mảng cá thể `{id,kind,fresh}` sắp theo id; giỏ rỗng -> `[]`."""
        return [public(it) for it in by_id(self.hold)]

    def snapshot(self) -> dict:
        return {
            "player": {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.t["hp_max"], "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": [public(it) for it in self.hold], "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "pos": n["pos"], "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "fish": [{"id": f["id"], "pos": f["pos"], "kind": f["kind"], "heading_deg": f["heading_deg"],
                      "age_ticks": f["age_ticks"]}
                     for f in sort_by_id(self.fish)],
            "monsters": self.monsters.snapshot(),
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        self.phase_tick += 1
        # 1. đồng hồ và hàng có sẵn: giảm bộ đếm, nút mọc lại
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        # độ tươi hàng có sẵn trong giỏ (hàng mới vào ở bước này hao từ bước sau)
        events += decay(self.hold, self.fresh.gather_per_tick, self.fresh, "hold")
        # 2. bơi + chặn mép, rồi dive/surface và oxy theo d cuối bước
        was_surface = self._at_surface()
        self._move(inp)
        self._surface_events(was_surface, events)
        if self._oxygen_and_choke(events):
            return events
        # 2b. thủy quái theo id, tối đa một lần chạm
        if self._monsters_step(events):
            return events
        # 3. interact: bến trước, rồi hái
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            self._try_gather(events)
        # 4. bắt cá
        if inp.pressed("catch"):
            self._try_catch(events)
        # 5. hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
            return events
        # 6. còn giờ: cá bơi, rồi sinh thêm theo lịch
        if self.fish_active:
            self._swim_fish()
            if self.phase_tick % self.t["fish_spawn_ticks"] == 0 and len(self.fish) < self.t["fish_max"]:
                f = self._spawn_one()
                if f is not None:
                    events.append(("fish_spawned", {"id": f["id"], "kind": f["kind"], "pos": list(f["pos"])}))
        return events

    def _spawn_one(self):
        """Sinh một đàn ở điểm sinh còn trống (cách mọi đàn > clearance). Hết điểm -> None."""
        t = self.t
        kinds = sorted(t["fish_weights"])
        pts = {k: sorted((float(x), float(d)) for x in t["fish_spawn_x"] for d in t["fish_spawn_depths"][k]
                         if all(math.dist((x, d), f["pos"]) > t["fish_spawn_clearance"] for f in self.fish))
               for k in kinds}
        ok = [k for k in kinds if pts[k]]
        if not ok:
            return None
        rng = self.rng.get("fish_spawn")
        r = rng.random() * sum(t["fish_weights"][k] for k in ok)
        kind, acc = ok[-1], 0.0
        for k in ok:
            acc += t["fish_weights"][k]
            if r < acc:
                kind = k
                break
        x, d = pts[kind][rng.randrange(len(pts[kind]))]
        f = {"id": self.ids.new("F"), "kind": kind, "pos": [x, d],
             "heading_deg": rng.random() * 360.0, "age_ticks": 0}
        self.fish.append(f)
        return f

    def _swim_fish(self):
        """Mỗi đàn bơi fish_speed/60 m; đổi hướng ở age 120, 240…; phản xạ ở mép x và dải độ sâu loài."""
        t = self.t
        step = t["fish_speed"] / TICK
        rng = self.rng.get("fish_turn")
        xlo, xhi = t["fish_x"]
        for f in sort_by_id(self.fish):
            f["age_ticks"] += 1
            if f["age_ticks"] % t["fish_turn_ticks"] == 0:
                f["heading_deg"] = rng.random() * 360.0
            h = math.radians(f["heading_deg"])
            hx, hd = math.cos(h), math.sin(h)
            dlo, dhi = t["fish_depths"][f["kind"]]
            x = f["pos"][0] + hx * step
            d = f["pos"][1] + hd * step
            flip_x = x < xlo or x > xhi
            flip_d = d < dlo or d > dhi
            if x < xlo:
                x = 2 * xlo - x
            elif x > xhi:
                x = 2 * xhi - x
            if d < dlo:
                d = 2 * dlo - d
            elif d > dhi:
                d = 2 * dhi - d
            f["pos"] = [x, d]
            if flip_x or flip_d:
                f["heading_deg"] = math.degrees(math.atan2(-hd if flip_d else hd, -hx if flip_x else hx)) % 360

    # --- tiện ích ---------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _try_gather(self, events):
        """Hái nút ready gần nhất trong interact_radius (chỉ ở mặt nước): gather / hold_full."""
        if not self._at_surface():
            return
        cands = [n for n in self.nodes
                 if n["regrow_ticks"] == 0 and math.dist(self.pos, n["pos"]) <= self.t["interact_radius"]]
        if not cands:
            return
        n = min(cands, key=lambda n: (math.dist(self.pos, n["pos"]), id_key(n["id"])))
        amount = self.t["node_yield"]
        free = self.t["hold_capacity"] - len(self.hold)
        if free < amount:
            events.append(("hold_full", {"action": "gather", "node_id": n["id"], "required": amount, "free": free}))
            return
        self.hold.extend(new_item(self.item_ids, n["kind"], self.fresh) for _ in range(amount))
        n["regrow_ticks"] = int(round(self.t["regrow_s"] * 60))
        events.append(("gather", {"node_id": n["id"], "kind": n["kind"], "amount": amount}))

    def _try_catch(self, events):
        """Bắt đàn gần nhất trong catch_radius (hết hồi, dưới nước): fish_caught / hold_full."""
        if self.catch_cd_ticks > 0 or self._at_surface():
            return
        cands = [f for f in self.fish if math.dist(self.pos, f["pos"]) <= self.t["catch_radius"]]
        if not cands:
            return
        f = min(cands, key=lambda f: (math.dist(self.pos, f["pos"]), id_key(f["id"])))
        y = self.t["fish_yield"][f["kind"]]
        free = self.t["hold_capacity"] - len(self.hold)
        if free < y:
            events.append(("hold_full", {"action": "catch", "fish_id": f["id"], "required": y, "free": free}))
            return
        self.hold.extend(new_item(self.item_ids, f["kind"], self.fresh) for _ in range(y))
        self.fish.remove(f)
        self.catch_cd_ticks = int(round(self.t["catch_cooldown_s"] * 60))
        events.append(("fish_caught", {"fish_id": f["id"], "kind": f["kind"], "yield": y}))

    def _surface_events(self, was_surface, events):
        """dive/surface khi đổi phía biên mặt nước giữa đầu và cuối bước."""
        now = self._at_surface()
        if was_surface and not now:
            events.append(("dive", {"pos": list(self.pos)}))
        elif not was_surface and now:
            events.append(("surface", {"pos": list(self.pos)}))

    def _oxygen_and_choke(self, events) -> bool:
        """Oxy theo d cuối bước; ngạt/ngất. Trả True nếu vừa ngất (step() phải return ngay)."""
        if self._at_surface():
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + self.t["oxygen_refill_per_tick"])
            self.zero_oxy_ticks = 0
            return False
        before = self.oxygen_ticks
        self.oxygen_ticks = max(0, self.oxygen_ticks - 1)
        if before > 0 and self.oxygen_ticks == 0:
            events.append(("oxygen_empty", {"oxygen_ticks": 0}))
        # đếm ngạt (kể cả bước vừa chạm 0); đủ chu kỳ thì choke, Máu 0 thì ngất
        if self.oxygen_ticks == 0:
            self.zero_oxy_ticks += 1
        if self.zero_oxy_ticks >= self.t["choke_interval_ticks"]:
            self.zero_oxy_ticks = 0
            self.hp -= 1
            events.append(("choke", {"hp": self.hp}))
            if self.hp <= 0:
                lost = lifo_drop(self.hold, len(self.hold))  # LIFO: vào giỏ sau bỏ trước
                events.append(("faint", {"cause": "choke", "lost": lost, "hp": 0}))
                self._finish("fainted", events)
                return True
        return False

    def _monsters_step(self, events) -> bool:
        """Thủy quái di chuyển; chạm khi hết bất tử: -1 Máu, mất hàng LIFO, bất tử. Trả True nếu vừa ngất."""
        hit = self.monsters.step(self.pos)
        if hit is None or self.invuln_ticks > 0:
            return False
        lost = self.monsters.apply_hit(hit, self.pos, self.hold)
        self.hp -= 1
        self.invuln_ticks = self.monsters.invuln_ticks
        events.append(("monster_hit", {"monster_id": hit["id"], "hp": self.hp, "lost": lost, "pos": list(self.pos)}))
        if self.hp > 0:
            return False
        rest = lifo_drop(self.hold, len(self.hold))  # LIFO: vào giỏ sau bỏ trước
        events.append(("faint", {"cause": "monster", "lost": rest, "hp": 0}))
        self._finish("fainted", events)
        return True

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": self.inventory_items()}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])

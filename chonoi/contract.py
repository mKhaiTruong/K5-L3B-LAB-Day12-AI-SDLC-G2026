"""Đọc game.contract.json và kiểm dải hợp lệ của tuning (Test Contract v1.1, TICKET-02)."""

import json
import os

from .errors import BadInput
from .inventory import KINDS

FISH_SPECIES = ("ca_linh", "ca_loc", "ca_keo")
NODE_SPECIES = ("bong_dien_dien", "bong_sung", "keo_neo")
DAYS = 5

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _between(name, v, lo, hi):
    if not _num(v) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải trong [{lo}, {hi}], đang là {v!r}")


def load_contract(path=DEFAULT_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được {path}: {e}")
    validate_tuning(c.get("tuning"))
    return c


def _int_between(name, v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải là số nguyên trong [{lo}, {hi}], đang là {v!r}")


def _pos_in(name, pos, bounds, keys):
    if (not isinstance(pos, list) or len(pos) != 2 or not all(_num(c) for c in pos)):
        raise BadInput(f"tuning.{name} phải là [số, số]")
    for c, k in zip(pos, keys):
        lo, hi = bounds[k]
        if not (lo <= c <= hi):
            raise BadInput(f"tuning.{name} nằm ngoài vùng {k} ∈ [{lo}, {hi}]")


def _bounds(name, b, keys):
    if not isinstance(b, dict) or set(b) != set(keys):
        raise BadInput(f"tuning.{name}.bounds phải có đúng khóa {list(keys)}")
    for k in keys:
        v = b[k]
        if not (isinstance(v, list) and len(v) == 2 and all(_num(c) for c in v) and v[0] == 0 and v[1] > 0):
            raise BadInput(f"tuning.{name}.bounds.{k} phải là [0, số dương]")


def _validate_gather(g):
    """Dải hợp lệ P1 theo PRD mục 13.2."""
    _between("gather.duration_s", g.get("duration_s"), 60, 600)
    _bounds("gather", g.get("bounds"), ("x", "d"))
    b = g["bounds"]
    _between("gather.dock_radius", g.get("dock_radius"), 0.5, 5)
    _between("gather.interact_radius", g.get("interact_radius"), 0.5, 5)
    _between("gather.catch_radius", g.get("catch_radius"), 0.5, 5)
    _between("gather.swim_speed", g.get("swim_speed"), 1, 10)
    _between("gather.catch_cooldown_s", g.get("catch_cooldown_s"), 0, 10)
    _between("gather.oxygen_max_s", g.get("oxygen_max_s"), 10, 120)
    _int_between("gather.ramp_max_ticks", g.get("ramp_max_ticks"), 0, 6)
    _int_between("gather.hold_capacity", g.get("hold_capacity"), 4, 30)
    _int_between("gather.hp_max", g.get("hp_max"), 1, 99)
    _int_between("gather.oxygen_refill_per_tick", g.get("oxygen_refill_per_tick"), 1, 10_000)
    _int_between("gather.choke_interval_ticks", g.get("choke_interval_ticks"), 1, 10_000)
    _int_between("gather.node_yield", g.get("node_yield"), 1, 12)
    _between("gather.regrow_s", g.get("regrow_s"), 0.1, 600)
    _between("gather.surface_depth", g.get("surface_depth"), 0, 5)
    _pos_in("gather.dock_pos", g.get("dock_pos"), b, ("x", "d"))
    _pos_in("gather.start_pos", g.get("start_pos"), b, ("x", "d"))
    if not _num(g.get("start_heading_deg")):
        raise BadInput("tuning.gather.start_heading_deg phải là số")
    fy = g.get("fish_yield")
    if not isinstance(fy, dict) or set(fy) != set(FISH_SPECIES):
        raise BadInput(f"tuning.gather.fish_yield phải có đúng {list(FISH_SPECIES)}")
    for k, v in fy.items():
        _int_between(f"gather.fish_yield.{k}", v, 1, g["hold_capacity"])
    nodes = g.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise BadInput("tuning.gather.nodes phải là mảng không rỗng")
    seen, kinds = set(), set()
    for n in nodes:
        if not isinstance(n, dict) or not isinstance(n.get("id"), str) or n["id"] in seen:
            raise BadInput("tuning.gather.nodes: mỗi nút cần id duy nhất")
        seen.add(n["id"])
        if n.get("kind") not in NODE_SPECIES:
            raise BadInput(f"tuning.gather.nodes.{n['id']}: kind phải là một trong {list(NODE_SPECIES)}")
        kinds.add(n["kind"])
        _pos_in(f"gather.nodes.{n['id']}.pos", n.get("pos"), b, ("x", "d"))
        if n["pos"][1] != 0:
            raise BadInput(f"tuning.gather.nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
    if kinds != set(NODE_SPECIES):
        raise BadInput(f"tuning.gather.nodes phải có ít nhất một nút mỗi loại {list(NODE_SPECIES)}")
    _validate_fish(g, b)
    _validate_monsters(g.get("monsters"), b)


def _per_species(name, m, check):
    """Kiểm map loài -> giá trị có đủ 3 loài cá, mỗi giá trị qua `check`."""
    if not isinstance(m, dict) or set(m) != set(FISH_SPECIES):
        raise BadInput(f"tuning.gather.{name} phải có đúng {list(FISH_SPECIES)}")
    for sp, v in m.items():
        check(f"gather.{name}.{sp}", v)


def _range_in(name, r, lo, hi):
    if not (isinstance(r, list) and len(r) == 2 and all(_num(c) for c in r) and lo <= r[0] <= r[1] <= hi):
        raise BadInput(f"tuning.{name} phải là [a, b] với {lo} ≤ a ≤ b ≤ {hi}")


def _validate_fish(g, b):
    """Cá bơi/sinh v1.1 (TICKET-02 mục 1.1)."""
    (x_lo, x_hi), (d_lo, d_hi) = b["x"], b["d"]
    _int_between("gather.fish_max", g.get("fish_max"), 1, 100)
    _int_between("gather.fish_initial", g.get("fish_initial"), 0, g["fish_max"])
    _between("gather.fish_speed", g.get("fish_speed"), 0, 10)
    _int_between("gather.fish_turn_ticks", g.get("fish_turn_ticks"), 1, 100_000)
    _int_between("gather.fish_spawn_ticks", g.get("fish_spawn_ticks"), 1, 100_000)
    _between("gather.fish_spawn_clearance", g.get("fish_spawn_clearance"), 0, 100)
    _range_in("gather.fish_x", g.get("fish_x"), x_lo, x_hi)
    _per_species("fish_depths", g.get("fish_depths"),
                 lambda n, v: _range_in(n, v, g["surface_depth"], d_hi))
    xs = g.get("fish_spawn_x")
    fx = g["fish_x"]
    if not (isinstance(xs, list) and xs and all(_num(x) and fx[0] <= x <= fx[1] for x in xs)):
        raise BadInput("tuning.gather.fish_spawn_x phải là danh sách x nằm trong fish_x")

    def depth_list(name, v, sp_name):
        lo, hi = g["fish_depths"][sp_name]
        if not (isinstance(v, list) and v and all(_num(d) and lo <= d <= hi for d in v)):
            raise BadInput(f"tuning.{name} phải là danh sách độ sâu trong fish_depths.{sp_name}")

    _per_species("fish_spawn_depths", g.get("fish_spawn_depths"),
                 lambda n, v: depth_list(n, v, n.rsplit(".", 1)[1]))
    _per_species("fish_weights", g.get("fish_weights"),
                 lambda n, v: _between(n, v, 1e-9, 1))


def _validate_monsters(m, b):
    """Cá Sấu v1.1 (TICKET-02 mục 1.2)."""
    if not isinstance(m, dict) or not isinstance(m.get("species"), dict) or not m["species"]:
        raise BadInput("tuning.gather.monsters phải có species")
    for sp, s in m["species"].items():
        n = f"gather.monsters.species.{sp}"
        for key in ("patrol_speed", "chase_speed", "detect_radius", "exit_radius", "hit_radius", "recoil_dist"):
            _between(f"{n}.{key}", s.get(key), 0, 100)
        _int_between(f"{n}.recoil_ticks", s.get("recoil_ticks"), 1, 100_000)
        _range_in(f"{n}.depths", s.get("depths"), b["d"][0], b["d"][1])
    _int_between("gather.monsters.invuln_ticks", m.get("invuln_ticks"), 0, 100_000)
    _between("gather.monsters.loss_ratio", m.get("loss_ratio"), 0, 1)
    spawns = m.get("spawns")
    if not isinstance(spawns, list):
        raise BadInput("tuning.gather.monsters.spawns phải là mảng")
    seen = set()
    for s in spawns:
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or s["id"] in seen:
            raise BadInput("tuning.gather.monsters.spawns: mỗi con cần id duy nhất")
        seen.add(s["id"])
        n = f"gather.monsters.spawns.{s['id']}"
        if s.get("kind") not in m["species"]:
            raise BadInput(f"tuning.{n}: kind phải thuộc species")
        _pos_in(f"{n}.pos", s.get("pos"), b, ("x", "d"))
        wps = s.get("waypoints")
        if not (isinstance(wps, list) and len(wps) == 2):
            raise BadInput(f"tuning.{n}.waypoints phải có đúng 2 điểm")
        for i, wp in enumerate(wps):
            _pos_in(f"{n}.waypoints[{i}]", wp, b, ("x", "d"))
        _int_between(f"{n}.from_day", s.get("from_day"), 1, DAYS)


def validate_tuning(t):
    if not isinstance(t, dict):
        raise BadInput("thiếu khối tuning")
    g, q, menu = t.get("gather"), t.get("quan"), t.get("menu")
    if not isinstance(g, dict) or not isinstance(q, dict) or not isinstance(menu, dict):
        raise BadInput("tuning phải có gather, quan, menu")
    _validate_gather(g)
    # Quán: dải hợp lệ P1 (PRD mục 13.2)
    _between("quan.duration_s", q.get("duration_s"), 60, 600)
    _bounds("quan", q.get("bounds"), ("x", "z"))
    _between("quan.patience_s", q.get("patience_s"), 20, 180)
    _between("quan.walk_speed", q.get("walk_speed"), 1, 10)
    _between("quan.interact_radius", q.get("interact_radius"), 0.5, 5)
    _int_between("quan.ramp_max_ticks", q.get("ramp_max_ticks", 6), 0, 6)
    _between("quan.eat_s", q.get("eat_s"), 0.1, 600)
    _between("quan.customer_interval_s", q.get("customer_interval_s"), 0.1, 600)
    _int_between("quan.first_customer_tick", q.get("first_customer_tick"), 1, int(q["duration_s"] * 60) - 1)
    if not (_num(q.get("tip_rate")) and q["tip_rate"] > 0 and _num(q.get("left_reputation_delta"))
            and q["left_reputation_delta"] < 0):
        raise BadInput("tip_rate phải > 0 và left_reputation_delta phải < 0")
    ratio = q.get("tip_min_patience_ratio")
    if not (_num(ratio) and 0 < ratio <= 1):
        raise BadInput("quan.tip_min_patience_ratio phải thuộc (0, 1]")
    if not (_num(q.get("tip_reputation")) and q["tip_reputation"] > 0):
        raise BadInput("quan.tip_reputation phải > 0")
    if q.get("burn_s") is not None:
        raise BadInput("burn_s phải là null ở Phase 1")
    for arr in ("stoves", "tables"):
        items = q.get(arr)
        ids = [e.get("id") for e in items] if isinstance(items, list) else None
        if not ids or len(set(ids)) != len(ids):
            raise BadInput(f"tuning.quan.{arr} phải là mảng có id duy nhất")
        for e in items:
            _pos_in(f"quan.{arr}.{e['id']}.pos", e.get("pos"), q["bounds"], ("x", "z"))
    for dish_id, d in menu.items():
        price, cook = d.get("price"), d.get("cook_s")
        if isinstance(price, bool) or not isinstance(price, int) or price <= 0 or not _num(cook) or cook <= 0:
            raise BadInput(f"menu.{dish_id}: price (nguyên) và cook_s phải > 0")
        recipe = d.get("recipe")
        if not isinstance(recipe, dict) or not recipe or set(recipe) - set(KINDS):
            raise BadInput(f"menu.{dish_id}.recipe phải là map nguyên liệu hợp lệ -> số lượng")
        for k, v in recipe.items():
            _int_between(f"menu.{dish_id}.recipe.{k}", v, 1, 100)
    _validate_freshness(t.get("freshness"))
    _validate_day_plan(t.get("day_plan"), menu)
    _validate_shop(t.get("shop"))


def _validate_freshness(f):
    """Độ tươi v1.2 (TICKET-03): initial, gather_decay_per_s, quan_decay_per_s, spoiled_below."""
    keys = ("initial", "gather_decay_per_s", "quan_decay_per_s", "spoiled_below")
    if not isinstance(f, dict) or set(f) != set(keys):
        raise BadInput(f"tuning.freshness phải có đúng {list(keys)}")
    _between("freshness.initial", f["initial"], 0, 100)
    _between("freshness.spoiled_below", f["spoiled_below"], 0, f["initial"])
    for k in ("gather_decay_per_s", "quan_decay_per_s"):
        _between(f"freshness.{k}", f[k], 0, 100)


def plan_ingredients(dishes: dict, menu: dict) -> dict:
    """Tính tổng nguyên liệu của một kế hoạch ngày.

    Args:
        dishes: map id món -> số suất.
        menu: thực đơn trong tuning (`menu`).

    Returns:
        Map kind -> tổng số lượng, vd `{"ca_loc": 3, "bong_sung": 6}` cho D1.
    """
    total = {}
    for dish_id, n in dishes.items():
        for k, q in menu[dish_id]["recipe"].items():
            total[k] = total.get(k, 0) + q * n
    return total


def _validate_day_plan(plan, menu):
    """Kế hoạch D1–D5: dishes thuộc menu, ingredients = tổng công thức × số suất."""
    if not isinstance(plan, list) or [p.get("day") for p in plan if isinstance(p, dict)] != list(range(1, DAYS + 1)):
        raise BadInput(f"tuning.day_plan phải là {DAYS} mục với day = 1..{DAYS} theo thứ tự")
    for p in plan:
        n = f"day_plan[{p['day']}]"
        dishes = p.get("dishes")
        if not isinstance(dishes, dict) or not dishes or set(dishes) - set(menu):
            raise BadInput(f"tuning.{n}.dishes phải là map id món (có trong menu) -> số suất")
        for dish_id, v in dishes.items():
            _int_between(f"{n}.dishes.{dish_id}", v, 1, 100)
        if p.get("ingredients") != plan_ingredients(dishes, menu):
            raise BadInput(f"tuning.{n}.ingredients phải bằng tổng công thức × số suất")


def _validate_shop(shop):
    """Shop: max_ticks và các cấp nâng cấp oxygen/hp (giá nguyên dương, cấp 1..n theo thứ tự)."""
    if not isinstance(shop, dict) or not isinstance(shop.get("upgrades"), dict):
        raise BadInput("tuning.shop phải có max_ticks và upgrades")
    _int_between("shop.max_ticks", shop.get("max_ticks"), 1, 100_000)
    fields = {"oxygen": ("oxygen_max_s", 10, 120), "hp": ("hp_max", 1, 99)}
    for up, (field, lo, hi) in fields.items():
        levels = shop["upgrades"].get(up)
        if not isinstance(levels, list) or [lv.get("level") for lv in levels] != list(range(1, len(levels) + 1)):
            raise BadInput(f"tuning.shop.upgrades.{up} phải là mảng cấp 1..n theo thứ tự")
        for lv in levels:
            _int_between(f"shop.upgrades.{up}[{lv['level']}].price", lv.get("price"), 1, 1_000_000)
            _between(f"shop.upgrades.{up}[{lv['level']}].{field}", lv.get(field), lo, hi)

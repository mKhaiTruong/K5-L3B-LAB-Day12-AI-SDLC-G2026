"""Nạp và kiểm scenario (Contract D). Trả về dict của đúng khối theo mode.

KHUNG: kiểm cú pháp, id trùng, bộ đếm âm, khoang vượt sức chứa, trường lạ.
TODO(nhóm): bổ sung kiểm mâu thuẫn mức luật mà nhóm cần (khách giữ chỗ quá kho, đơn assigned
phải có đúng một món, khách eating thiếu giá/tip...) — xem PRD-0 mục D và 'Mâu thuẫn -> mã 2'.
"""

import json
import math

from .contract import plan_ingredients
from .errors import BadInput
from .fresh import Freshness, parse_items
from .inventory import KINDS_P1, validate_items

GATHER_KEYS = {"player", "hold", "nodes", "fish", "random_fish", "time_left_ticks", "monsters"}
MONSTER_KEYS = {"id", "kind", "pos", "waypoints", "target_idx", "state", "state_ticks_left", "recoil_dir"}
MONSTER_STATES = ("patrol", "chase", "recoil")  # stunned chỉ có khi bật mở rộng Lao (nhóm không làm)
DAY_KEYS = {"money", "earned", "reputation", "upgrades", "day_plan"}
DAY_FORBIDDEN_QUAN = ("stock", "reputation")  # v1.1 mục 4.3: cấm khi chạy day
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
NODE_KINDS = ("bong_dien_dien", "bong_sung", "keo_neo")
FISH_KINDS = ("ca_linh", "ca_loc", "ca_keo")
NODE_KEYS = {"id", "kind", "pos", "regrow_ticks"}
FISH_KEYS = {"id", "kind", "pos", "heading_deg", "age_ticks"}
QUAN_PLAYER_KEYS = {"pos", "vel"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}


def _check_ids(name, arr):
    if not isinstance(arr, list):
        raise BadInput(f"{name} phải là mảng")
    seen = set()
    for e in arr:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"]:
            raise BadInput(f"{name}: mỗi phần tử cần id (chuỗi khác rỗng)")
        if e["id"] in seen:
            raise BadInput(f"{name}: id trùng {e['id']}")
        seen.add(e["id"])


def load_scenario(path, mode: str, tuning: dict) -> dict:
    """Nạp file scenario và kiểm theo Test Contract (mục D v1.0 + mục 4.3 v1.1).

    Args:
        path: đường dẫn file scenario, hoặc None nếu không truyền `--scenario`.
        mode: `gather`, `quan` hoặc `day`.
        tuning: khối `tuning` của game.contract.json.

    Returns:
        Với `gather`/`quan`: dict của đúng khối đó (thiếu khối -> `{}`).
        Với `day`: dict có đủ ba khóa `{"day": {...}, "gather": {...}, "quan": {...}}`,
        khối thiếu là `{}`. `gather`/`quan` là mẫu khởi tạo mỗi Ngày.

    Raises:
        BadInput: khi file sai cú pháp, khối sai mode hoặc dữ liệu mâu thuẫn (mã 2).
    """
    if path is None:
        return {"day": {}, "gather": {}, "quan": {}} if mode == "day" else {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được scenario {path}: {e}")
    if not isinstance(data, dict) or not set(data) <= {"gather", "quan", "day"}:
        raise BadInput("scenario chỉ được có khối 'gather', 'quan' hoặc 'day'")
    if mode == "day":
        out = {k: data.get(k, {}) for k in ("day", "gather", "quan")}
        for k, block in out.items():
            if not isinstance(block, dict):
                raise BadInput(f"khối {k} phải là object")
        bad = [k for k in DAY_FORBIDDEN_QUAN if k in out["quan"]]
        if bad:
            raise BadInput(f"chạy day không được khai quan.{bad[0]} (dùng gather.hold / day.reputation)")
        _validate_day(out["day"], tuning)
        _check_block(out["gather"], "gather", tuning)
        _check_block(out["quan"], "quan", tuning)
        return out
    if set(data) - {mode}:
        raise BadInput(f"khối sai mode: chạy --mode {mode} chỉ nhận khối '{mode}'")
    block = data.get(mode, {})
    _check_block(block, mode, tuning)
    return block


def _check_block(block, mode, tuning):
    """Kiểm một khối gather/quan: trường lạ, time_left_ticks, rồi luật riêng của mode."""
    if not isinstance(block, dict):
        raise BadInput(f"khối {mode} phải là object")
    allowed = GATHER_KEYS if mode == "gather" else QUAN_KEYS
    extra = set(block) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong {mode}: {sorted(extra)}")
    dur = int(round(tuning[mode]["duration_s"] * 60))
    if "time_left_ticks" in block:
        t = block["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
    if mode == "gather":
        _validate_gather(block, tuning)
    else:
        _validate_quan(block, tuning)


def _validate_day(d, tuning):
    """Khối day: tiền/earned/uy tín/cấp nâng cấp đầu kỳ và day_plan ghi đè (v1.1 mục 4.3)."""
    extra = set(d) - DAY_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong day: {sorted(extra)}")
    for key in ("money", "earned"):
        if key in d:
            _nonneg_int(f"day.{key}", d[key])
    money, earned = d.get("money", 0), d.get("earned", 0)
    if money > 0 and "earned" not in d:
        raise BadInput("day: có money đầu kỳ thì phải khai cả earned")
    if money > earned:
        raise BadInput("day: cần 0 ≤ money ≤ earned")
    q = tuning["quan"]
    if "reputation" in d and not (_num(d["reputation"]) and q["reputation_min"] <= d["reputation"] <= q["reputation_max"]):
        raise BadInput(f"day.reputation phải là số trong [{q['reputation_min']}, {q['reputation_max']}]")
    ups = d.get("upgrades", {})
    shop_ups = tuning["shop"]["upgrades"]
    if not isinstance(ups, dict) or set(ups) - set(shop_ups):
        raise BadInput(f"day.upgrades phải là map trong {sorted(shop_ups)} -> cấp")
    for up, lv in ups.items():
        _nonneg_int(f"day.upgrades.{up}", lv)
        if lv > len(shop_ups[up]):
            raise BadInput(f"day.upgrades.{up} vượt cấp tối đa {len(shop_ups[up])}")
    plan = d.get("day_plan", [])
    if not isinstance(plan, list):
        raise BadInput("day.day_plan phải là mảng")
    menu, days, seen = tuning["menu"], len(tuning["day_plan"]), set()
    for p in plan:
        if not isinstance(p, dict) or set(p) - {"day", "dishes", "ingredients"} or "dishes" not in p:
            raise BadInput("day.day_plan: mỗi mục là {day, dishes, ingredients?}")
        n = p.get("day")
        if isinstance(n, bool) or not isinstance(n, int) or not (1 <= n <= days) or n in seen:
            raise BadInput(f"day.day_plan: day phải là số nguyên 1..{days}, không trùng")
        seen.add(n)
        dishes = p["dishes"]
        if not isinstance(dishes, dict) or not dishes or set(dishes) - set(menu):
            raise BadInput(f"day.day_plan[{n}].dishes phải là map id món (có trong menu) -> số suất")
        for dish_id, v in dishes.items():
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                raise BadInput(f"day.day_plan[{n}].dishes.{dish_id} phải là số nguyên dương")
        if "ingredients" in p and p["ingredients"] != plan_ingredients(dishes, menu):
            raise BadInput(f"day.day_plan[{n}].ingredients khác tổng công thức × số suất")


def _validate_monster(m, g, bounds):
    """Một Cá Sấu fixture: kind, vị trí trong dải độ sâu loài, 2 waypoint, trạng thái và timer khớp nhau."""
    mid = m["id"]
    extra = set(m) - MONSTER_KEYS
    if extra:
        raise BadInput(f"monsters.{mid}: trường lạ/chưa hỗ trợ {sorted(extra)}")
    species = g["monsters"]["species"]
    if m.get("kind") not in species:
        raise BadInput(f"monsters.{mid}: kind phải là một trong {sorted(species)}")
    lo, hi = species[m["kind"]]["depths"]
    wps = m.get("waypoints")
    if not (isinstance(wps, list) and len(wps) == 2):
        raise BadInput(f"monsters.{mid}.waypoints phải có đúng 2 điểm")
    for name, p in [("pos", m.get("pos"))] + [(f"waypoints[{i}]", wp) for i, wp in enumerate(wps)]:
        _pos(f"monsters.{mid}.{name}", p, bounds)
        if not (lo <= p[1] <= hi):
            raise BadInput(f"monsters.{mid}.{name} phải ở d ∈ [{lo}, {hi}] của loài {m['kind']}")
    if m.get("target_idx", 1) not in (0, 1) or isinstance(m.get("target_idx"), bool):
        raise BadInput(f"monsters.{mid}.target_idx phải là 0 hoặc 1")
    state = m.get("state", "patrol")
    if state not in MONSTER_STATES:
        raise BadInput(f"monsters.{mid}.state phải là một trong {MONSTER_STATES}")
    timer = m.get("state_ticks_left", 0)
    _nonneg_int(f"monsters.{mid}.state_ticks_left", timer)
    rdir = m.get("recoil_dir")
    if state == "recoil":
        rmax = species[m["kind"]]["recoil_ticks"]
        if not (1 <= timer <= rmax):
            raise BadInput(f"monsters.{mid}: recoil cần state_ticks_left trong [1, {rmax}]")
        if not (isinstance(rdir, list) and len(rdir) == 2 and all(_num(c) for c in rdir)
                and abs(math.hypot(*rdir) - 1) <= 1e-6):
            raise BadInput(f"monsters.{mid}: recoil cần recoil_dir là vector đơn vị")
    else:
        if timer:
            raise BadInput(f"monsters.{mid}: state {state} không có timer (state_ticks_left = 0)")
        if rdir is not None:
            raise BadInput(f"monsters.{mid}: recoil_dir chỉ khai khi state = recoil")


def _num(v):
    """Kiểm v là số hữu hạn (loại bool, NaN, ±Infinity)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _nonneg_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")


def _pos(name, pos, bounds, axes=("x", "d")):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for c, axis in zip(pos, axes):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng nước ({axis} ∈ [{lo}, {hi}])")


def _validate_gather(b, tuning):
    g = tuning["gather"]
    bounds = g["bounds"]
    for arr in ("nodes", "fish"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "hold" in b:
        h = b["hold"]
        if _v12(tuning):
            parse_items(h, "gather.hold", KINDS_P1)  # v1.2: mảng cá thể {id,kind,fresh}
        elif not isinstance(h, list) or any(k not in KINDS_P1 for k in h):
            raise BadInput("hold phải là mảng id nguyên liệu hợp lệ")
        if len(h) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
    p = b.get("player", {})
    if not isinstance(p, dict):
        raise BadInput("player phải là object")
    extra = set(p) - GATHER_PLAYER_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather.player: {sorted(extra)}")
    if "pos" in p:
        _pos("player.pos", p["pos"], bounds)
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, d]")
    if "heading_deg" in p and not _num(p["heading_deg"]):
        raise BadInput("player.heading_deg phải là số")
    for key in ("invuln_ticks", "catch_cd_ticks", "zero_oxy_ticks", "oxygen_ticks", "hp"):
        if key in p:
            _nonneg_int(f"player.{key}", p[key])
    omax = int(round(g["oxygen_max_s"] * 60))
    if "oxygen_ticks" in p and p["oxygen_ticks"] > omax:
        raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in p and not (1 <= p["hp"] <= g["hp_max"]):
        raise BadInput("player.hp phải trong [1, hp_max]")
    cd_max = int(round(g["catch_cooldown_s"] * 60))
    if "catch_cd_ticks" in p and p["catch_cd_ticks"] > cd_max:
        raise BadInput(f"player.catch_cd_ticks phải trong [0, {cd_max}]")
    inv_max = g["monsters"]["invuln_ticks"]
    if "invuln_ticks" in p and p["invuln_ticks"] > inv_max:
        raise BadInput(f"player.invuln_ticks phải trong [0, {inv_max}]")
    if "monsters" in b:
        _check_ids("monsters", b["monsters"])
        for m in b["monsters"]:
            _validate_monster(m, g, bounds)
    if "zero_oxy_ticks" in p:
        pos = p.get("pos", g["start_pos"])
        oxy = p.get("oxygen_ticks", omax)
        if p["zero_oxy_ticks"] > 59:
            raise BadInput("player.zero_oxy_ticks phải trong [0, 59]")
        if p["zero_oxy_ticks"] > 0 and not (oxy == 0 and pos[1] > g["surface_depth"]):
            raise BadInput("player.zero_oxy_ticks > 0 chỉ khi oxy = 0 và đang dưới nước")
    regrow_max = int(round(g["regrow_s"] * 60))
    for n in b.get("nodes", []):
        extra = set(n) - NODE_KEYS
        if extra:
            raise BadInput(f"nodes.{n['id']}: trường lạ/chưa hỗ trợ {sorted(extra)}")
        if n.get("kind") not in NODE_KINDS:
            raise BadInput(f"nodes.{n['id']}: kind phải là một trong {NODE_KINDS}")
        _pos(f"nodes.{n['id']}.pos", n.get("pos"), bounds)
        if n["pos"][1] != 0:
            raise BadInput(f"nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
        if "regrow_ticks" in n:
            _nonneg_int(f"nodes.{n['id']}.regrow_ticks", n["regrow_ticks"])
            if n["regrow_ticks"] > regrow_max:
                raise BadInput(f"nodes.{n['id']}.regrow_ticks phải trong [0, {regrow_max}]")
    for f in b.get("fish", []):
        extra = set(f) - FISH_KEYS
        if extra:
            raise BadInput(f"fish.{f['id']}: trường lạ/chưa hỗ trợ {sorted(extra)}")
        if f.get("kind") not in FISH_KINDS:
            raise BadInput(f"fish.{f['id']}: kind phải là một trong {FISH_KINDS}")
        _pos(f"fish.{f['id']}.pos", f.get("pos"), bounds)
        if f["pos"][1] <= g["surface_depth"]:
            raise BadInput(f"fish.{f['id']}: đàn cá phải ở dưới nước")
        if "heading_deg" in f and not _num(f["heading_deg"]):
            raise BadInput(f"fish.{f['id']}.heading_deg phải là số")
        if "age_ticks" in f:
            _nonneg_int(f"fish.{f['id']}.age_ticks", f["age_ticks"])


QUAN_STOVE_KEYS = {"id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks"}
QUAN_TABLE_KEYS = {"id", "pos"}
CUSTOMER_KEYS = {"id", "table_id", "dish_id", "order_tick", "state", "patience_ticks_left",
                 "eat_ticks_left", "order_status", "reserved", "base_price", "tip"}
DISH_KEYS = {"order_id", "dish_id", "base_price"}
STOVE_STATES = ("idle", "cooking", "ready")
CUSTOMER_STATES = ("waiting", "eating")
ORDER_STATUSES = ("reserved", "assigned", "unfulfillable", "served")


def _validate_quan(b, tuning):
    q, menu = tuning["quan"], tuning["menu"]
    qb = q["bounds"]
    for arr in ("stoves", "tables", "customers"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "stock" in b:
        stock = parse_items(b["stock"], "quan.stock", KINDS_P1) if _v12(tuning) else validate_items(b["stock"])
    if "random_customers" in b and not isinstance(b["random_customers"], bool):
        raise BadInput("random_customers phải là boolean")
    if "reputation" in b:
        r = b["reputation"]
        if not _num(r) or not (q["reputation_min"] <= r <= q["reputation_max"]):
            raise BadInput(f"reputation phải là số trong [{q['reputation_min']}, {q['reputation_max']}]")
    p = b.get("player", {})
    if not isinstance(p, dict) or set(p) - QUAN_PLAYER_KEYS:
        raise BadInput("quan.player chỉ có pos và vel")
    if "pos" in p:
        _pos("player.pos", p["pos"], qb, axes=("x", "z"))
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, z]")
    customers = {c["id"]: c for c in b.get("customers", [])}
    _validate_tables(b.get("tables", []), q)
    v12 = _v12(tuning)
    for c in customers.values():
        _validate_customer(c, q, menu, v12)
    if v12 and "stock" in b:  # giữ chỗ theo id kiểm được ngay khi scenario có stock; --inventory kiểm ở QuanSim
        check_reserved_ids(list(customers.values()), stock, tuning)
    # món đang ở bếp / trên tay: payload hợp lệ, nối đúng đơn assigned, mỗi đơn tối đa một món
    holders = {}  # order_id -> [(nơi giữ, payload món)]
    for s in b.get("stoves", []):
        dish = _validate_stove(s, q, menu)
        if dish is not None:
            holders.setdefault(dish["order_id"], []).append((f"stoves.{s['id']}", dish))
    if b.get("hand") is not None:
        _check_dish("hand", b["hand"], menu)
        holders.setdefault(b["hand"]["order_id"], []).append(("hand", b["hand"]))
    for oid, held in holders.items():
        where, dish = held[0]
        c = customers.get(oid)
        if c is None:
            raise BadInput(f"{where}: order_id {oid} không trỏ tới khách nào")
        if len(held) > 1:
            raise BadInput(f"đơn {oid} có nhiều hơn một món ({', '.join(w for w, _ in held)})")
        if c.get("order_status", "reserved") != "assigned":
            raise BadInput(f"{where}: đơn {oid} phải ở trạng thái assigned")
        if dish["dish_id"] != c["dish_id"]:
            raise BadInput(f"{where}: món {dish['dish_id']} không khớp đơn {oid} ({c['dish_id']})")
    for c in customers.values():
        if c.get("order_status", "reserved") == "assigned" and c["id"] not in holders:
            raise BadInput(f"customers.{c['id']}: đơn assigned phải có đúng một món ở bếp hoặc trên tay")


def _validate_tables(tables, q):
    known = {t["id"] for t in q["tables"]}
    for t in tables:
        if set(t) - QUAN_TABLE_KEYS:
            raise BadInput(f"tables.{t['id']}: trường lạ/chưa hỗ trợ {sorted(set(t) - QUAN_TABLE_KEYS)}")
        if t["id"] not in known:
            raise BadInput(f"tables.{t['id']}: id bàn không tồn tại")
        if "pos" in t:
            _pos(f"tables.{t['id']}.pos", t["pos"], q["bounds"], axes=("x", "z"))


def _validate_customer(c, q, menu, v12=False):
    cid = c["id"]
    extra = set(c) - CUSTOMER_KEYS
    if extra:
        raise BadInput(f"customers.{cid}: trường lạ/chưa hỗ trợ {sorted(extra)}")
    if not isinstance(c.get("table_id"), str) or c["table_id"] not in {t["id"] for t in q["tables"]}:
        raise BadInput(f"customers.{cid}: table_id phải là bàn có thật")
    if c.get("dish_id") not in menu:
        raise BadInput(f"customers.{cid}: dish_id phải là một trong {sorted(menu)}")
    state = c.get("state", "waiting")
    status = c.get("order_status", "reserved")
    if state not in CUSTOMER_STATES:
        raise BadInput(f"customers.{cid}: state phải là một trong {CUSTOMER_STATES}")
    if status not in ORDER_STATUSES:
        raise BadInput(f"customers.{cid}: order_status phải là một trong {ORDER_STATUSES}")
    for key in ("order_tick", "patience_ticks_left", "eat_ticks_left", "base_price", "tip"):
        if key in c:
            _nonneg_int(f"customers.{cid}.{key}", c[key])
    if c.get("patience_ticks_left", 0) > int(round(q["patience_s"] * 60)):
        raise BadInput(f"customers.{cid}.patience_ticks_left vượt kiên nhẫn tối đa")
    if c.get("eat_ticks_left", 0) > int(round(q["eat_s"] * 60)):
        raise BadInput(f"customers.{cid}.eat_ticks_left vượt thời gian ăn")
    reserved = c.get("reserved")
    if reserved is not None and v12:
        if not (isinstance(reserved, list) and all(isinstance(i, str) and i for i in reserved)
                and len(set(reserved)) == len(reserved)):
            raise BadInput(f"customers.{cid}.reserved phải là mảng id cá thể (chuỗi khác rỗng, không trùng)")
    elif reserved is not None:
        reserved = validate_items(reserved)
    if (state == "eating") != (status == "served"):
        raise BadInput(f"customers.{cid}: khách eating phải có order_status served (và ngược lại)")
    if state == "eating":
        if c.get("eat_ticks_left", 0) <= 0:
            raise BadInput(f"customers.{cid}: khách eating cần eat_ticks_left > 0")
        if "base_price" not in c or "tip" not in c:
            raise BadInput(f"customers.{cid}: khách eating phải khai base_price và tip đã chốt")
    if not v12 and status == "reserved" and reserved is not None and reserved != menu[c["dish_id"]]["recipe"]:
        raise BadInput(f"customers.{cid}: reserved khác công thức {c['dish_id']}")
    if status != "reserved" and reserved:
        raise BadInput(f"customers.{cid}: đơn {status} phải có phần giữ rỗng")


def _validate_stove(s, q, menu):
    """Kiểm một bản cập nhật bếp; trả payload món đang giữ (hoặc None)."""
    sid = s["id"]
    extra = set(s) - QUAN_STOVE_KEYS
    if extra:
        raise BadInput(f"stoves.{sid}: trường lạ/chưa hỗ trợ {sorted(extra)}")
    if sid not in {x["id"] for x in q["stoves"]}:
        raise BadInput(f"stoves.{sid}: id bếp không tồn tại")
    if "pos" in s:
        _pos(f"stoves.{sid}.pos", s["pos"], q["bounds"], axes=("x", "z"))
    state = s.get("state", "idle")
    if state not in STOVE_STATES:
        raise BadInput(f"stoves.{sid}: state phải là một trong {STOVE_STATES}")
    for key in ("cook_ticks_left", "ready_ticks"):
        if key in s:
            _nonneg_int(f"stoves.{sid}.{key}", s[key])
    dish = s.get("dish")
    cook = s.get("cook_ticks_left", 0)
    if state == "idle":
        if dish is not None or cook or s.get("ready_ticks", 0):
            raise BadInput(f"stoves.{sid}: bếp idle không có món và bộ đếm phải bằng 0")
        return None
    if dish is None:
        raise BadInput(f"stoves.{sid}: bếp {state} phải có món")
    _check_dish(f"stoves.{sid}.dish", dish, menu)
    if state == "cooking":
        cook_max = int(round(menu[dish["dish_id"]]["cook_s"] * 60))
        if not (1 <= cook <= cook_max) or s.get("ready_ticks", 0):
            raise BadInput(f"stoves.{sid}: bếp cooking cần cook_ticks_left trong [1, {cook_max}], ready_ticks = 0")
    elif cook:
        raise BadInput(f"stoves.{sid}: bếp ready cần cook_ticks_left = 0")
    return dish


def _check_dish(name, dish, menu):
    if not isinstance(dish, dict) or set(dish) != DISH_KEYS:
        raise BadInput(f"{name}: payload món phải đúng các khóa {sorted(DISH_KEYS)}")
    if not isinstance(dish["order_id"], str) or dish["dish_id"] not in menu:
        raise BadInput(f"{name}: order_id phải là chuỗi, dish_id phải có trong menu")
    if isinstance(dish["base_price"], bool) or not isinstance(dish["base_price"], int) or dish["base_price"] <= 0:
        raise BadInput(f"{name}: base_price phải là số nguyên dương")


def _v12(tuning) -> bool:
    """Contract v1.2 (có khối freshness) dùng cá thể cho hold/stock/reserved."""
    return "freshness" in tuning


def check_reserved_ids(customers, stock, tuning):
    """Kiểm giữ chỗ theo id cá thể (v1.2): trỏ tới cá thể có trong kho, chưa ươn, đủ đúng công thức,
    không dùng chung giữa các đơn; đơn không phải `reserved` thì phần giữ rỗng.

    Đơn `reserved` thiếu `reserved` KHÔNG kiểm ở đây: QuanSim cấp theo order_tick rồi id bàn
    (`fresh.reserve_recipe`), không đủ -> mã 2.

    Args:
        customers: khách (scenario hoặc đã dựng), `reserved` là mảng id.
        stock: kho cá thể nội bộ `{"id","kind","u"}` (xem `chonoi.fresh`).
        tuning: khối tuning (menu, freshness).

    Raises:
        BadInput: id không có trong kho, cá thể ươn, dùng chung, hoặc khác công thức (mã 2).
    """
    cfg = Freshness(tuning)
    by = {it["id"]: it for it in stock}
    used = set()
    for c in customers:
        ids = c.get("reserved")
        if ids is None:
            continue
        status = c.get("order_status", "reserved")
        if status != "reserved":
            if ids:
                raise BadInput(f"customers.{c['id']}: đơn {status} phải có phần giữ rỗng")
            continue
        kinds = {}
        for i in ids:
            if i not in by:
                raise BadInput(f"customers.{c['id']}.reserved: {i} không có trong kho")
            if i in used:
                raise BadInput(f"customers.{c['id']}.reserved: {i} đã bị đơn khác giữ")
            if cfg.spoiled(by[i]):
                raise BadInput(f"customers.{c['id']}.reserved: {i} đã ươn")
            used.add(i)
            kinds[by[i]["kind"]] = kinds.get(by[i]["kind"], 0) + 1
        if kinds != tuning["menu"][c["dish_id"]]["recipe"]:
            raise BadInput(f"customers.{c['id']}.reserved khác công thức {c['dish_id']}")


def check_reserved_within_stock(customers, stock):
    """Kiểm tổng phần giữ chỗ của khách không vượt tồn vật lý.

    Gọi sau khi đã điền `reserved` mặc định theo công thức (QuanSim), vì tồn có thể đến
    từ `--inventory` chứ không chỉ `scenario.quan.stock`.

    Args:
        customers: danh sách khách đã dựng, mỗi khách có `reserved` (kind -> số lượng).
        stock: tồn vật lý (kind -> số lượng), gồm cả phần đã giữ.

    Raises:
        BadInput: khi một nguyên liệu bị giữ nhiều hơn tồn (mã 2).
    """
    total = {}
    for c in customers:
        for kind, n in c.get("reserved", {}).items():
            total[kind] = total.get(kind, 0) + n
    for kind, n in sorted(total.items()):
        if n > stock.get(kind, 0):
            raise BadInput(f"giữ chỗ {kind} ×{n} vượt tồn ({stock.get(kind, 0)})")

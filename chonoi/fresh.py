"""Độ tươi cá thể (TICKET-03, contract v1.2) — dùng chung cho gather, quan, day, scenario, file kho.

Biểu diễn: mỗi cá thể là dict nội bộ `{"id": "I3", "kind": "ca_linh", "u": 24000}` với `u` là số
NGUYÊN đơn vị, `UNITS = 240` đơn vị mỗi điểm tươi (PRD gợi ý). Nhờ vậy:
  - gather hao 0.5/s = 2 đơn vị/tick, quán hao 0.25/s = 1 đơn vị/tick (số nguyên, không lệch float);
  - so ngưỡng 30 (= 7200 đơn vị) chính xác, `floor` giá cũng chính xác.
Ra ngoài (JSONL, file kho) dùng `public(item)` -> `{"id","kind","fresh"}` với fresh = u / 240.

Cách dùng điển hình (gather/quan):

    cfg = Freshness(tuning)                                  # đọc tuning.freshness
    self.ids = ItemIds(); self.ids.reserve_all(self.hold)    # id I* tăng xuyên pha/Ngày (day giữ một ItemIds)
    item = new_item(self.ids, "ca_linh", cfg)                # bắt/hái: fresh 100
    events += decay(self.hold, cfg.gather_per_tick, cfg, "hold")   # đầu bước: hao + spoiled theo id
"""

import math

from .errors import BadInput
from .ids import id_key

UNITS = 240


def to_units(fresh) -> int:
    """Đổi fresh (số điểm) sang số nguyên đơn vị; fixture phải biểu diễn chính xác (vd 97.5 -> 23400)."""
    return int(round(fresh * UNITS))


class Freshness:
    """Thông số độ tươi từ `tuning.freshness`, đã đổi sang đơn vị nguyên.

    Args:
        tuning: khối `tuning` của game.contract.json.

    Raises:
        BadInput: khi hao/tick không ra số nguyên đơn vị.
    """

    def __init__(self, tuning):
        f = tuning["freshness"]
        hz = tuning["tick_hz"]
        self.initial = to_units(f["initial"])
        self.spoiled_below = to_units(f["spoiled_below"])
        self.gather_per_tick = self._per_tick(f["gather_decay_per_s"], hz)
        self.quan_per_tick = self._per_tick(f["quan_decay_per_s"], hz)

    @staticmethod
    def _per_tick(per_s, hz):
        u = per_s * UNITS / hz
        if abs(u - round(u)) > 1e-9:
            raise BadInput(f"freshness: {per_s}/s không ra số nguyên đơn vị mỗi tick (UNITS={UNITS})")
        return int(round(u))

    def spoiled(self, item) -> bool:
        """Ươn = fresh < spoiled_below (so trên đơn vị nguyên, trước mọi làm tròn)."""
        return item["u"] < self.spoiled_below


class ItemIds:
    """Cấp id cá thể I1, I2, … tăng mãi, kể cả khi cá thể cũ đã dùng/bỏ (giữ MỘT đối tượng xuyên pha/Ngày)."""

    def __init__(self):
        self.last = 0

    def reserve(self, ident: str):
        if ident.startswith("I") and ident[1:].isdigit():
            self.last = max(self.last, int(ident[1:]))

    def reserve_all(self, items):
        for it in items:
            self.reserve(it["id"])

    def new(self) -> str:
        self.last += 1
        return f"I{self.last}"


def new_item(ids: ItemIds, kind: str, cfg: Freshness) -> dict:
    """Tạo cá thể mới fresh = initial (100) với id kế tiếp; bắt đầu hao từ bước sau."""
    return {"id": ids.new(), "kind": kind, "u": cfg.initial}


def public(item) -> dict:
    """Cá thể ra ngoài (snapshot, event, file kho): `{"id","kind","fresh"}`."""
    return {"id": item["id"], "kind": item["kind"], "fresh": item["u"] / UNITS}


def by_id(items) -> list:
    """Sắp cá thể theo id (I2 trước I10)."""
    return sorted(items, key=lambda it: id_key(it["id"]))


def decay(items, per_tick: int, cfg: Freshness, location: str) -> list:
    """Hao tươi một tick cho mọi cá thể (kẹp 0) và trả event `spoiled` cho cá thể vừa qua ngưỡng, theo id.

    Args:
        items: danh sách cá thể nội bộ, sửa tại chỗ.
        per_tick: số đơn vị trừ mỗi tick (`cfg.gather_per_tick` hoặc `cfg.quan_per_tick`).
        cfg: thông số độ tươi.
        location: `"hold"` hoặc `"stock"` (ghi vào data của event).

    Returns:
        Danh sách `("spoiled", {"item_id","kind","location"})` theo id; rỗng nếu không ai qua ngưỡng.
    """
    out = []
    for it in by_id(items):
        was_ok = not cfg.spoiled(it)
        it["u"] = max(0, it["u"] - per_tick)
        if was_ok and cfg.spoiled(it):
            out.append(("spoiled", {"item_id": it["id"], "kind": it["kind"], "location": location}))
    return out


def pick_freshest(items, kind: str, n: int, cfg: Freshness, exclude=()) -> list:
    """Chọn n cá thể chưa ươn tươi nhất của `kind` (hòa theo id), bỏ qua id trong `exclude`; thiếu -> None."""
    cands = [it for it in items if it["kind"] == kind and not cfg.spoiled(it) and it["id"] not in exclude]
    cands.sort(key=lambda it: (-it["u"], id_key(it["id"])))
    return cands[:n] if len(cands) >= n else None


def reserve_recipe(items, recipe: dict, cfg: Freshness, exclude=()) -> list:
    """Giữ chỗ theo công thức: mỗi kind lấy cá thể khả dụng tươi nhất; trả mảng id (theo id) hoặc None nếu thiếu."""
    taken = []
    for kind in sorted(recipe):
        got = pick_freshest(items, kind, recipe[kind], cfg, exclude=set(exclude) | {i["id"] for i in taken})
        if got is None:
            return None
        taken += got
    return [it["id"] for it in by_id(taken)]


def fresh_price(price: int, used) -> int:
    """Giá theo tươi: floor(giá niêm yết × trung bình fresh / 100), tính trên đơn vị nguyên nên chính xác."""
    used = list(used)
    return (price * sum(it["u"] for it in used)) // (len(used) * UNITS * 100)


def lifo_drop(hold: list, k: int) -> list:
    """Bỏ k cá thể theo LIFO (vào giỏ sau mất trước); trả dạng public theo thứ tự bỏ."""
    return [public(hold.pop()) for _ in range(min(k, len(hold)))]


def parse_items(raw, where: str, kinds) -> list:
    """Kiểm và đổi mảng cá thể `{id,kind,fresh}` (file kho / scenario) sang dạng nội bộ, giữ thứ tự.

    Raises:
        BadInput: sai schema, kind lạ, id trùng/rỗng, fresh không hữu hạn hoặc ngoài [0, 100] (mã 2).
    """
    if not isinstance(raw, list):
        raise BadInput(f"{where} phải là mảng cá thể {{id, kind, fresh}}")
    out, seen = [], set()
    for i, it in enumerate(raw):
        if not isinstance(it, dict) or set(it) != {"id", "kind", "fresh"}:
            raise BadInput(f"{where}[{i}] phải có đúng các khóa id, kind, fresh")
        if not isinstance(it["id"], str) or not it["id"] or it["id"] in seen:
            raise BadInput(f"{where}[{i}]: id phải là chuỗi khác rỗng, không trùng")
        if it["kind"] not in kinds:
            raise BadInput(f"{where}[{i}]: nguyên liệu lạ {it['kind']!r}")
        f = it["fresh"]
        if isinstance(f, bool) or not isinstance(f, (int, float)) or not math.isfinite(f) or not (0 <= f <= 100):
            raise BadInput(f"{where}[{i}]: fresh phải là số hữu hạn trong [0, 100]")
        seen.add(it["id"])
        out.append({"id": it["id"], "kind": it["kind"], "u": to_units(f)})
    return out

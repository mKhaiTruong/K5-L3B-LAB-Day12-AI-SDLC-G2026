"""Thủy quái trong gather (TICKET-02 mục 1.2, thứ tự mục 4.5). Hiện có Cá Sấu Năm Chèo (`ca_sau`).

Cách gather.py dùng (mỗi bước, SAU khi người chơi bơi + oxy/ngạt):

    hit = self.monsters.step(self.pos)                 # di chuyển theo id rồi chọn tối đa một con chạm
    if hit and self.invuln_ticks == 0:
        lost = self.monsters.apply_hit(hit, self.pos, self.hold)   # recoil + trả mảng cá thể mất (LIFO)
        self.hp -= 1; self.invuln_ticks = self.monsters.invuln_ticks
        events.append(("monster_hit", {"monster_id": hit["id"], "hp": self.hp, "lost": lost,
                                       "pos": list(self.pos)}))
        # hp == 0 -> faint(cause "monster", lost = phần giỏ còn lại) -> gather_end(fainted)

`step` không tự biết bất tử: gather tự kiểm `invuln_ticks == 0` trước khi gọi `apply_hit`.
Snapshot: `self.monsters.snapshot()` -> danh sách theo id.
"""

import math

from ..fresh import lifo_drop
from ..ids import sort_by_id

TICK = 60.0
EPS = 1e-9


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _toward(pos, target, step):
    """Đi từ pos về target tối đa `step` m; trả (vị trí mới, đã tới nơi?)."""
    d = _dist(pos, target)
    if d <= step + EPS:  # EPS: cộng dồn 1/60 m lệch ~1e-13, tránh tới nơi trễ 1 bước
        return [float(target[0]), float(target[1])], True
    return [pos[0] + (target[0] - pos[0]) / d * step, pos[1] + (target[1] - pos[1]) / d * step], False


class MonsterSet:
    """Danh sách thủy quái của một buổi sáng: patrol / chase / recoil, chọn hit.

    Args:
        g: khối `tuning.gather` (cần `bounds`, `monsters`).
        fixtures: `scenario.gather.monsters` (thay danh sách mặc định) hoặc None.
        day: số Ngày hiện tại; chỉ sinh con có `from_day <= day` (gather độc lập dùng Ngày 1).
    """

    def __init__(self, g, fixtures=None, day=1):
        cfg = g["monsters"]
        self.species = cfg["species"]
        self.invuln_ticks = cfg["invuln_ticks"]
        self.loss_ratio = cfg["loss_ratio"]
        self.x_bounds = g["bounds"]["x"]
        src = fixtures if fixtures is not None else [s for s in cfg["spawns"] if s["from_day"] <= day]
        self.items = sort_by_id([{
            "id": m["id"], "kind": m["kind"],
            "pos": [float(c) for c in m["pos"]],
            "waypoints": [[float(c) for c in wp] for wp in m["waypoints"]],
            "target_idx": m.get("target_idx", 1),
            "state": m.get("state", "patrol"),
            "state_ticks_left": m.get("state_ticks_left", 0),
            "recoil_dir": m.get("recoil_dir"),
        } for m in src])

    def _clamp(self, m):
        lo, hi = self.species[m["kind"]]["depths"]
        m["pos"][0] = min(max(m["pos"][0], self.x_bounds[0]), self.x_bounds[1])
        m["pos"][1] = min(max(m["pos"][1], lo), hi)

    def step(self, player_pos):
        """Cập nhật mọi con theo id, rồi trả con gây chạm (gần nhất, hòa theo id) hoặc None.

        Con đang recoil (kể cả con vừa hết recoil ở bước này) không phát hiện, không chạm.

        Args:
            player_pos: vị trí người chơi [x, d] sau khi bơi ở bước này.

        Returns:
            dict của con gây chạm (chính phần tử trong `items`), hoặc None.
        """
        can_hit = []
        for m in self.items:
            sp = self.species[m["kind"]]
            if m["state"] == "recoil":
                step = sp["recoil_dist"] / sp["recoil_ticks"]
                m["pos"] = [m["pos"][0] + m["recoil_dir"][0] * step, m["pos"][1] + m["recoil_dir"][1] * step]
                self._clamp(m)
                m["state_ticks_left"] -= 1
                if m["state_ticks_left"] <= 0:
                    m.update(state="patrol", state_ticks_left=0, recoil_dir=None)
                continue  # hết recoil: xét phát hiện/chạm từ bước kế
            deep = player_pos[1] >= sp["depths"][0]
            d = _dist(m["pos"], player_pos)
            if m["state"] == "patrol" and deep and d <= sp["detect_radius"]:
                m["state"] = "chase"
            elif m["state"] == "chase" and (not deep or d > sp["exit_radius"]):
                m["state"] = "patrol"
            if m["state"] == "chase":
                m["pos"], _ = _toward(m["pos"], player_pos, sp["chase_speed"] / TICK)
            else:
                m["pos"], arrived = _toward(m["pos"], m["waypoints"][m["target_idx"]], sp["patrol_speed"] / TICK)
                if arrived:
                    m["target_idx"] = 1 - m["target_idx"]  # mục tiêu kia cho bước sau
            self._clamp(m)
            can_hit.append(m)
        best = None
        for m in can_hit:
            sp = self.species[m["kind"]]
            d = _dist(m["pos"], player_pos)
            if player_pos[1] >= sp["depths"][0] and d <= sp["hit_radius"]:
                if best is None or d < best[0]:  # items đã sắp theo id -> hòa giữ con id nhỏ
                    best = (d, m)
        return best[1] if best else None

    def apply_hit(self, m, player_pos, hold):
        """Đưa con gây chạm vào recoil và bỏ floor(n × loss_ratio) hàng theo LIFO khỏi `hold`.

        Args:
            m: con trả về từ `step`.
            player_pos: vị trí người chơi lúc chạm.
            hold: giỏ (mảng cá thể nội bộ `{id,kind,u}` theo thứ tự vào giỏ), bị sửa tại chỗ.

        Returns:
            Mảng cá thể đã mất dạng `{id,kind,fresh}`, vào giỏ sau mất trước (contract v1.2).
        """
        sp = self.species[m["kind"]]
        dx, dd = m["pos"][0] - player_pos[0], m["pos"][1] - player_pos[1]
        n = math.hypot(dx, dd)
        m.update(state="recoil", state_ticks_left=sp["recoil_ticks"],
                 recoil_dir=[dx / n, dd / n] if n > 0 else [1.0, 0.0])
        k = math.floor(len(hold) * self.loss_ratio)
        return lifo_drop(hold, k)

    def snapshot(self):
        """Danh sách thủy quái cho snapshot, theo id (trường theo scenario v1.1 mục 4.3)."""
        return [{k: (list(v) if isinstance(v, list) else v) for k, v in m.items()} for m in self.items]

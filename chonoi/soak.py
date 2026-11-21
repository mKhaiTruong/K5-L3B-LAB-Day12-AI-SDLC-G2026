"""Soak headless (TICKET-04 mục 2): python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

Chạy N Ngày trong MỘT tiến trình, cùng lớp `DaySim` như mode `day`. Mỗi Ngày đi qua gather -> quan -> shop;
kế hoạch D1–D5 lặp ở Ngày 6–10; tiền, earned, uy tín, cấp nâng cấp, số Ngày và id cá thể chạy liên tục.

Bot tất định (không đọc đồng hồ, không ngẫu nhiên riêng): đứng yên ở bến suốt gather và quán,
bấm `shop_done` ở bước đầu của Shop. Soak không ghi JSONL và không ghi bảng xếp hạng.

Mã thoát: 0 chạy xong (kể cả khi có crash, đã ghi trong soak.json); 2 tham số sai; 1 không ghi được file.
"""

import argparse
import json
import math
import os
import sys
import time
import traceback

from .contract import DAYS, load_contract
from .errors import BadInput
from .inputs import BUTTONS, InputState
from .rng import Streams
from .sim.day import DaySim


class SoakDaySim(DaySim):
    """`DaySim` không giới hạn số Ngày: Ngày d dùng kế hoạch D((d - 1) mod 5 + 1)."""

    def __init__(self, tuning, scenario, streams, days):
        super().__init__(tuning, scenario, streams, days=1)
        self.days = days

    @property
    def plan(self):
        return self.plans[(self.day - 1) % DAYS + 1]


def _idle(edges=()):
    return InputState((0.0, 0.0), {b: False for b in BUTTONS}, set(edges))


def _score(sim, tuning):
    return sim.earned + tuning["score"]["reputation_multiplier"] * math.floor(sim.reputation)


def soak(tuning, seed, days, max_ticks_per_day=200_000):
    """Chạy `days` Ngày với bot tất định.

    Args:
        tuning: khối `tuning` của contract.
        seed: seed của `Streams`.
        days: số Ngày cần chạy (>= 1).
        max_ticks_per_day: chặn vòng lặp vô hạn nếu một pha không bao giờ kết thúc (tính là crash).

    Returns:
        Dict `{days, days_completed, crashes, results, duration_s}`; `results[]` là
        `{day, earned, reputation, score}` lúc Shop đóng.
    """
    t0 = time.perf_counter()
    results, crashes = [], 0
    try:
        sim = SoakDaySim(tuning, {}, Streams(seed), days)
        ticks_today = 0
        while not sim.done:
            edges = ("shop_done",) if sim.phase == "shop" else ()
            day_before = sim.days_completed
            sim.step(_idle(edges))
            ticks_today += 1
            if sim.days_completed > day_before:
                results.append({"day": sim.days_completed, "earned": sim.earned,
                                "reputation": sim.reputation, "score": _score(sim, tuning)})
                ticks_today = 0
            elif ticks_today > max_ticks_per_day:
                raise RuntimeError(f"Ngày {sim.day} vượt {max_ticks_per_day} tick")
    except Exception:  # soak đếm crash thay vì dừng tiến trình
        crashes += 1
        traceback.print_exc(file=sys.stderr)
    return {"days": days, "days_completed": len(results), "crashes": crashes, "results": results,
            "duration_s": round(time.perf_counter() - t0, 3)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.soak", description="Soak headless N Ngày (TICKET-04).")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--days", required=True, type=int)
    p.add_argument("--out", required=True)
    try:
        a = p.parse_args(argv)
    except SystemExit:
        return 2
    try:
        if a.days < 1:
            raise BadInput("--days phải >= 1")
        tuning = load_contract()["tuning"]
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    report = soak(tuning, a.seed, a.days)
    try:
        tmp = a.out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, a.out)
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

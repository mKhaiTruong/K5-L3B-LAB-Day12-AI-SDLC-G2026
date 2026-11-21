"""Soak headless (TICKET-04 mục 2): hộp đen qua `soak_cmd` trong game.contract.json."""

import json
import os
import shlex
import subprocess
import tempfile
import unittest

from chonoi.contract import load_contract
from chonoi.rng import Streams
from chonoi.soak import SoakDaySim, _idle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def soak_cmd(*args):
    cmd = shlex.split(load_contract()["soak_cmd"])
    return subprocess.run([*cmd, *args], cwd=ROOT, capture_output=True, text=True)


class SoakCmd(unittest.TestCase):
    def test_contract_v13_declares_bench_and_soak(self):
        c = load_contract()
        self.assertEqual(c["contract_version"], "1.3")
        self.assertTrue(c["bench_cmd"].strip())
        self.assertTrue(c["soak_cmd"].strip())

    def test_ten_days_no_crash_and_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            outs = []
            for i in range(2):
                path = os.path.join(d, f"soak{i}.json")
                p = soak_cmd("--seed", "7", "--days", "10", "--out", path)
                self.assertEqual(p.returncode, 0, p.stderr)
                with open(path, encoding="utf-8") as f:
                    outs.append(json.load(f))
        a, b = outs
        self.assertEqual(set(a), {"days", "days_completed", "crashes", "results", "duration_s"})
        self.assertEqual((a["days"], a["days_completed"], a["crashes"]), (10, 10, 0))
        self.assertEqual([r["day"] for r in a["results"]], list(range(1, 11)))
        for r in a["results"]:
            self.assertEqual(set(r), {"day", "earned", "reputation", "score"})
        a.pop("duration_s"), b.pop("duration_s")  # bỏ số đo thời gian thực khi so
        self.assertEqual(a, b)

    def test_bad_args_exit_2_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            for args in (["--seed", "7", "--days", "0"], ["--seed", "x", "--days", "3"], ["--days", "3"]):
                p = soak_cmd(*args, "--out", path)
                self.assertEqual(p.returncode, 2, args)
                self.assertFalse(os.path.exists(path))


class PlanCycle(unittest.TestCase):
    def test_day_6_uses_plan_d1(self):
        tuning = load_contract()["tuning"]
        sim = SoakDaySim(tuning, {}, Streams(7), 6)
        plans = {}
        while not sim.done:
            plans.setdefault(sim.day, sim.plan)
            sim.step(_idle(("shop_done",) if sim.phase == "shop" else ()))
        self.assertEqual(sim.days_completed, 6)
        self.assertEqual(plans[6], plans[1])
        self.assertEqual([plans[d] for d in range(1, 6)], [sim.plans[d] for d in range(1, 6)])


if __name__ == "__main__":
    unittest.main()

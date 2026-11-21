"""Bench (TICKET-04 mục 1): hộp đen qua `bench_cmd` trong game.contract.json + công thức avg / 1% low."""

import json
import math
import os
import shlex
import subprocess
import tempfile
import unittest

from chonoi.bench import FIELDS, bench_json, summarize
from chonoi.contract import load_contract

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bench_cmd(*args):
    cmd = shlex.split(load_contract()["bench_cmd"])
    return subprocess.run([*cmd, *args], cwd=ROOT, capture_output=True, text=True, timeout=120)


class BenchCmd(unittest.TestCase):
    def check_file(self, path):
        with open(path, encoding="utf-8") as f:
            b = json.load(f)
        self.assertEqual(set(b), set(FIELDS))  # đúng 5 khóa
        self.assertIsInstance(b["frames"], int)
        for k in ("avg_fps", "p1_low_fps", "measured_s", "load_ms"):
            self.assertIsInstance(b[k], (int, float), k)
            self.assertNotIsInstance(b[k], bool, k)
            self.assertTrue(math.isfinite(b[k]) and b[k] >= 0, k)
        self.assertGreater(b["frames"], 0)
        self.assertAlmostEqual(b["avg_fps"], b["frames"] / b["measured_s"], delta=0.02 * b["avg_fps"])
        self.assertLessEqual(b["p1_low_fps"], b["avg_fps"] + 0.01)
        return b

    def test_bench_cmd_writes_five_fields(self):
        """Lệnh trong contract chạy được (dự phòng không render để test không cần trình duyệt)."""
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "bench.json")
            p = bench_cmd("--seed", "42", "--duration", "1", "--warmup", "0", "--no-browser", "--out", out)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.check_file(out)

    @unittest.skipUnless(os.environ.get("CHONOI_BENCH_BROWSER") == "1", "đặt CHONOI_BENCH_BROWSER=1 để đo render thật")
    def test_bench_cmd_browser_render(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "bench.json")
            p = bench_cmd("--seed", "42", "--duration", "2", "--warmup", "1", "--out", out)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("render", p.stderr)
            self.check_file(out)

    def test_bad_duration_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            p = bench_cmd("--seed", "42", "--duration", "0", "--out", os.path.join(d, "b.json"))
            self.assertEqual(p.returncode, 2)
            self.assertFalse(os.path.exists(os.path.join(d, "b.json")))


class BenchMath(unittest.TestCase):
    def test_avg_and_p1_low(self):
        # 200 khung: 198 khung 10 ms, 2 khung 50 ms -> k = ceil(0.01*200) = 2 khung chậm nhất, TB 50 ms -> 20 FPS
        frames, measured, avg, p1 = summarize([0.010] * 198 + [0.050] * 2)
        self.assertEqual(frames, 200)
        self.assertAlmostEqual(measured, 2.08)
        self.assertAlmostEqual(avg, 200 / 2.08)
        self.assertAlmostEqual(p1, 20.0)

    def test_p1_low_at_least_one_frame(self):
        frames, _, _, p1 = summarize([0.016, 0.040, 0.016])  # ceil(0.03) = 1 -> khung 40 ms
        self.assertEqual(frames, 3)
        self.assertAlmostEqual(p1, 25.0)

    def test_json_shape(self):
        b = bench_json(2160, 30.0004, 72.0, 38.123, 2400.4)
        self.assertEqual(list(b), list(FIELDS))
        self.assertEqual(b, {"avg_fps": 72.0, "p1_low_fps": 38.12, "frames": 2160, "measured_s": 30.0, "load_ms": 2400})


if __name__ == "__main__":
    unittest.main()

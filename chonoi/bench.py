"""Benchmark có render (TICKET-04 mục 1), chỉ dùng thư viện chuẩn Python.

    python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json

Cảnh đo: buổi sáng (gather) lõi với độ tươi (giỏ có sẵn cá thể đang hao), cá bơi, Cá Sấu M1, hiệu ứng
mặc định (không bật tương phản cao); Út Sen đứng yên ở bến (không gửi input). Cửa sổ 1280×720.

Cách đo (giả định của nhóm, ghi ở docs/clarify.md): UI là trang web `chonoi/web/index.html`, nên bench
dựng máy chủ live (cùng sim, 60 tick/s) rồi mở Chrome/Chromium/Edge headless 1280×720 vào
`/?bench=1&warmup=3&duration=N`. Trang đo thời gian giữa các khung `requestAnimationFrame` sau 3 s làm nóng
và gửi kết quả về `POST /bench`. Không tìm thấy trình duyệt (hoặc trình duyệt không trả kết quả) thì
bench vẫn ghi bench.json bằng phép đo dự phòng không render (bước sim + tuần tự hoá snapshot) và báo
rõ ra stderr.

bench.json có đúng 5 trường: avg_fps, p1_low_fps, frames, measured_s, load_ms.
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

T_START_MS = time.time() * 1000.0  # "lúc khởi chạy" cho load_ms (Date.now() của trình duyệt cùng đồng hồ máy)

from .contract import load_contract  # noqa: E402
from .errors import BadInput  # noqa: E402
from .inputs import LiveInputs  # noqa: E402
from .live import LiveGame, LiveServer, _Handler  # noqa: E402
from .runner import Session  # noqa: E402
from .scenario import load_scenario  # noqa: E402

WIDTH, HEIGHT = 1280, 720
FIELDS = ("avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms")
# giỏ có sẵn để cảnh đo có độ tươi (thanh tươi + một con đã ươn); Út Sen ở bến, không input
BENCH_HOLD = [
    {"id": "I1", "kind": "ca_loc", "fresh": 100},
    {"id": "I2", "kind": "ca_linh", "fresh": 75},
    {"id": "I3", "kind": "bong_sung", "fresh": 50},
    {"id": "I4", "kind": "ca_keo", "fresh": 20},
]


def summarize(frame_s):
    """Thời gian từng khung (giây) -> (frames, measured_s, avg_fps, p1_low_fps) theo TICKET-04."""
    frames = len(frame_s)
    measured = sum(frame_s)
    if frames == 0 or measured <= 0:
        return 0, 0.0, 0.0, 0.0
    k = max(1, math.ceil(0.01 * frames))
    slowest = sorted(frame_s, reverse=True)[:k]
    return frames, measured, frames / measured, 1.0 / (sum(slowest) / k)


def bench_json(frames, measured_s, avg_fps, p1_low_fps, load_ms):
    return {"avg_fps": round(avg_fps, 2), "p1_low_fps": round(p1_low_fps, 2), "frames": int(frames),
            "measured_s": round(measured_s, 3), "load_ms": int(round(max(0.0, load_ms)))}


def bench_scenario(tuning):
    """Khối gather của cảnh đo (đi qua load_scenario để kiểm như scenario thường)."""
    g = tuning["gather"]
    block = {"player": {"pos": list(g["dock_pos"])}, "hold": BENCH_HOLD}
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "bench-scenario.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"gather": block}, f)
        return load_scenario(path, "gather", tuning)


# --- trình duyệt -------------------------------------------------------------------------
def find_browser():
    env = os.environ.get("CHONOI_BROWSER")
    if env:
        return env if (os.path.isfile(env) or shutil.which(env)) else None
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge",
                 "microsoft-edge", "microsoft-edge-stable"):
        p = shutil.which(name)
        if p:
            return p
    cands = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/Applications/Chromium.app/Contents/MacOS/Chromium",
             "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
        if base:
            cands += [os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                      os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe")]
    return next((c for c in cands if os.path.isfile(c)), None)


class _BenchHandler(_Handler):
    result = None  # gán trên lớp con: {"data": None, "event": threading.Event()}

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/bench":
            return super().do_POST()
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n).decode("utf-8")) if 0 < n <= 4_000_000 else None
            if not isinstance(body, dict):
                raise ValueError("body phải là object")
        except (ValueError, UnicodeDecodeError) as e:
            self._send(400, json.dumps({"error": str(e)}).encode("utf-8"))
            return
        self.result["data"] = body
        self.result["event"].set()
        self._send(200, b'{"ok":true}')


def run_browser(exe, tuning, scenario, seed, warmup, duration, show=False):
    """Đo trên trình duyệt; trả dict kết quả trang gửi về, hoặc None nếu hết giờ."""
    game = LiveGame("gather", tuning, scenario, seed)
    server = LiveServer(game, "127.0.0.1", 0)
    result = {"data": None, "event": threading.Event()}
    server.httpd.RequestHandlerClass = type("BenchHandler", (_BenchHandler,), {"game": game, "result": result})
    server.httpd.handle_error = lambda request, client_address: None  # trình duyệt bị tắt giữa chừng: không in traceback
    server.start()
    url = f"{server.url}?bench=1&warmup={warmup}&duration={duration}"
    profile = tempfile.mkdtemp(prefix="chonoi-bench-")
    args = [exe, f"--window-size={WIDTH},{HEIGHT}", f"--user-data-dir={profile}", "--no-first-run",
            "--no-default-browser-check", "--disable-extensions", "--force-device-scale-factor=1",
            "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows"]
    args += [f"--app={url}"] if show else ["--headless=new", "--hide-scrollbars", url]
    proc = None
    try:
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        result["event"].wait(warmup + duration + 30)
        return result["data"]
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        server.stop()
        shutil.rmtree(profile, ignore_errors=True)


def run_fallback(tuning, scenario, seed, warmup, duration):
    """Dự phòng KHÔNG render: mỗi 'khung' = 1 bước sim + tuần tự hoá snapshot như /state."""
    s = Session("gather", tuning, scenario, seed)
    idle = LiveInputs()
    first_ms = None
    times, t_begin = [], None
    while True:
        t0 = time.perf_counter()
        if s.done:
            s = Session("gather", tuning, scenario, seed)
        s.step(idle.advance())
        json.dumps(s.snapshot(), ensure_ascii=False, separators=(",", ":"))
        t1 = time.perf_counter()
        if first_ms is None:
            first_ms = time.time() * 1000.0
            t_begin = t1
        if t1 - t_begin >= warmup:
            times.append(t1 - t0)
            if t1 - t_begin >= warmup + duration:
                break
    return first_ms, times


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.bench", description="Benchmark có render cảnh lặn (TICKET-04).")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--duration", required=True, type=float, help="số giây đo (sau làm nóng)")
    p.add_argument("--out", required=True)
    p.add_argument("--warmup", type=float, default=3.0, help="giây làm nóng (mặc định 3 theo TICKET-04)")
    p.add_argument("--no-browser", action="store_true", help="bỏ trình duyệt, dùng phép đo dự phòng không render")
    p.add_argument("--show", action="store_true", help="mở cửa sổ trình duyệt thật thay vì headless")
    a = p.parse_args(argv)
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # thông báo tiếng Việt trên console Windows
    except (AttributeError, ValueError):
        pass
    if a.duration <= 0 or a.warmup < 0:
        sys.stderr.write("đầu vào sai: --duration phải > 0, --warmup phải >= 0\n")
        return 2
    try:
        tuning = load_contract()["tuning"]
        scenario = bench_scenario(tuning)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2

    data = None
    exe = None if a.no_browser else find_browser()
    if exe:
        try:
            data = run_browser(exe, tuning, scenario, a.seed, a.warmup, a.duration, a.show)
        except OSError as e:
            sys.stderr.write(f"không chạy được trình duyệt {exe}: {e}\n")
        if data is None:
            sys.stderr.write("trình duyệt không trả kết quả đo -> dùng phép đo dự phòng không render\n")
    elif not a.no_browser:
        sys.stderr.write("không tìm thấy Chrome/Chromium/Edge (đặt CHONOI_BROWSER) -> phép đo dự phòng không render\n")

    if data is not None:
        frames, measured, avg, p1 = summarize([float(x) / 1000.0 for x in data.get("frame_ms", [])])
        out = bench_json(frames, measured, avg, p1, float(data.get("first_frame_epoch_ms", T_START_MS)) - T_START_MS)
        source = f"render trình duyệt ({os.path.basename(exe)}, canvas {data.get('viewport')}, dpr {data.get('dpr')})"
    else:
        first_ms, times = run_fallback(tuning, scenario, a.seed, a.warmup, a.duration)
        frames, measured, avg, p1 = summarize(times)
        out = bench_json(frames, measured, avg, p1, first_ms - T_START_MS)
        source = "DỰ PHÒNG không render (bước sim + snapshot JSON)"
    try:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(out, f)
            f.write("\n")
    except OSError as e:
        sys.stderr.write(f"không ghi được {a.out}: {e}\n")
        return 1
    sys.stderr.write(f"bench: {source}: {json.dumps(out)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

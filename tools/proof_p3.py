"""Sinh bằng chứng Phase 3 (contract v1.2: kho cá thể + độ tươi) vào docs/proof/phase-3/.

    python3 tools/proof_p3.py

Chạy: toàn bộ test; smoke bàn giao kho theo PRD (gather --inventory-out -> quan --inventory, so id/kind/fresh);
ngưỡng ươn ở gather và quán; tốc độ hao; giá theo độ tươi; mất hàng LIFO dạng cá thể; kho đếm cũ -> mã 2;
mode day 2 Ngày (bàn giao giữ id, id I* tăng liên tục xuyên Ngày); tất định (chạy lại cùng seed -> giống
từng byte). Chỉ dùng thư viện chuẩn. JSONL lưu đuôi .jsonl.txt vì .gitignore bỏ qua *.jsonl.
"""

import datetime
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "proof", "phase-3")
PY = sys.executable
ENV = dict(os.environ, PYTHONUTF8="1",
           PYTHONPATH=os.pathsep.join(["tests", "."]),
           PATH=os.path.dirname(PY) + os.pathsep + os.environ.get("PATH", ""))
CONTRACT = json.load(open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8"))
F = CONTRACT["tuning"]["freshness"]
TOL = 0.01  # dung sai quan sát fresh (JSONL làm tròn 3 chữ số)


def sh(args):
    p = subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout, p.stderr


def headless(*args, expect=0):
    code, _, err = sh([PY, "-m", "chonoi.headless", *args])
    if code != expect:
        sys.exit(f"headless mã {code} (mong {expect}): {' '.join(args)}\n{err}")
    return err.strip()


def p(*parts):
    return os.path.join(OUT, *parts)


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_json(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False) + "\n")
    return rel(path)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def rows(path):
    return [json.loads(line) for line in read(path).splitlines() if line.strip()]


def evs(rs, *names):
    return [r for r in rs if r["type"] == "event" and (not names or r["name"] in names)]


def snaps(rs):
    return [r for r in rs if r["type"] == "snapshot"]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def items(*spec):
    """items(("I1", "ca_linh", 100), ...) -> mảng cá thể fixture."""
    return [{"id": i, "kind": k, "fresh": f} for i, k, f in spec]


def ik(arr):
    return [(it["id"], it["kind"]) for it in arr]


def close(a, b):
    return len(a) == len(b) and all(ik([x]) == ik([y]) and abs(x["fresh"] - y["fresh"]) <= TOL for x, y in zip(a, b))


QUIET = {"random_fish": False, "monsters": []}
DOCK = {"frames": [{"tick": 0, "interact": True}]}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    commit = sh(["git", "rev-parse", "--short", "HEAD"])[1].strip()
    dirty = sh(["git", "status", "--porcelain", "--", "chonoi", "tests", "game.contract.json"])[1].strip()
    lines = []
    ok = lambda b: "ĐẠT" if b else "CHƯA ĐẠT"
    os.makedirs(OUT, exist_ok=True)

    # 1. toàn bộ test
    code, out, err = sh([PY, "-m", "unittest", "discover", "-s", "tests", "-v"])
    write(p("tests-full.txt"), err + out)
    summary = [ln for ln in (err + out).splitlines() if ln.startswith("Ran ") or ln == "OK" or ln.startswith("FAILED")]
    lines.append(f"| Toàn bộ test (`unittest discover -s tests -v`) | [`tests-full.txt`](tests-full.txt) | {' · '.join(summary)} |")

    # 2. smoke bàn giao kho (PRD): cập bến ở tick 0 -> file kho -> quán đọc ở tick 0
    hd = p("handoff")
    sc = write_json(os.path.join(hd, "dock.json"), {"gather": {**QUIET, "hold": items(("I1", "ca_linh", 100))}})
    inp = write_json(os.path.join(hd, "dock-inputs.json"), DOCK)
    kho, g1, g2, q1 = (os.path.join(hd, n) for n in ("kho.json", "gather.jsonl.txt", "gather-rerun.jsonl.txt", "quan.jsonl.txt"))
    kho2 = os.path.join(hd, "kho-rerun.json")
    headless("--mode", "gather", "--seed", "42", "--ticks", "1", "--scenario", sc, "--inputs", inp,
             "--out", rel(g1), "--inventory-out", rel(kho))
    headless("--mode", "gather", "--seed", "42", "--ticks", "1", "--scenario", sc, "--inputs", inp,
             "--out", rel(g2), "--inventory-out", rel(kho2))
    headless("--mode", "quan", "--seed", "42", "--ticks", "0", "--inventory", rel(kho), "--out", rel(q1))
    saved = json.loads(read(kho))["items"]
    end_inv = evs(rows(g1), "gather_end")[0]["data"]["inventory"]["items"]
    stock0 = snaps(rows(q1))[0]["stock"]
    want_fresh = F["initial"] - F["gather_decay_per_s"] / 60  # hao đúng 1 bước gather trước khi cập bến
    hand_ok = close(saved, end_inv) and close(saved, stock0) and ik(saved) == [("I1", "ca_linh")] \
        and abs(saved[0]["fresh"] - want_fresh) <= 1e-9
    lines.append(f"| Smoke bàn giao kho (PRD): giỏ `I1 ca_linh 100`, cập bến tick 0 → `quan --inventory --ticks 0` | "
                 f"[`handoff/`](handoff/) | file kho `{json.dumps(saved)}`; `gather_end.inventory` `{json.dumps(end_inv)}`; "
                 f"quán tick 0 `stock` `{json.dumps(stock0)}`; id/kind khớp, fresh lệch ≤ {TOL} → {ok(hand_ok)} |")
    same_h = sha(g1) == sha(g2) and sha(kho) == sha(kho2)
    lines.append(f"| Tất định bàn giao (chạy lại seed 42) | `handoff/gather-rerun.jsonl.txt`, `kho-rerun.json` | "
                 f"JSONL {sha(g1)[:12]}… = {sha(g2)[:12]}…, kho {sha(kho)[:12]}… = {sha(kho2)[:12]}… → "
                 f"{'GIỐNG TỪNG BYTE' if same_h else 'KHÁC'} |")

    # 3. ngưỡng ươn: fresh đúng ngưỡng -> spoiled ở tick 1, đúng một lần (gather: hold, quán: stock)
    td = p("threshold")
    thr = F["spoiled_below"]
    sg = write_json(os.path.join(td, "gather.json"), {"gather": {**QUIET, "hold": items(("I1", "ca_linh", thr))}})
    gt = os.path.join(td, "gather.jsonl.txt")
    headless("--mode", "gather", "--seed", "1", "--ticks", "120", "--scenario", sg, "--out", rel(gt))
    sq = write_json(os.path.join(td, "quan.json"), {"quan": {"random_customers": False,
                                                            "stock": items(("I2", "ca_loc", thr), ("I10", "ca_loc", thr),
                                                                           ("I3", "ca_loc", thr + 1))}})
    qt = os.path.join(td, "quan.jsonl.txt")
    headless("--mode", "quan", "--seed", "1", "--ticks", "120", "--scenario", sq, "--out", rel(qt))
    gsp = [(e["tick"], e["data"]) for e in evs(rows(gt), "spoiled")]
    qsp = [(e["tick"], e["data"]) for e in evs(rows(qt), "spoiled")]
    g_ok = gsp == [(1, {"item_id": "I1", "kind": "ca_linh", "location": "hold"})]
    q_ok = qsp == [(1, {"item_id": "I2", "kind": "ca_loc", "location": "stock"}),
                   (1, {"item_id": "I10", "kind": "ca_loc", "location": "stock"})]
    lines.append(f"| Ngưỡng ươn gather: fresh {thr} → `spoiled` ở tick 1, một lần trong 120 tick | "
                 f"[`threshold/gather.jsonl.txt`](threshold/gather.jsonl.txt) | {gsp} → {ok(g_ok)} |")
    lines.append(f"| Ngưỡng ươn quán: I2, I10 fresh {thr} + I3 fresh {thr + 1} → `spoiled` theo id ở tick 1 | "
                 f"[`threshold/quan.jsonl.txt`](threshold/quan.jsonl.txt) | {qsp}; I3 không ươn → {ok(q_ok)} |")

    # 4. tốc độ hao: gather 0.5/s, quán 0.25/s
    rd = p("rate")
    rg = write_json(os.path.join(rd, "gather.json"), {"gather": {**QUIET, "hold": items(("I1", "ca_loc", 100))}})
    rq = write_json(os.path.join(rd, "quan.json"), {"quan": {"random_customers": False, "stock": items(("I1", "ca_loc", 100))}})
    rgo, rqo = os.path.join(rd, "gather.jsonl.txt"), os.path.join(rd, "quan.jsonl.txt")
    headless("--mode", "gather", "--seed", "1", "--ticks", "60", "--scenario", rg, "--out", rel(rgo), "--snapshot-every", "60")
    headless("--mode", "quan", "--seed", "1", "--ticks", "240", "--scenario", rq, "--out", rel(rqo), "--snapshot-every", "240")
    fg = snaps(rows(rgo))[-1]["hold"][0]["fresh"]
    fq = snaps(rows(rqo))[-1]["stock"][0]["fresh"]
    wg, wq = 100 - F["gather_decay_per_s"], 100 - F["quan_decay_per_s"] * 4
    lines.append(f"| Tốc độ hao: gather {F['gather_decay_per_s']}/s (60 tick), quán {F['quan_decay_per_s']}/s (240 tick) | "
                 f"[`rate/`](rate/) | gather {fg} (mong {wg}), quán {fq} (mong {wq}) → "
                 f"{ok(abs(fg - wg) <= 1e-9 and abs(fq - wq) <= 1e-9)} |")

    # 5. giá theo độ tươi: floor(giá × fresh trung bình / 100), chốt lúc cook_started
    pd = p("price")
    menu = CONTRACT["tuning"]["menu"]["ca_loc_nuong_trui"]
    sp = write_json(os.path.join(pd, "quan.json"), {"quan": {"player": {"pos": [2, 8]}, "random_customers": False,
                                                            "stock": items(("I1", "ca_loc", 50.5)),
                                                            "customers": [{"id": "C1", "table_id": "T1",
                                                                           "dish_id": "ca_loc_nuong_trui"}]}})
    pi = write_json(os.path.join(pd, "inputs.json"), DOCK)
    po = os.path.join(pd, "quan.jsonl.txt")
    headless("--mode", "quan", "--seed", "1", "--ticks", "1", "--scenario", sp, "--inputs", pi, "--out", rel(po))
    cs = evs(rows(po), "cook_started")
    used = 50.5 - F["quan_decay_per_s"] / 60
    want_price = int(menu["price"] * used // 100)
    price_ok = bool(cs) and cs[0]["data"]["base_price"] == want_price and ik(cs[0]["data"]["items"]) == [("I1", "ca_loc")]
    lines.append(f"| Giá theo độ tươi: món {menu['price']}, cá I1 fresh 50.5 (hao 1 bước) | [`price/quan.jsonl.txt`](price/quan.jsonl.txt) | "
                 f"`cook_started` {json.dumps(cs[0]['data'] if cs else {}, ensure_ascii=False)} (mong base_price {want_price}) → {ok(price_ok)} |")

    # 6. mất hàng LIFO dạng cá thể (Cá Sấu chạm)
    md = p("monsters")
    croc = {"id": "M1", "kind": "ca_sau", "pos": [62, 24], "waypoints": [[60, 24], [64, 24]]}
    hold4 = items(("I1", "ca_loc", 100), ("I2", "bong_sung", 100), ("I3", "ca_linh", 100), ("I4", "bong_sung", 100))
    sm = write_json(os.path.join(md, "hit.json"), {"gather": {"player": {"pos": [62, 24]}, "random_fish": False,
                                                             "hold": hold4, "monsters": [croc]}})
    mo = os.path.join(md, "hit.jsonl.txt")
    headless("--mode", "gather", "--seed", "1", "--ticks", "1", "--scenario", sm, "--out", rel(mo))
    hit = evs(rows(mo), "monster_hit")
    lost = hit[0]["data"]["lost"] if hit else []
    lines.append(f"| Cá Sấu chạm: `lost` là mảng cá thể theo LIFO | [`monsters/hit.jsonl.txt`](monsters/hit.jsonl.txt) | "
                 f"`lost` {json.dumps(lost)} → {ok(ik(lost) == [('I4', 'bong_sung'), ('I3', 'ca_linh')])} |")

    # 7. kho đếm (v1.0/v1.1) khi chạy v1.2 -> mã 2, không ghi đầu ra
    bd = p("bad")
    cnt = write_json(os.path.join(bd, "kho-dem.json"), {"items": {"ca_loc": 1}})
    bad_out = os.path.join(bd, "bad.jsonl.txt")
    msg = headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--inventory", cnt, "--out", rel(bad_out), expect=2)
    lines.append(f"| Kho đếm cũ `{{\"items\":{{\"ca_loc\":1}}}}` khi chạy v1.2 → mã 2 | — | mã 2 "
                 f"({msg.splitlines()[-1] if msg else ''}); file đầu ra {'KHÔNG tạo' if not os.path.exists(bad_out) else 'BỊ TẠO'} |")

    # 8. mode day 2 Ngày: bàn giao giữ id, id I* tăng liên tục xuyên Ngày, tất định
    dd = p("day")
    sd = write_json(os.path.join(dd, "day.json"), {
        "gather": {"random_fish": False, "player": {"pos": [2, 0]},
                   "hold": items(("I1", "ca_loc", 100), ("I2", "bong_sung", 100), ("I3", "bong_sung", 100))},
        "quan": {"random_customers": False, "time_left_ticks": 5}})
    di = write_json(os.path.join(dd, "inputs.json"), DOCK)
    d1, d2 = os.path.join(dd, "day.jsonl.txt"), os.path.join(dd, "day-rerun.jsonl.txt")
    args = ["--mode", "day", "--days", "2", "--seed", "1", "--ticks", "13000", "--scenario", sd, "--inputs", di,
            "--snapshot-every", "600"]
    headless(*args, "--out", rel(d1))
    headless(*args, "--out", rel(d2))
    dr = rows(d1)
    ends = {e["day"]: e["data"]["inventory"]["items"] for e in evs(dr, "gather_end")}
    shop = {}
    for s in snaps(dr):
        if s.get("phase") == "shop":
            shop.setdefault(s["day"], s["stock"])
    ids = {d: [it["id"] for it in v] for d, v in ends.items()}
    shop_ids = {d: [it["id"] for it in v] for d, v in shop.items()}
    d_ok = ids.get(1) == ["I1", "I2", "I3"] and ids.get(2) == ["I4", "I5", "I6"] and shop_ids.get(1) == ids.get(1)
    lines.append(f"| Mode day 2 Ngày: giỏ → kho quán giữ id; Ngày 2 giỏ dựng sẵn nhận id mới nối tiếp | [`day/day.jsonl.txt`](day/day.jsonl.txt) | "
                 f"`gather_end` id {ids}; kho lúc vào Shop Ngày 1 {shop_ids.get(1)} "
                 f"(fresh {[it['fresh'] for it in shop.get(1, [])]}) → {ok(d_ok)} |")
    lines.append(f"| Tất định mode day (chạy lại seed 1) | `day/day-rerun.jsonl.txt` | sha256 {sha(d1)[:12]}… = {sha(d2)[:12]}… → "
                 f"{'GIỐNG TỪNG BYTE' if sha(d1) == sha(d2) else 'KHÁC'} |")

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    write(p("README.md"),
          "# Bằng chứng Phase 3\n\n"
          f"Sinh bằng `python3 tools/proof_p3.py` ở commit **`{commit}`**{' (code có thay đổi chưa commit!)' if dirty else ''}, "
          f"lúc {now}. Contract `{CONTRACT['contract_version']}`, `freshness` = `{json.dumps(F)}`.\n\n"
          "| Kiểm chứng | File | Kết quả |\n|---|---|---|\n" + "\n".join(lines) + "\n")
    print(read(p("README.md")))


if __name__ == "__main__":
    main()

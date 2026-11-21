# Ma trận truy vết Phase 4

> Kiểm chứng trên `78b6474` (nhánh nền `mKhaiTruong/contract-v1.3` sau khi gộp PR #30; PR #29 → `main`), 2026-11-21, Windows 11 + Python 3.12 (`.venv`, shim `python3`) + Chrome. Máy chấm chạy Linux.
> Bằng chứng: [`docs/proof/phase-4/`](../proof/phase-4/). Test: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` → **199 OK, 1 skip** ([`tests-full.txt`](../proof/phase-4/tests-full.txt); skip = test render trình duyệt thật, bật bằng `CHONOI_BENCH_BROWSER=1`).
> Mã AC-P4-xx do nhóm đánh theo các mục và DoD của TICKET-04 (đề ở lab board, không có văn bản trong repo). Giả định ghi ở [clarify #31–#36](../clarify.md).
> Bản bàn giao: `16a095c`, `aa19c7f` (Khuê: contract v1.3, soak), PR #30 (Phong: bench, cảnh báo, tương phản cao), `4658e04` (Khuê: docs).

## Contract + bench

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-01 `contract_version: "1.3"`, khai `bench_cmd`, `soak_cmd` ở gốc; gameplay / tuning / kho / JSONL theo v1.2 | test + đọc | `game.contract.json`; `test_soak.SoakCmd.test_contract_v13_declares_bench_and_soak`; regression P1–P3 không đổi | đạt |
| AC-P4-02 `bench_cmd --seed 42 --duration 30 --out bench.json`: cảnh chuẩn (độ tươi, cá bơi, Cá Sấu, Út Sen đứng ở bến), 1280×720, làm nóng 3 s, đúng 5 trường | chạy lệnh + test | [`bench.json`](../proof/phase-4/bench.json), [`bench-stderr.txt`](../proof/phase-4/bench-stderr.txt) (render Chrome, canvas 1280×720, dpr 1); `test_bench` (5 khóa, kiểu, công thức avg / 1% low, mã 2) | đạt (cách đo: [clarify #34–#35](../clarify.md)) |
| AC-P4-03 Báo cáo mốc avg ≥ 60 FPS, 1% low ≥ 30 FPS, load ≤ 10 s | đọc `bench.json` | avg **120.0**, 1% low **115.64**, frames 3600 / 30.001 s, load **1210 ms**. Headless đồng bộ khung theo tần số màn hình, nên avg chạm trần vsync (lần đo của Phong trên máy 60 Hz: 60.0 / 57.8 / 543 ms) | đạt cả 3 mốc |

## Soak headless

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-04 `soak_cmd --seed 7 --days 10 --out soak.json`: một tiến trình, mỗi Ngày gather → quan → shop, D1–D5 lặp ở Ngày 6–10, trạng thái chạy liên tục | test + chạy hộp đen | [`soak.json`](../proof/phase-4/soak.json); `test_soak.PlanCycle.test_day_6_uses_plan_d1` | đạt (giả định [clarify #31–#32](../clarify.md)) |
| AC-P4-05 `soak.json` có `days, days_completed, crashes, results[]{day, earned, reputation, score}, duration_s`; đạt khi `days_completed = days`, `crashes = 0` | test + chạy hộp đen | `soak.json`: 10 / 10, crashes 0; `test_soak.SoakCmd.test_ten_days_no_crash_and_deterministic` | đạt |
| AC-P4-06 Tất định: chạy lại cùng seed giống nhau ở trường gameplay (bỏ `duration_s`) | chạy 2 lần + so | [`soak-determinism.txt`](../proof/phase-4/soak-determinism.txt) | đạt |

## Cảnh báo + tương phản

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-07 Cảnh báo bằng chữ + biểu tượng: thủy quái gần, oxy sắp hết, khách sắp giận | đọc code + ảnh | `chonoi/web/index.html` (PR #30); ngưỡng [clarify #36](../clarify.md) | đạt |
| AC-P4-08 Chế độ tương phản cao (nút / phím H / `?hc=1`); cả 3 cảnh báo hiện ở chế độ đó | chơi thử tay + ảnh | [`warn/`](../proof/phase-4/warn/): chơi tay `play-gather-hc.png`, `play-quan-hc.png` (+ bản thường `play-*-normal.png`); ảnh Chrome headless `gather-hc.png`, `quan-hc.png` kèm trạng thái `/state` lúc chụp | đạt |

## Đóng gói + phát hành

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-09 Clone sạch chạy bản có giao diện ≤ 3 lệnh (macOS / Linux); README ghi môi trường, điều khiển, test, headless, bench | đọc | `README.md` mục "Chạy từ clone sạch", "Benchmark và soak", "Chạy test" | đạt một phần (README xong; chưa thử clone sạch trên máy Linux / macOS thật) |
| AC-P4-10 `CHANGELOG.md` theo từng phase; rà `CREDITS.md`, `LICENSE` | đọc | `CHANGELOG.md` (phase-1..4); `CREDITS.md` (không có asset ngoài); `LICENSE` (MIT) | đạt |
| AC-P4-11 GitHub Release `v1.0.0` có bản đóng gói + release notes (điểm mới, cách chạy, giới hạn) | `gh release view v1.0.0` | Release `v1.0.0`, đính kèm `chonoi-v1.0.0.zip` (`git archive` của commit gắn tag) | đạt (kiểm sau khi công bố) |
| AC-P4-12 Tag `phase-4` và Release `v1.0.0` cùng trỏ một commit trên `main` | `git rev-parse` | commit merge PR #29 vào `main` | đạt (kiểm sau khi công bố) |

## Regression + ghi chép

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-13 Regression P1–P3 còn hiệu lực đạt | toàn bộ test | `tests-full.txt` **199 OK** (189 P1–P3 + 4 soak + 6 bench, 1 skip); test đổi: `test_fresh_v12` so `"1.3"` (lý do: bump contract, `aa19c7f`) | đạt |
| AC-P4-14 `docs/clarify.md`, `docs/ai-usage-log.md` cập nhật | đọc | clarify #31–#36; ai-usage-log P4 (Khuê, Phong) | đạt |
| AC-P4-15 Retro rà hành động P2, chốt việc tiếp theo, nêu một lỗi AI và cách xác minh | đọc | `docs/retro.md` Phase 4 | đạt |
| AC-P4-16 Phản tư cá nhân đủ người (≤ 200 từ, dẫn commit) | đọc | `docs/members/trinhtuanphong123.md`, `qockhah253.md`, `mKhaiTruong.md` (đều ≤ 200 từ) | đạt |

## Đánh giá ngắn
- **Đạt:** contract v1.3; bench có render (đạt cả 3 mốc); soak 10 Ngày không crash, tất định; 3 cảnh báo + tương phản cao; regression 199 OK; CHANGELOG / CREDITS / LICENSE; retro; tag + Release.
- **Đạt một phần:** chưa thử clone sạch trên Linux / macOS thật.
- Ghi chú: ảnh chơi tay, ai-usage-log P4 của Phong (PR #31) và phản tư của Khuê vào `main` **sau** tag `phase-4` / `v1.0.0`; code không đổi.
- **Mở rộng (leaderboard, phụ đề SFX):** không làm, nhóm 3 người không bắt buộc.
- **Rủi ro:**
  - Bot soak không phục vụ khách (`earned` = 0), nên soak chỉ đi qua nhánh "không đủ nguyên liệu" của quán.
  - Máy chấm không có Chrome thì bench dùng phép đo dự phòng không render (số FPS rất cao, có báo trên stderr), xem clarify #35.

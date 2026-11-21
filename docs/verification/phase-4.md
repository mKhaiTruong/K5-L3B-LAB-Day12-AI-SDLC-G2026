# Ma trận truy vết Phase 4

> Kiểm chứng trên `aa19c7f` (nhánh nền `mKhaiTruong/contract-v1.3`, PR #29 → `main`), 2026-11-21, Windows 11 + Python 3.12 (`.venv`, shim `python3`). Máy chấm chạy Linux.
> Bằng chứng: [`docs/proof/phase-4/`](../proof/phase-4/). Test: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` → **193/193 OK** ([`tests-full.txt`](../proof/phase-4/tests-full.txt)).
> Mã AC-P4-xx do nhóm đánh theo các mục và DoD của TICKET-04 (đề ở lab board, không có văn bản trong repo). Giả định ghi ở [clarify #31–#33](../clarify.md).
> **Cần chạy lại trên commit gắn tag** sau khi PR bench / cảnh báo của Phong merge; các mục "chưa" dưới đây chờ PR đó.

## Contract + lệnh

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-01 `contract_version: "1.3"`, khai `bench_cmd`, `soak_cmd` ở gốc; gameplay / tuning / kho / JSONL theo v1.2 | test + đọc | `game.contract.json`; `test_soak.SoakCmd.test_contract_v13_declares_bench_and_soak`; regression P1–P3 không đổi | đạt |
| AC-P4-02 `bench_cmd --seed 42 --duration 30 --out bench.json`: cảnh chuẩn, 1280×720, làm nóng 3 s, đúng 5 trường | chạy lệnh | `docs/proof/phase-4/bench.json` (Phong) | **chưa** (chờ PR Phong) |
| AC-P4-03 Báo cáo mốc avg ≥ 60 FPS, 1% low ≥ 30 FPS, load ≤ 10 s | đọc `bench.json` | — | **chưa** |

## Soak headless

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-04 `soak_cmd --seed 7 --days 10 --out soak.json`: một tiến trình, mỗi Ngày gather → quan → shop, D1–D5 lặp ở Ngày 6–10, trạng thái chạy liên tục | test + chạy hộp đen | [`soak.json`](../proof/phase-4/soak.json); `test_soak.PlanCycle.test_day_6_uses_plan_d1` | đạt (giả định [clarify #31–#32](../clarify.md)) |
| AC-P4-05 `soak.json` có `days, days_completed, crashes, results[]{day, earned, reputation, score}, duration_s`; đạt khi `days_completed = days`, `crashes = 0` | test + chạy hộp đen | `soak.json`: 10 / 10, crashes 0; `test_soak.SoakCmd.test_ten_days_no_crash_and_deterministic` | đạt |
| AC-P4-06 Tất định: chạy lại cùng seed giống nhau ở trường gameplay (bỏ `duration_s`) | chạy 2 lần + so | [`soak-determinism.txt`](../proof/phase-4/soak-determinism.txt) | đạt |

## Cảnh báo + tương phản

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-07 Cảnh báo bằng chữ / biểu tượng: thủy quái gần, oxy sắp hết, khách sắp giận | chơi thử | `chonoi/web/index.html` (Phong) | **chưa** |
| AC-P4-08 Chế độ tương phản cao; chơi thử cả 3 cảnh báo ở chế độ đó | chơi thử + ảnh | `docs/proof/phase-4/` (Phong) | **chưa** |

## Đóng gói + phát hành

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-09 Clone sạch chạy bản có giao diện ≤ 3 lệnh (macOS / Linux); README ghi môi trường, điều khiển, test, headless, bench | đọc + thử clone sạch | `README.md` mục "Chạy từ clone sạch", "Benchmark và soak", "Chạy test" | đạt một phần (README xong; thử clone sạch trên Linux / macOS chưa ghi lại) |
| AC-P4-10 `CHANGELOG.md` theo từng phase; rà `CREDITS.md`, `LICENSE` | đọc | `CHANGELOG.md` (phase-1..4); `CREDITS.md` (không có asset ngoài); `LICENSE` (MIT) | đạt |
| AC-P4-11 GitHub Release `v1.0.0` có bản đóng gói + release notes (điểm mới, cách chạy, giới hạn) | `gh release view v1.0.0` | — | **chưa** |
| AC-P4-12 Tag `phase-4` và Release `v1.0.0` cùng trỏ một commit trên `main` | `git rev-parse` | — | **chưa** |

## Regression + ghi chép

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-13 Regression P1–P3 còn hiệu lực đạt | toàn bộ test | `tests-full.txt` **193/193** (189 P1–P3 + 4 soak); test đổi: `test_fresh_v12` so `"1.3"` (lý do: bump contract, commit `aa19c7f`) | đạt |
| AC-P4-14 `docs/clarify.md`, `docs/ai-usage-log.md` cập nhật | đọc | clarify #31–#33; ai-usage-log P4 (Khuê; Phong chờ bổ sung) | đạt một phần |
| AC-P4-15 Retro rà hành động P2, chốt việc tiếp theo, nêu một lỗi AI và cách xác minh | đọc | `docs/retro.md` Phase 4 | đạt |
| AC-P4-16 Phản tư cá nhân đủ người (≤ 200 từ, dẫn commit) | đọc | `docs/members/trinhtuanphong123.md` (P1–P3), `qockhah253.md`, `mKhaiTruong.md` | **đạt một phần** (2 mục "tự viết" của Khuê còn trống; Phong chưa thêm P4) |

## Đánh giá ngắn
- **Đạt:** contract v1.3, soak 10 Ngày (không crash, tất định), regression 193/193, CHANGELOG / CREDITS / LICENSE, retro.
- **Chưa:** bench, 3 cảnh báo + tương phản cao (PR của Phong), Release `v1.0.0` + tag `phase-4`.
- **Mở rộng (leaderboard, phụ đề SFX):** không làm, nhóm 3 người không bắt buộc.
- **Rủi ro:** bot soak không phục vụ khách (`earned` = 0), nên soak chỉ đi qua nhánh "không đủ nguyên liệu" của quán; nếu runner lớp dùng input riêng thì đường code khác có thể lộ lỗi.

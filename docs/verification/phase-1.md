# Ma trận truy vết Phase 1

> Kiểm chứng trên `main` @ `47a673f`, ngày 2026-11-21, Windows 11 + Python 3.12 (`.venv`, shim `python3`). Máy chấm chạy Linux. Bằng chứng nằm trong [`docs/proof/phase-1/`](../proof/phase-1/).
> PRD-0 không đánh số AC, nên nhóm tự đặt `AC-P1-xx` theo DoD (mục 7) và luật bắt buộc (mục F, G).
> Test: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` → **88 test, OK** ([`tests.txt`](../proof/phase-1/tests.txt)).

## Lõi buổi sáng (gather)

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P1-01 Bơi `[x,d]`, ramp ≤ 6 tick, chặn mép, hướng 90° = xuống | test hộp đen | `test_smoke_p1.Movement` (6 test) | đạt |
| AC-P1-02 Oxy: dưới nước −1/tick, mặt nước +6/tick (kẹp), `oxygen_empty` một lần, `dive`/`surface` khi đổi phía | test hộp đen | `test_gather_lat1.Lat1Oxygen` (5 test) | đạt |
| AC-P1-03 Ngạt lần đầu ở t+59; nổi lên đúng bước ngạt thì không ngạt; mất 3 Máu → `faint` (`lost` LIFO) → `gather_end fainted`, kho rỗng | test hộp đen + file kho | `test_gather_lat1.Lat1ChokeFaint` (6 test) | đạt |
| AC-P1-04 Hái ở mặt nước: nút ready gần nhất (tính đúng mép, hòa theo id), `hold_full` giữ nút, mọc lại sau 20 s | test hộp đen | `test_gather_lat2` l2_01–l2_08 | đạt |
| AC-P1-05 Bắt cá dưới nước: đàn gần nhất, đủ yield, cooldown 30 tick; thiếu chỗ → `hold_full`, không đặt cooldown, không thử đàn khác | test hộp đen | `test_gather_lat2` l2_09–l2_16 | đạt (đã chốt theo TICKET-02, [clarify #5](../clarify.md)) |
| AC-P1-06 Cập bến xét trước hái; hết giờ thì giữ giỏ; hái/bắt ở bước cuối vẫn vào kho | test + chạy trọn ca | `test_time_ends_gather_and_keeps_hold`, l2_06; [`determinism-exitcodes.txt`](../proof/phase-1/determinism-exitcodes.txt) §2 (`reason: time` ở tick 10800) | đạt |
| AC-P1-07 6 đàn cá mặc định đứng yên (có cả hai loài) | test hộp đen | l2_16 | đạt (giả định [clarify #4](../clarify.md)) |

## Lõi buổi tối (quan)

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P1-08 Khách theo lịch (120, mỗi 900 tick), bàn trống id nhỏ nhất, chọn món theo seed trong món đủ kho khả dụng, giữ chỗ ngay; `no_dish` | test + chạy trọn ca | `test_quan.Customers` (6 test); §2 trong `determinism-exitcodes.txt` (khách đến ở 120 / 3720 / 7320) | đạt (giả định [clarify #2](../clarify.md)) |
| AC-P1-09 Hết kiên nhẫn (3600 tick) → `customer_left patience`, uy tín −0.5 | test + chạy trọn ca | `test_patience_leave_cuts_reputation`; §2: rời đúng 3600 tick sau khi đến | đạt |
| AC-P1-10 Interact: chọn (khoảng cách, bếp trước bàn, id); nấu → bưng → phục vụ; boa `floor(giá×0.2)` khi tỷ lệ kiên nhẫn ≥ 0.5; ăn xong trả tiền | test | `test_quan.Kitchen` (cook→pick→serve→pay, ngưỡng boa đúng 0.5, bếp trước bàn, phục vụ đúng tick kiên nhẫn 0) | đạt (giả định [clarify #6](../clarify.md)) |
| AC-P1-11 Hết ca: khách đang ăn trả `closing`, khách chờ rời không trừ uy tín, rồi `quan_end` | test + chạy trọn ca | `test_closing_paying_and_leaving`; §2 (C3 `closing`, uy tín giữ 2.0) | đạt |
| AC-P1-12 Điểm = `earned + 100 × floor(reputation)` ở snapshot và `end` | chạy trọn ca | §2: `earned 0, reputation 2.0 → score 200` | đạt |

## Test Contract v1.0

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P1-13 `game.contract.json` khớp preset mục A, dải hợp lệ được kiểm khi nạp | so từng khóa với preset; chạy `--ticks 0` hai mode | `determinism-exitcodes.txt` §3 (exit 0) | đạt |
| AC-P1-14 Cờ headless, mã thoát 0/1/2, chẩn đoán qua stderr | test + chạy tay | `test_con_03_*`, `test_inventory_flags_mode_mismatch_exit_2`; §3 | đạt |
| AC-P1-15 Scenario mâu thuẫn → mã 2 (gather + quan, gồm giữ quá tồn kể cả với `--inventory`) | test | `test_scenario_gather` (5), `test_scenario_quan` (9), `test_quan_fixture_khong_hop_le_exit_2`; §3 | đạt (giả định [clarify #7–#10](../clarify.md)) |
| AC-P1-16 Cùng seed + đầu vào → JSONL giống từng byte | chạy 2 lần, so sha256 | `test_con_02_deterministic_bytes`, `test_deterministic_same_seed`; §1 (gather/quan seed 7 giống nhau, seed 8 khác) | đạt |
| AC-P1-17 Smoke 2 tiến trình: gather ghi kho đúng 1 lần, quán tick 0 có `stock` đúng file | chạy đúng 2 lệnh mục G | [`smoke-dock-quan.txt`](../proof/phase-1/smoke-dock-quan.txt): `stock = {"bong_sung": 2, "ca_loc": 1}` → ĐẠT; `test_inv_01_*` | đạt |
| AC-P1-18 Chạm `--ticks` trước khi kết thúc → không ghi file kho; sai schema kho → mã 2 | test | `test_inv_01_not_written_when_tick_limit_first`, `test_inv_bad_schema_exit_2`; §3 (`ca_tra` → 2) | đạt |

## DoD (PRD-0 mục 7)

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P1-19 Chơi được 2 buổi, HUD đọc được | chơi thử `chonoi.live` | Phong chơi thử HUD sáng (giỏ 12/12, `hold_full` ở N4) và chạy một lượt hái → bắt → cập bến → quán ([standup](../standup.md), [phản tư Phong](../members/trinhtuanphong123.md)); `test_live` | **đạt một phần**: HUD tối hiện `stock` là tồn vật lý (gồm phần giữ chỗ), chưa phải "kho khả dụng". Snapshot đúng PRD; cần sửa `chonoi/web/index.html` (file khung) ở phase sau |
| AC-P1-20 README: chạy từ clone sạch ≤ 3 lệnh, điều khiển, cách tính điểm, test 1 lệnh | đọc README | [`README.md`](../../README.md) | đạt |
| AC-P1-21 Hợp đồng kho có schema + ví dụ hợp lệ | đọc | [`docs/contracts/README.md`](../contracts/README.md) | đạt |
| AC-P1-22 Fork chung, commit theo tài khoản, mỗi người ≥ 3 commit, `TEAM.md` + `team_size` khớp | `git log --no-merges`; `tools/check_team.py` | Khuê 5 · Phong 6 · Khánh 4 commit (không tính merge); `team_size = 3` | **đạt một phần**: `check_team.py` báo "số thành viên phải từ 4 đến 6 (đang có 3)", nhóm chỉ có 3 người ([clarify #1](../clarify.md), chờ giảng viên) |
| AC-P1-23 Ghi chép tối thiểu (clarify, ai-usage-log, members, verification, proof) | đọc | `docs/` | đạt (phản tư cá nhân còn vài mục để từng người tự viết) |
| AC-P1-24 Tag `phase-1` trỏ tới commit bàn giao trên `main` | `git tag` | — | chưa (Integrator gắn sau khi merge PR này) |

## Đánh giá ngắn
- **Đạt:** toàn bộ luật lõi gather/quan, Test Contract v1.0, smoke 2 tiến trình, tất định (88/88 test).
- **Đạt một phần:** HUD tối chưa hiện "kho khả dụng"; nhóm 3 người (đề yêu cầu 4–6).
- **Rủi ro:** 9 giả định chưa được Anh Năm xác nhận vì bot trả lỗi `not_granted` (clarify #2–#10). Test ẩn có thể chấm khác ở các chỗ này.
- **Chỉnh cho phase sau:** sửa HUD tối (`kho khả dụng = stock − reserved`); hỏi lại Anh Năm khi bot dùng được; chạy test trên Linux (CI) để khớp máy chấm.

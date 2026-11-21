# Ma trận truy vết Phase 3

> Kiểm chứng trên `4df8b78` (nhánh nền `mKhaiTruong/contract-v1.2`, PR #22 → `main`), 2026-11-21, Windows 11 + Python 3.12 (`.venv`, shim `python3`). Máy chấm chạy Linux.
> Bằng chứng: [`docs/proof/phase-3/`](../proof/phase-3/) (sinh bằng `tools/proof_p3.py`). Test: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` → **189/189 OK** ([`tests-full.txt`](../proof/phase-3/tests-full.txt)).
> Bản bàn giao: nhánh nền gồm `3d24de2` (Khuê, contract v1.2 + `chonoi/fresh.py`), PR #26 (Phong, gather), #23 + #27 (Khánh, quán + day), #25 (Khánh, HUD).
> Mã AC-P3-xx do nhóm đánh theo các mục của TICKET-03 (đề ở lab board, không có văn bản trong repo). Giả định ghi ở [clarify #24–#30](../clarify.md).

## Contract + kho cá thể

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P3-01 `contract_version: "1.2"`, `tuning.freshness` (100 / 0.5 / 0.25 / 30), kiểm dải lúc nạp | test | `game.contract.json`, `chonoi/contract.py`; `test_fresh_v12.Units.test_contract_v12_rates` | đạt |
| AC-P3-02 File kho `{"items":[{id,kind,fresh}]}` theo id; sai schema / id trùng / fresh ngoài [0, 100] / kho đếm cũ → mã 2 | test + chạy hộp đen | `test_fresh_v12.InventoryFile` (4 test); proof "Kho đếm cũ → mã 2" (không tạo file đầu ra) | đạt |
| AC-P3-03 Scenario v1.2: `gather.hold`, `quan.stock` là mảng cá thể; `reserved` là mảng id, id lạ / ươn / dùng chung / sai công thức → mã 2 | test | `test_scenario_quan.test_reserved_ids_v12`, `test_reserved_must_match_recipe`, `test_reserved_within_stock_exit_0`; `test_quan.FreshStock.test_reserved_spoiled_or_unknown_in_fixture_exit_2` | đạt |

## Gather

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P3-04 Giỏ hao 0.5/s ở đầu bước, kẹp 0 | test + chạy hộp đen | `test_gather_fresh` fr02, fr05; proof [`rate/`](../proof/phase-3/rate/): 60 tick → 99.5 | đạt |
| AC-P3-05 `spoiled` (location `hold`) đúng một lần khi qua ngưỡng, theo id; ví dụ PRD fresh 30 → tick 1 | test + chạy hộp đen | `test_gather_fresh` fr01, fr03, fr04; proof [`threshold/gather.jsonl.txt`](../proof/phase-3/threshold/gather.jsonl.txt): `spoiled I1` ở tick 1, một lần trong 120 tick | đạt |
| AC-P3-06 Hái / bắt: mỗi đơn vị là cá thể mới fresh 100, id `I*` nối tiếp, hao từ bước sau; hàng ươn vẫn chiếm chỗ | test | `test_gather_fresh` fr06, fr07, fr08; `test_gather_lat2` l2_01, l2_09 | đạt |
| AC-P3-07 Mất hàng (Cá Sấu chạm, ngất) là mảng cá thể theo LIFO | test + chạy hộp đen | `test_gather_monsters` m03, m05, m06; `test_gather_lat1.test_l1_09`; `test_monsters.test_apply_hit_lifo_and_recoil`; proof [`monsters/hit.jsonl.txt`](../proof/phase-3/monsters/hit.jsonl.txt): `lost` = I4, I3 | đạt |
| AC-P3-08 Smoke bàn giao kho (PRD): `gather --inventory-out` → `quan --inventory --ticks 0`, so id / kind / fresh | 2 tiến trình + so byte | proof [`handoff/`](../proof/phase-3/handoff/): file kho = `gather_end.inventory` = `stock` quán tick 0 (I1 ca_linh, fresh 99.9917, lệch ≤ 0.01 do làm tròn JSONL); chạy lại giống từng byte; `test_smoke_p1.test_inv_01_*`, `test_gather_fresh.test_fr09` | đạt |

## Quán + day

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P3-09 Kho hao 0.25/s; `spoiled` (location `stock`) một lần, theo id | test + chạy hộp đen | `test_quan.FreshStock.test_stock_decays_and_spoiled_once_by_id`; proof `threshold/quan.jsonl.txt` (I2, I10 ở tick 1, I3 không ươn), `rate/` (240 tick → 99.0) | đạt |
| AC-P3-10 Giữ chỗ cá thể tươi nhất, hòa theo id, bỏ hàng ươn | test | `test_quan.FreshStock.test_reserve_freshest_tie_by_id`, `test_fresh_v12.ReserveAndPrice.test_reserve_freshest_tie_by_id_skip_spoiled` | đạt |
| AC-P3-11 Hàng đang giữ vừa ươn → nhả hết rồi giữ lại một lần theo (`order_tick`, id bàn); không đủ → `unfulfillable` | test | `test_quan.FreshStock` (3 test: rereserve_once, no_replacement_unfulfillable, releases_all_first) | đạt (giả định [clarify #25](../clarify.md)) |
| AC-P3-12 Giá = `floor(giá × fresh trung bình / 100)` lúc `cook_started`; `items` là mảng cá thể (kind rồi id) | test + chạy hộp đen | `test_quan.FreshStock` (price, sorted_by_kind_then_id), `test_quan.Kitchen.test_cook_pick_serve_pay_with_tip` (60 → 59); proof [`price/`](../proof/phase-3/price/): fresh 50.5 → 30 | đạt |
| AC-P3-13 Day: một `ItemIds` cả lượt; bàn giao giỏ → kho quán giữ id + độ tươi; Ngày 2 giỏ dựng sẵn nhận id mới | test + chạy hộp đen 2 Ngày | `test_day.ItemIdsAcrossDays`, `test_day.DayFlow.test_gather_to_quan_to_shop_and_stock_carried`; proof [`day/`](../proof/phase-3/day/): `gather_end` Ngày 1 I1–I3, Ngày 2 I4–I6, kho lúc vào Shop = I1–I3 (fresh 99.971 = 100 − 7/240) | đạt (giả định [clarify #26](../clarify.md)) |
| AC-P3-14 Tất định: chạy lại cùng seed → giống từng byte | so sha256 | proof: bàn giao (JSONL + file kho), mode day 2 Ngày | đạt |

## UI + DoD

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P3-15 HUD: giỏ / kho vẽ từng cá thể, thanh tươi, hàng ươn mờ + ✕, hàng đang giữ chỗ có viền, cảnh báo `spoiled` | đọc code + chơi thử | `chonoi/web/index.html` (PR #25); ảnh chơi thử [`docs/proof/phase-3/hud/`](../proof/phase-3/hud/) | đạt (ảnh có cá thể, thanh tươi, ươn mờ + ✕, viền giữ chỗ; dòng cảnh báo ~2,5 giây chưa lọt vào ảnh, event `spoiled` thấy ở log sự kiện HUD) |
| AC-P3-16 Regression P1/P2 với contract v1.2; test đổi có ghi lý do | toàn bộ test | `tests-full.txt` **189/189**; fixture đổi sang cá thể (lý do trong commit PR #23, #26 và mục "Cách cập nhật fixture" ở `CHANGELOG.md`) | đạt |
| AC-P3-17 Hợp đồng + changelog cập nhật breaking change | đọc | `docs/contracts/README.md` (v1.2), `docs/contracts/inventory.sample.json`, `CHANGELOG.md` | đạt |
| AC-P3-18 Ghi chép: clarify, ai-usage-log, retro | đọc | `docs/clarify.md` #24–#30, `docs/retro.md` Phase 3, `docs/ai-usage-log.md` (P3 đủ Khuê, Khánh, Phong) | đạt |
| AC-P3-19 Tag `phase-3` trỏ tới commit bàn giao trên `main` | `git tag` | — | chưa |

## Đánh giá ngắn
- **Đạt:** toàn bộ lõi headless Phase 3: kho cá thể + độ tươi ở gather, quán, day; giữ chỗ theo id, giữ lại khi ươn, giá theo độ tươi; smoke bàn giao kho theo PRD, tất định; regression 189/189.
- **Đạt:** HUD độ tươi có ảnh chơi thử giỏ / kho (`docs/proof/phase-3/hud/`); ai-usage-log P3 đủ 3 người.
- **Còn nợ từ P2 (không thuộc Phase 3):** UI menu / DayIntro / DayResult / Summary / pause menu (AC-P2-17); `chonoi/live.py` chưa có mode `day`.
- **Rủi ro:** đơn vị 240 / điểm và làm tròn 3 chữ số là giả định của nhóm (test ẩn so `fresh` chặt hơn ±0.01 có thể lệch); quy tắc giữ lại khi ươn (#25) và kho không mang sang Ngày sau (#26) chưa được xác nhận.

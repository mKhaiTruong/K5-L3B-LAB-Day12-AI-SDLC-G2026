# Bằng chứng Phase 3

Sinh bằng `python3 tools/proof_p3.py` ở commit **`4df8b78`**, lúc 2026-11-21 19:38. Contract `1.2`, `freshness` = `{"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30}`.

| Kiểm chứng | File | Kết quả |
|---|---|---|
| Toàn bộ test (`unittest discover -s tests -v`) | [`tests-full.txt`](tests-full.txt) | Ran 189 tests in 14.401s · OK |
| Smoke bàn giao kho (PRD): giỏ `I1 ca_linh 100`, cập bến tick 0 → `quan --inventory --ticks 0` | [`handoff/`](handoff/) | file kho `[{"id": "I1", "kind": "ca_linh", "fresh": 99.99166666666666}]`; `gather_end.inventory` `[{"id": "I1", "kind": "ca_linh", "fresh": 99.992}]`; quán tick 0 `stock` `[{"id": "I1", "kind": "ca_linh", "fresh": 99.992}]`; id/kind khớp, fresh lệch ≤ 0.01 → ĐẠT |
| Tất định bàn giao (chạy lại seed 42) | `handoff/gather-rerun.jsonl.txt`, `kho-rerun.json` | JSONL 2338952c8a27… = 2338952c8a27…, kho e39f6f48e417… = e39f6f48e417… → GIỐNG TỪNG BYTE |
| Ngưỡng ươn gather: fresh 30 → `spoiled` ở tick 1, một lần trong 120 tick | [`threshold/gather.jsonl.txt`](threshold/gather.jsonl.txt) | [(1, {'item_id': 'I1', 'kind': 'ca_linh', 'location': 'hold'})] → ĐẠT |
| Ngưỡng ươn quán: I2, I10 fresh 30 + I3 fresh 31 → `spoiled` theo id ở tick 1 | [`threshold/quan.jsonl.txt`](threshold/quan.jsonl.txt) | [(1, {'item_id': 'I2', 'kind': 'ca_loc', 'location': 'stock'}), (1, {'item_id': 'I10', 'kind': 'ca_loc', 'location': 'stock'})]; I3 không ươn → ĐẠT |
| Tốc độ hao: gather 0.5/s (60 tick), quán 0.25/s (240 tick) | [`rate/`](rate/) | gather 99.5 (mong 99.5), quán 99.0 (mong 99.0) → ĐẠT |
| Giá theo độ tươi: món 60, cá I1 fresh 50.5 (hao 1 bước) | [`price/quan.jsonl.txt`](price/quan.jsonl.txt) | `cook_started` {"stove_id": "B1", "order_id": "C1", "dish_id": "ca_loc_nuong_trui", "items": [{"id": "I1", "kind": "ca_loc", "fresh": 50.496}], "base_price": 30} (mong base_price 30) → ĐẠT |
| Cá Sấu chạm: `lost` là mảng cá thể theo LIFO | [`monsters/hit.jsonl.txt`](monsters/hit.jsonl.txt) | `lost` [{"id": "I4", "kind": "bong_sung", "fresh": 99.992}, {"id": "I3", "kind": "ca_linh", "fresh": 99.992}] → ĐẠT |
| Kho đếm cũ `{"items":{"ca_loc":1}}` khi chạy v1.2 → mã 2 | — | mã 2 (đầu vào sai: file kho.items phải là mảng cá thể {id, kind, fresh}); file đầu ra KHÔNG tạo |
| Mode day 2 Ngày: giỏ → kho quán giữ id; Ngày 2 giỏ dựng sẵn nhận id mới nối tiếp | [`day/day.jsonl.txt`](day/day.jsonl.txt) | `gather_end` id {1: ['I1', 'I2', 'I3'], 2: ['I4', 'I5', 'I6']}; kho lúc vào Shop Ngày 1 ['I1', 'I2', 'I3'] (fresh [99.971, 99.971, 99.971]) → ĐẠT |
| Tất định mode day (chạy lại seed 1) | `day/day-rerun.jsonl.txt` | sha256 34dfa018b83c… = 34dfa018b83c… → GIỐNG TỪNG BYTE |

# Changelog
## Unreleased

## phase-4 / v1.0.0 — 2026-11-21 (Test Contract v1.3)
- Contract: `contract_version: "1.3"`; khai `bench_cmd` (`python3 -m chonoi.bench`) và `soak_cmd` (`python3 -m chonoi.soak`) ở gốc `game.contract.json`. Gameplay, tuning, kho, JSONL **không đổi** so với v1.2, nên không cần sửa fixture.
- Soak: `chonoi/soak.py` chạy N Ngày trong một tiến trình (kế hoạch D1–D5 lặp ở Ngày 6–10; tiền, uy tín, cấp, id cá thể chạy liên tục), ghi `soak.json`; `tests/test_soak.py`.
- Bench: `chonoi/bench.py`, cảnh lặn có render 1280×720, ghi `bench.json` (Phong).
- UI: 3 cảnh báo có chữ + biểu tượng (thủy quái gần, oxy sắp hết, khách sắp giận) và chế độ tương phản cao (Phong).
- README: yêu cầu môi trường, 3 lệnh từ clone sạch, lệnh headless / bench / soak / test, hạn chế đã biết.
- Bằng chứng `docs/proof/phase-4/`, ma trận `docs/verification/phase-4.md`.

## phase-3 — 2026-11-21 (Test Contract v1.2)
### BREAKING: kho cá thể + độ tươi
- File kho `{"items":{kind:n}}` → `{"items":[{"id","kind","fresh"}]}` (sắp theo id). Chạy v1.2 mà đọc kho đếm → **mã 2**.
- `gather.hold`, `quan.stock` trong scenario là mảng cá thể; `customers[].reserved` là mảng id cá thể.
- Event: `faint.lost`, `monster_hit.lost`, `cook_started.items`, `gather_end.inventory.items` là mảng cá thể; thêm `spoiled {item_id, kind, location: hold|stock}`.
- Snapshot: `hold` (gather), `stock` (quán, Shop) là mảng cá thể.

**Cách cập nhật fixture / scenario cũ**
```text
"hold": ["ca_loc","bong_sung"]          →  "hold": [{"id":"I1","kind":"ca_loc","fresh":100},{"id":"I2","kind":"bong_sung","fresh":100}]
"stock": {"ca_loc": 2}                  →  "stock": [{"id":"I1","kind":"ca_loc","fresh":100},{"id":"I2","kind":"ca_loc","fresh":100}]
"reserved": {"ca_loc": 1}               →  "reserved": ["I1"]
{"items": {"bong_sung":2,"ca_loc":1}}   →  {"items": [{"id":"I1","kind":"ca_loc","fresh":100}, ...]}
```
Test so `lost` / `hold` theo `(id, kind)`; `fresh` trong JSONL so với dung sai ±0.01 (làm tròn 3 chữ số).

### Luật
- `tuning.freshness`: gather −0.5/s, quán −0.25/s, ươn khi `fresh < 30`; nội bộ số nguyên 240 đơn vị/điểm (`chonoi/fresh.py`).
- Quán: giữ chỗ cá thể tươi nhất (hòa theo id), bỏ hàng ươn; hàng đang giữ vừa ươn → nhả và giữ lại một lần, không đủ → `unfulfillable`; giá = `floor(giá × fresh trung bình / 100)` lúc `cook_started`.
- Day: một `ItemIds` cho cả lượt; bàn giao giỏ → kho quán giữ nguyên id và độ tươi; từ Ngày 2 giỏ dựng sẵn nhận id mới.
- HUD: giỏ/kho vẽ từng cá thể, thanh tươi, hàng ươn mờ + ✕, viền vàng cho hàng đang giữ chỗ, cảnh báo `spoiled`.
- 189 test; bằng chứng `docs/proof/phase-3/` (`tools/proof_p3.py`).

## phase-2 — 2026-11-21 (Test Contract v1.1)
- Số chuẩn TICKET-02, 6 nguyên liệu / 6 món, cá bơi + sinh theo seed, Cá Sấu (theo Ngày), quán 2 bếp / 4 bàn
- Mode `day` (gather → quan → shop), Shop + cấp, pause, `--days 1..5`
- 157 test; bằng chứng `docs/proof/phase-2/`

## phase-1 — 2026-11-21
- gather: bơi, oxy, ngạt, Máu, ngất (LIFO), hái nút, bắt cá, cập bến, ghi file kho (lát 1–2)
- quan: khách theo lịch, giữ chỗ, kiên nhẫn, bếp, bưng, phục vụ, boa, uy tín, hết ca (lát 3–4)
- scenario: kiểm mâu thuẫn mã 2 cho gather và quan, gồm giữ quá tồn
- docs: hợp đồng kho/sự kiện, README nhóm, clarify, verification + proof Phase 1
- 88 test (unittest), smoke dock → quán đạt

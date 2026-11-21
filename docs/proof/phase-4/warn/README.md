# Chơi thử 3 cảnh báo + tương phản cao (TICKET-04)

Chụp tay trên `python -m chonoi.live` (nhánh `trinhtuanphong123/bench-p4`, commit `5e5ca16`), seed 1, Chrome trên Windows. Tương phản cao bật bằng `?hc=1` / phím **H** / nút góc phải.

| Ảnh | Chế độ | Lệnh | Thấy trong ảnh |
|---|---|---|---|
| [`gather-hc.png`](gather-hc.png) | **tương phản cao** | `python -m chonoi.live --mode gather --scenario docs/proof/phase-4/warn/gather.json` | dải vàng chữ đen "🫧 OXY SẮP HẾT — còn 2 s" và "🐊 THỦY QUÁI GẦN — Cá Sấu M1 cách 1 m"; Cá Sấu đỏ viền vàng + vòng phát hiện vàng; nền nước đặc, chữ trắng viền đen |
| [`quan-hc.png`](quan-hc.png) | **tương phản cao** | `python -m chonoi.live --mode quan --scenario docs/proof/phase-4/warn/quan.json` | dải vàng "😠 KHÁCH SẮP GIẬN — C1 bàn T1 còn 12 s"; khách viền vàng + mặt giận; sàn đen, bàn viền trắng |
| [`gather-normal.png`](gather-normal.png) | thường | như trên | cùng 2 cảnh báo, dải đỏ chữ trắng |
| [`quan-normal.png`](quan-normal.png) | thường | như trên | cùng cảnh báo khách, dải đỏ, khách viền đỏ |

Kịch bản: [`gather.json`](gather.json) (Út Sen ở [53, 22], cách Cá Sấu M1 7.3 m < `detect_radius` 10, oxy 420 / 1800 < 25%), [`quan.json`](quan.json) (khách C1 còn 840 / 3600 tick kiên nhẫn < 25%). Chạy headless cùng kịch bản: M1 chuyển `chase` trước tick 60, khách C1 `waiting` suốt 300 tick đầu.

Ghi chú: hai ảnh gather chụp lúc Út Sen vừa ngất (khung "fainted" ở giữa), cảnh báo vẫn hiện vì Cá Sấu còn trong bán kính và oxy còn thấp. Ngưỡng cảnh báo: `docs/clarify.md` #36.

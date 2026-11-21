# Cảnh báo dễ nhận biết ở chế độ tương phản cao (AC-P4-07, AC-P4-08)

Chụp trên `78b6474` bằng Chrome headless 1280×720, trang mở với `?hc=1` (tương phản cao bật sẵn, giống bấm **H**). Máy chủ là `chonoi.live` (cùng sim với headless), seed 1, chạy ~1,5 s trước khi chụp.

| Ảnh | Kịch bản | Thấy trong ảnh | Trạng thái `/state` lúc chụp |
|---|---|---|---|
| [`gather-hc.png`](gather-hc.png) | [`gather.json`](gather.json) | dải vàng chữ đen **🫧 OXY SẮP HẾT — còn 4 s, nổi lên thở!** và **🐊 THỦY QUÁI GẦN — Cá Sấu M1 cách 1 m**; vòng phát hiện nét đứt vàng quanh M1; nút "Tương phản cao (H): BẬT" | tick 115, oxy 305 / 1800 tick (< 25%), M1 `chase`, cách người chơi ~1,5 m |
| [`quan-hc.png`](quan-hc.png) | [`quan.json`](quan.json) | dải **😠 KHÁCH SẮP GIẬN — C1 bàn T1 còn 11 s**; khách C1 viền vàng + 😠; thanh kiên nhẫn gần cạn | tick 123, C1 `waiting`, kiên nhẫn 717 / 3600 tick (< 25%) |

Ngưỡng của từng cảnh báo: [clarify #36](../../../clarify.md). Cảnh báo chỉ là phần hiển thị, không đổi luật / JSONL (regression 199 OK).

# Cảnh báo dễ nhận biết ở chế độ tương phản cao (AC-P4-07, AC-P4-08)

Chụp trên `78b6474` bằng Chrome headless 1280×720, trang mở với `?hc=1` (tương phản cao bật sẵn, giống bấm **H**). Máy chủ là `chonoi.live` (cùng sim với headless), seed 1, chạy ~1,5 s trước khi chụp.

| Ảnh | Kịch bản | Thấy trong ảnh | Trạng thái `/state` lúc chụp |
|---|---|---|---|
| [`gather-hc.png`](gather-hc.png) | [`gather.json`](gather.json) | dải vàng chữ đen **🫧 OXY SẮP HẾT — còn 4 s, nổi lên thở!** và **🐊 THỦY QUÁI GẦN — Cá Sấu M1 cách 1 m**; vòng phát hiện nét đứt vàng quanh M1; nút "Tương phản cao (H): BẬT" | tick 115, oxy 305 / 1800 tick (< 25%), M1 `chase`, cách người chơi ~1,5 m |
| [`quan-hc.png`](quan-hc.png) | [`quan.json`](quan.json) | dải **😠 KHÁCH SẮP GIẬN — C1 bàn T1 còn 11 s**; khách C1 viền vàng + 😠; thanh kiên nhẫn gần cạn | tick 123, C1 `waiting`, kiên nhẫn 717 / 3600 tick (< 25%) |

**Chơi thử tay (Phong)**: Chrome trên Windows, `python -m chonoi.live` cùng hai kịch bản trên, chụp màn hình trong lúc chơi (code như `5e5ca16`).

| Ảnh | Chế độ | Thấy trong ảnh |
|---|---|---|
| [`play-gather-hc.png`](play-gather-hc.png) | tương phản cao (`?hc=1`, nút "BẬT") | dải vàng 🫧 OXY SẮP HẾT (còn 2 s) và 🐊 THỦY QUÁI GẦN (M1 cách 1 m); Cá Sấu đỏ viền vàng, vòng phát hiện vàng. Chụp lúc Út Sen vừa ngất nên giữa màn hình có khung "fainted" |
| [`play-quan-hc.png`](play-quan-hc.png) | tương phản cao | dải vàng 😠 KHÁCH SẮP GIẬN — C1 bàn T1 còn 12 s; khách viền vàng; sàn đen, bàn viền trắng |
| [`play-gather-normal.png`](play-gather-normal.png), [`play-quan-normal.png`](play-quan-normal.png) | thường | cùng 3 cảnh báo, dải đỏ chữ trắng |

Ngưỡng của từng cảnh báo: [clarify #36](../../../clarify.md). Cảnh báo chỉ là phần hiển thị, không đổi luật / JSONL (regression 199 OK).

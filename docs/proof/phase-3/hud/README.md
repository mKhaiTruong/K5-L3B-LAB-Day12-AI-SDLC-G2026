# Chơi thử HUD độ tươi (AC-P3-15)

Chụp tay trên `python -m chonoi.live` ở nhánh `mKhaiTruong/phase-3-close` (code game như `4df8b78`), seed 1. Không do `tools/proof_p3.py` sinh.

| Ảnh | Lệnh | Thấy trong ảnh |
|---|---|---|
| [`gather.png`](gather.png) | `python -m chonoi.live --mode gather --scenario docs/proof/phase-3/hud/gather.json` | Giỏ 4/12 vẽ từng cá thể: cá lóc I1 thanh xanh, bông súng I2 thanh vàng (55 → 44), cá kèo I3 (fresh 20) và cá linh I4 (ươn ở tick 1201) mờ + ✕; tóm tắt "ươn 2"; log sự kiện có `t1201 spoiled {"item_id":"I4","kind":"ca_linh","location":"hold"}` |
| [`quan.png`](quan.png) | `python -m chonoi.live --mode quan --scenario docs/proof/phase-3/hud/quan.json` | Kho 4 cá thể: cá lóc I1 viền vàng (khách C1 giữ chỗ cho `ca_loc_nuong_trui`), cá linh I4 (fresh 20) mờ + ✕; dòng kho "ươn 1 · viền vàng = đang giữ chỗ" |

Kịch bản: [`gather.json`](gather.json), [`quan.json`](quan.json). Chạy headless cùng kịch bản (1300 tick, seed 1): gather `spoiled` I4 ở tick 1201; quán `spoiled` I2 ở tick 1201, C1 giữ `I1` suốt.

Chưa chụp được dòng cảnh báo "⚠ … đã ươn" (chỉ hiện ~2,5 giây sau event); event `spoiled` thấy ở log sự kiện của HUD.

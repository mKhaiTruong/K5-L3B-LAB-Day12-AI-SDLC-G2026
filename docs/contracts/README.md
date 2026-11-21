# Hợp đồng tích hợp — Test Contract v1.3 (Phase 4)

> Chốt ở kickoff P1 (v1.0), cập nhật v1.1 (P2), v1.2 (P3: kho cá thể + độ tươi) và **v1.3 (P4: thêm `bench_cmd`, `soak_cmd`; gameplay / kho / JSONL giữ như v1.2)**. Đổi hợp đồng: báo cả nhóm, PR cần người khác duyệt, ghi lý do (ADR hoặc mục "Lịch sử thay đổi" cuối file).
> Nguồn: PRD-0 mục C (inputs), E (output/sự kiện), F (luật), G (kho); TICKET-02, TICKET-03. Số liệu chỉ đọc từ `game.contract.json`.

## 1. File kho (gather → quan) — PRD-0 mục G, TICKET-03

**Schema v1.2** (`contract_version: "1.2"`)

```json
{"items": [{"id": "I<n>", "kind": "<kind>", "fresh": <số 0..100>}, ...]}
```

| Quy tắc | Chi tiết |
|---|---|
| Khóa gốc | chỉ có `items` (**mảng**). Thêm khóa khác → bên đọc từ chối (mã 2) |
| Mỗi cá thể | đúng 3 khóa `id, kind, fresh`. Thiếu / thừa khóa → mã 2 |
| `id` | chuỗi không rỗng, **không trùng** trong file. Bên ghi dùng `I1, I2…` (cấp bởi `chonoi.fresh.ItemIds`) |
| `kind` hợp lệ | danh mục nguyên liệu của contract (`chonoi/inventory.py`). Kind lạ → mã 2 |
| `fresh` | số hữu hạn trong `[0, 100]`; ươn khi `fresh < tuning.freshness.spoiled_below` (30). Ươn vẫn là cá thể hợp lệ |
| Thứ tự | bên ghi sắp theo id (`I2` trước `I10`) |
| Kho rỗng | `{"items":[]}` |
| Trần giỏ | `hold_capacity` **không** áp lên kho quán |
| Kho đếm cũ | `{"items":{kind:n}}` khi chạy v1.2 → **mã 2** (v1.0/v1.1 vẫn đọc kho đếm, `inventory.read_inventory`) |

**Ví dụ hợp lệ** (giỏ 3 cá thể vừa hái, xem `inventory.sample.json`)

```json
{"items":[{"id":"I1","kind":"ca_loc","fresh":100},{"id":"I2","kind":"bong_sung","fresh":100},{"id":"I3","kind":"bong_sung","fresh":100}]}
```

**Ví dụ không hợp lệ (mã 2):** `{"items":{"ca_loc":1}}` · `{"items":[{"id":"I1","kind":"ca_tra","fresh":100}]}` · `{"items":[{"id":"I1","kind":"ca_loc","fresh":101}]}` · `{"items":[{"id":"I1","kind":"ca_loc"}]}` · hai cá thể cùng `id` · `{"items":[],"money":0}`

**Độ tươi** (`tuning.freshness`, xem [clarify #27–#29](../clarify.md)): nội bộ lưu số nguyên `u`, 240 đơn vị / điểm (gather −2/tick = 0.5/s, quán −1/tick = 0.25/s, ươn khi `u < 7200`). Ra ngoài luôn qua `fresh.public()` → `fresh = u / 240`. JSONL làm tròn 3 chữ số; file kho ghi đủ chính xác.

**Ai ghi / ai đọc / khi nào**

| | Gather (ghi, `--inventory-out`) | Quán (đọc, `--inventory`) |
|---|---|---|
| Khi nào | đúng **một lần** khi có `gather_end` (`time` / `docked` / `fainted`) | lúc khởi tạo, trước khi ghi JSONL |
| Nội dung | khớp object `inventory` trong event `gather_end` (id, kind; fresh ±0.01 do JSONL làm tròn); ngất → `{"items":[]}` | thành `stock` cá thể, giữ nguyên id và độ tươi (gồm cả phần sẽ giữ chỗ) |
| Chạm `--ticks` trước khi kết thúc | **không** tạo và không ghi đè file | — |
| Cách ghi | file tạm cùng thư mục → thay thế nguyên tử (`inventory.write_inventory`) | — |
| Thiếu file | — | thiếu cả `--inventory` lẫn `scenario.quan.stock` → kho rỗng; khai **cả hai** → mã 2 |

Đầu lượt quán độc lập: `money = earned = 0`, uy tín theo `reputation_initial` (trừ khi scenario khai).

## 2. Giao diện `sim/*` ↔ `client/ui`

UI (P1: `chonoi.live`) **chỉ đọc snapshot** và **chỉ gửi lệnh qua `InputState`**, không gọi thẳng vào luật. Mọi thứ hiển thị phải suy ra được từ snapshot.

**Lệnh UI gửi vào** (cùng format frame của `--inputs`, mục C)

| Trường | Kiểu | Phím gợi ý | Ý nghĩa |
|---|---|---|---|
| `move` | `[a, b]`, mỗi số ∈ [−1, 1], chuẩn hóa nếu dài > 1 | WASD / mũi tên | gather: `b > 0` = lặn xuống · quan: `b > 0` = về bắc |
| `interact` | bool, tác động ở **cạnh lên** | E | gather: cập bến / hái · quan: nấu / bưng / phục vụ |
| `catch` | bool, cạnh lên | Space | gather: bắt cá (quan: bỏ qua) |

**Trạng thái UI được đọc** (snapshot, mục E)

| Mode | Trường | HUD tối thiểu dùng |
|---|---|---|
| chung | `tick, sim_tick, mode, phase, phase_tick, state, time_left_ticks, money, earned, reputation, score` | thời gian, tiền, uy tín |
| gather | `player{pos, vel, heading_deg, oxygen_ticks, hp, zero_oxy_ticks, catch_cd_ticks, oxygen_max_ticks, hp_max, at_surface}`, `hold` (mảng cá thể `{id,kind,fresh}` theo thứ tự vào giỏ), `hold_count, hold_capacity, nodes[]{…, ready}, fish[]` | oxy, Máu, giỏ, độ tươi |
| quan | `player{pos, vel}, stock` (mảng cá thể theo id, **gồm cả hàng ươn**), `hand, stoves[]{id, pos, state, dish, cook_ticks_left, ready_ticks}, tables[]{id, pos, customer_id}, customers[]{…, order_status, reserved: [id…]}` (chỉ khách còn ngồi) | kho khả dụng, độ tươi, hàng đang giữ chỗ, món gọi, kiên nhẫn, trạng thái bếp, món trên tay |
| day / shop | `day, day_plan, upgrades, active_upgrades`; Shop có `stock` (kho lúc vào Shop, mảng cá thể) | Ngày, kế hoạch, cấp |

Điểm: `score = earned + reputation_multiplier × floor(reputation)`.

## 3. Danh sách sự kiện — mục E

Event được phát tại tick `k+1` của bước `k`, theo thứ tự xử lý, trước snapshot. Hiện người "nghe" chỉ có JSONL, test và UI (hiện thông báo); không module nào phụ thuộc event của module khác, chỉ phụ thuộc file kho.

**Gather** — phát bởi `chonoi/sim/gather.py` (Phong)

| name | data | Khi nào |
|---|---|---|
| `dive` / `surface` | `pos` (sau di chuyển) | đổi phía biên mặt nước (`d > 0.5` ↔ `d ≤ 0.5`) |
| `oxygen_empty` | `oxygen_ticks: 0` | oxy vừa từ dương xuống 0 |
| `choke` | `hp` (sau trừ) | `zero_oxy_ticks` đủ 60 |
| `faint` | `cause` (`choke`/`monster`), `lost` (mảng cá thể), `hp: 0` | Máu về 0; `lost` theo LIFO (vào giỏ sau bỏ trước) |
| `monster_hit` | `monster_id, hp, lost` (mảng cá thể, LIFO), `pos` | Cá Sấu chạm (v1.1) |
| `spoiled` | `item_id, kind, location: "hold"` | cá thể trong giỏ vừa qua ngưỡng ươn (một lần / cá thể, theo id) |
| `gather` | `node_id, kind, amount` | hái thành công |
| `node_regrown` | `node_id` | `regrow_ticks` 1 → 0 |
| `hold_full` | `action` (`gather`/`catch`), `node_id` hoặc `fish_id`, `required, free` | thiếu chỗ trong giỏ |
| `fish_caught` | `fish_id, kind, yield` | bắt được đàn |
| `gather_end` | `reason` (`time`/`docked`/`fainted`), `inventory` (= object mục 1) | kết thúc buổi sáng |

**Quán** — phát bởi `chonoi/sim/quan.py` (Khánh)

| name | data | Khi nào |
|---|---|---|
| `customer_arrived` | `order_id, table_id, dish_id` | khách mới ngồi + giữ chỗ |
| `no_dish` | `{}` | có bàn trống nhưng không món nào đủ nguyên liệu khả dụng |
| `spoiled` | `item_id, kind, location: "stock"` | cá thể trong kho vừa qua ngưỡng ươn; đơn đang giữ nó nhả và giữ lại một lần, không đủ → `order_status: unfulfillable` |
| `cook_started` | `stove_id, order_id, dish_id, items` (mảng cá thể, sắp theo kind rồi id), `base_price` = `floor(giá × fresh trung bình / 100)` | bếp idle nhận đơn reserved cũ nhất |
| `dish_ready` | `stove_id, order_id, dish_id` | nấu xong |
| `dish_picked` | `stove_id, order_id, dish_id` | bưng món lên tay trống |
| `served` | `order_id, table_id, dish_id, patience_ticks_left, base_price, tip` | giao đúng bàn |
| `paid` | `order_id, table_id, base_price, tip, amount, reason` (`finished_eating`/`closing`) | khách trả tiền |
| `customer_left` | `order_id, table_id, reason` (`patience`/`closing`), `reputation` | khách rời không ăn |
| `quan_end` | `reason: "time", money, earned, shift_earned, reputation` | hết ca, đã dọn xong |

Dòng cuối JSONL luôn là `{"type":"end", ticks, sim_tick, mode, state, reason, money, earned, reputation, score}` do `chonoi/runner.py` ghi (`reason` thêm `tick_limit` khi gameplay chưa xong).

## 4. Smoke tích hợp (phải xanh trước khi tag)

```bash
# dock.json (TICKET-03): {"gather":{"hold":[{"id":"I1","kind":"ca_linh","fresh":100}],"random_fish":false,"monsters":[]}}
# dock-inputs.json: {"frames":[{"tick":0,"interact":true}]}
python3 -m chonoi.headless --mode gather --seed 42 --scenario dock.json --inputs dock-inputs.json --ticks 1 --out gather.jsonl --inventory-out catch.json
python3 -m chonoi.headless --mode quan --seed 42 --inventory catch.json --ticks 0 --out quan.jsonl
# kỳ vọng: catch.json = {"items":[{"id":"I1","kind":"ca_linh","fresh":99.99166…}]} (hao 1 bước gather)
#          snapshot quán tick 0 có "stock":[{"id":"I1","kind":"ca_linh","fresh":99.992}]
```

Đã có sẵn trong `tests/test_smoke_p1.py` (`test_inv_01_*`), `tests/test_gather_fresh.py` (`test_fr09`) và `tools/proof_p3.py`.

## 5. Bench và soak (v1.3, TICKET-04)

| Lệnh (gốc `game.contract.json`) | Gọi | Đầu ra |
|---|---|---|
| `bench_cmd` = `python3 -m chonoi.bench` | `--seed <int> --duration <giây> --out bench.json` | `{avg_fps, p1_low_fps, frames, measured_s, load_ms}`; cảnh lặn chuẩn (độ tươi, cá bơi, Cá Sấu, hiệu ứng mặc định; Út Sen đứng yên ở bến), 1280×720, làm nóng 3 s |
| `soak_cmd` = `python3 -m chonoi.soak` | `--seed <int> --days <N> --out soak.json` | `{days, days_completed, crashes, results[]{day, earned, reputation, score}, duration_s}`; `results` lấy lúc Shop đóng; Ngày d dùng kế hoạch D((d−1) mod 5 + 1) |

Tham số sai → mã 2, không tạo file đầu ra. Soak không ghi JSONL, không ghi bảng xếp hạng. So tính lặp thì bỏ `duration_s`.

## Lịch sử thay đổi

| Ngày | Đổi gì | Lý do | Ai duyệt |
|---|---|---|---|
| 2026-11-21 | Bản đầu (P1) | kickoff | Khuê (Integrator) |
| 2026-11-21 | v1.2: file kho, `hold`, `stock`, `reserved`, `lost`, `cook_started.items` thành cá thể `{id,kind,fresh}`; thêm event `spoiled`, `tuning.freshness` | TICKET-03 (độ tươi); PR #22, #23, #25, #26, #27 | Khuê (Integrator); Phong, Khánh code theo |
| 2026-11-21 | v1.3: thêm `bench_cmd`, `soak_cmd` (mục 5); không đổi gameplay | TICKET-04 (phát hành v1.0.0); PR #29 | Khuê (Integrator); Phong code bench |

# Retro nhóm

## Phase 2 (nhanh)
- Điều tốt:
  - Có **nhánh nền** `mKhaiTruong/contract-v1.1` (PR #14 draft) ngay đầu phase. Cả nhóm tách nhánh từ đó, nên `main` luôn xanh dù contract v1.1 làm hỏng test cũ.
  - Checklist việc của từng người ghi thẳng trên PR #14, kèm hàm dùng chung (`plan_ingredients`, `check_reserved_within_stock`, `MonsterSet`).
  - Review có gộp thử trong worktree tạm + chạy toàn bộ test trước khi merge. Bắt được conflict `scenario.py` ở PR #15 và 3 điểm lệch PRD (thứ tự event tick 0, trường thừa trong snapshot, khách ngoài kế hoạch); Khánh sửa trong 1 commit.
- Điều tệ:
  - Khuê và Khánh **cùng viết** kiểm scenario `day`, vì Khánh tách nhánh trước khi commit scenario lên nhánh nền → mất thời gian và phải rebase.
  - Lát gather (cá bơi/sinh + nối Cá Sấu) là phần nặng nhất nhưng chỉ một người làm, thành điểm nghẽn cuối phase.
  - UI menu/HUD v1.1 chưa ai làm.
- 1 hành động cho Phase 3: **báo trong kênh nhóm trước khi bắt đầu một file dùng chung** (`scenario.py`, `runner.py`, `contract.py`) và push nhánh nền ngay sau mỗi commit, để không ai viết trùng. Người nhận: Khuê (Integrator).

## Phase 3 (nhanh)
- Rà hành động Phase 2 ("báo trước khi đụng file dùng chung, push nhánh nền ngay"): **đã làm**. Mọi hàm độ tươi dùng chung (`chonoi/fresh.py`: `decay`, `reserve_recipe`, `fresh_price`, `lifo_drop`, `ItemIds`…) có sẵn trên nhánh nền `3d24de2` trước khi Phong và Khánh tách nhánh, nên không ai viết trùng như ở P2.
- Điều tốt:
  - PR #22 (draft) ghi rõ **test nào đang fail chờ ai** (Phong 10, Khánh 2). Mỗi người biết xong khi nào: test của mình xanh.
  - Phong review PR quán của Khánh (`0f629f1`, "theo review của Phong"): bắt lỗi thứ tự bàn giao sau lần hao ở gather và id giỏ Ngày 2.
  - Review gộp thử **cả 3 PR cùng lúc** (#23, #25, #26) trong worktree tạm rồi chạy toàn bộ test (189 OK) trước khi merge. Một nghi ngờ (Ngày 2 với giỏ dạng chuỗi) được chạy thử và loại bỏ, không đoán.
- Điều tệ:
  - PR gather (#26) và PR quán/day (#23) phụ thuộc nhau, nên Khánh phải viết code tương thích tạm (`inspect.signature`, nhánh giỏ chuỗi). Sau đó cần thêm PR #27 để dọn.
  - PR docs #24 ghi "đã chốt" mà không đồng bộ với `verification/phase-1.md`, và có dòng trùng → mất một vòng review.
  - Quá hạn demo. Proof, verification, hợp đồng v1.2 làm sau cùng; `docs/contracts/README.md` còn mô tả kho đếm v1.0 tới lúc đóng phase.
  - HUD độ tươi chưa được chơi thử / chụp ảnh. ai-usage-log P3 trễ.
- 1 hành động cho Phase 4: **cập nhật hợp đồng (`docs/contracts/`) và CHANGELOG ngay trong PR nền, trước khi chia việc**, kèm thứ tự merge các PR phụ thuộc nhau. Mỗi PR có dòng ai-usage-log của người mở. Người nhận: Khuê (Integrator).

## Phase 4 (cuối)
- **Rà lại hành động Phase 2** ("báo trước khi đụng file dùng chung, push nhánh nền ngay sau mỗi commit", người nhận Khuê):
  - **P3: đã làm.** Mọi hàm dùng chung có trên nhánh nền `3d24de2` trước khi tách nhánh, nên không ai viết trùng.
  - **P4: đã làm.** Khi chia lại việc lúc Khánh rời, mỗi file chỉ có một chủ: Phong giữ `chonoi/web/index.html` (bench + cảnh báo), Khuê giữ `chonoi/soak.py` + docs.
  - **Còn vướng:** "báo" vẫn qua chat, không ghi lại. Ở P3, việc cùng sửa `day.py` vẫn phải thêm một PR dọn (#27).
- **Rà hành động Phase 3** ("cập nhật hợp đồng + CHANGELOG ngay trong PR nền, trước khi chia việc"): **làm một phần.** `game.contract.json` v1.3 nằm ở commit đầu của nhánh nền (`16a095c`) và PR #29 có bảng phân việc ngay từ đầu. Còn `docs/contracts/README.md` và `CHANGELOG.md` thì cập nhật sau khi đã chia việc, vì phải đóng Phase 3 trước.
- Điều tốt:
  - Quy trình nhánh nền → PR con → nền xanh → `main` → tag giữ `main` xanh suốt 4 phase. Mọi thay đổi vào `main` đều qua PR.
  - Review chéo có bắt được lỗi thật:
    - Phong review #23 của Khánh: id `I1` bị dùng lại ở Ngày 2, kỳ vọng `u` 24000 → 23998.
    - Khuê bắt lỗi M2 ở Ngày 3 khi chạy smoke `day` (P2).
    - Phong sửa câu sai trong log của Khánh.
  - Verification ghi trung thực "đạt một phần"; ảnh HUD P3 được bổ sung trước khi chuyển sang "đạt".
- Điều tệ:
  - Quá hạn demo P3, kéo theo P4 bắt đầu muộn. Khánh hết token giữa P4, nên một người phải nhận 2 phần việc.
  - UI menu / màn Ngày (nợ từ P2) chưa bao giờ được làm; `live.py` vẫn chưa có mode `day`.
  - Token / chi phí chưa ai đo (cột "chưa đo" ở mọi dòng ai-usage-log).
- **Số liệu:**
  - Commit không tính merge trên `main` + nhánh nền v1.3: Khánh 19, Phong 19, Khuê 18 (9 commit khung của giảng viên không tính).
  - Cách đọc code của nhau: gộp thử PR trong worktree tạm, chạy toàn bộ test, đối chiếu PRD / hợp đồng trước khi merge (`[prcheck]`).
  - Token theo người: chưa đo.
- **Một lần AI sai và cách nhóm xác minh:**
  - Khi review P3, AI (của Khuê) nghi `day.py` sẽ crash ở Ngày 2 nếu giỏ dựng sẵn là chuỗi kiểu cũ.
  - Nhóm không sửa theo nghi ngờ đó mà viết script chạy thử trong scratchpad. Kết quả: `parse_items` đã chặn từ Ngày 1 (mã 2), nên bỏ nghi ngờ.
  - Ngược lại, bản nháp ai-usage-log của Khánh do AI viết đã ghi sai nội dung review của Phong. Phong đối chiếu với commit `0f629f1` / `23ce143` và sửa ở `ac96bd6`.
- **Nếu làm lại, đổi gì:**
  - Đóng phase (proof, verification, hợp đồng) ngay khi PR code cuối merge, không để tới sau hạn.
  - Mỗi người ghi ai-usage-log ngay trong PR của mình.
  - Có một người dự phòng cho mỗi module, để khi có người rời (hết token) thì việc không dồn vào một chỗ.
- **Hành động tiếp theo** (sau v1.0.0): làm UI vòng Ngày (`live.py --mode day` + màn Shop) và đo token theo người. Người nhận: Phong (UI), Khuê (đo).

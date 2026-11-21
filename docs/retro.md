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
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:

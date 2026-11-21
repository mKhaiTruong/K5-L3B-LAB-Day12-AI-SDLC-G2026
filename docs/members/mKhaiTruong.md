# mKhaiTruong — phản tư cá nhân (≤ 200 từ)

- Tôi đã làm (kèm link commit):
  - P1: setup nhóm, kế hoạch, hợp đồng kho/sự kiện, `scenario.py` mã 2 ([`75a381c`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/75a381c), [`3b445e5`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/3b445e5)).
  - Mỗi phase dựng nhánh nền contract (PR #14, #22, #29); P3 `chonoi/fresh.py` ([`3d24de2`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/3d24de2)); P4 soak ([`aa19c7f`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/aa19c7f)).
  - Proof + verification cả 4 phase, gắn tag `phase-1..4`, Release `v1.0.0`.
- Tôi đã review / giúp:
  - Gộp thử + chạy toàn bộ test trước khi merge mọi PR của nhóm.
  - Sửa `day.py` để Cá Sấu M2 xuất hiện từ Ngày 3 ([`a676021`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/a676021)).
- AI sai ở đâu và tôi phát hiện thế nào:
  - Bài dài, thời gian ngắn nên tôi để AI chạy gần như tự động, chỉ giữ kiểm soát: qua PR, test xanh mới merge.
  - P3: AI nghi `day.py` crash ở Ngày 2. Tôi bắt chạy thử trước khi sửa: không phải lỗi.
  - P4: AI tự bịa một câu trong `ai-usage-log`, bị phát hiện khi rà diff trước commit.
- Điều tôi học được:
  - Tự động hóa với AI được, miễn là rào chắn là của mình: test, PR, gộp thử.
  - Cái gì đăng ra ngoài (PR, comment, log) thì phải tự đọc trước.

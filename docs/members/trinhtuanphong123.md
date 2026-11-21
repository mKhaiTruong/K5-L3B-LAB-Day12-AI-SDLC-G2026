# trinhtuanphong123 — phản tư cá nhân (≤ 200 từ)

- Tôi đã làm (kèm link commit):
  - P1 `gather`: lát 1 oxy, ngạt, ngất [`eb4885d`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/eb4885d) (PR #4); lát 2 hái, bắt cá [`a9f2305`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/a9f2305) (PR #7); README [`045a046`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/045a046); proof phase-1.
  - P2: cá bơi, sinh theo seed/lịch, nối Cá Sấu [`252d8e3`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/252d8e3) (PR #19); proof phase-2 [`a589c62`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/a589c62) (PR #21).
  - P3: giỏ cá thể, hao tươi, `spoiled`, id I* [`4a0239e`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/4a0239e), [`689e499`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/689e499) (PR #26).
- Tôi đã review (kèm link):
  - PR [#8](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/pull/8) (Khuê) và [#23](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/pull/23) (Khánh): gộp thử, chạy toàn bộ test. Ở #23 tìm ra Ngày 2 dùng lại id `I1`, test kỳ vọng `u` sai (24000 → 23998).
  - PR [#25](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/pull/25) (HUD): đối chiếu schema snapshot.
- AI sai ở đâu và tôi phát hiện thế nào:
  - Spec sai số dòng, sót docstring: phát hiện khi đọc diff.
  - HUD hiện `[object Object]`: phát hiện khi chơi thử.
  - Test so `fresh` tuyệt đối, hỏng vì JSONL làm tròn 3 chữ số: phát hiện khi ghép nhánh, đổi sang dung sai ±0.01 theo PRD.
- Điều tôi học được:
  - Spec có số tham chiếu đã chạy thử giúp model nhỏ code đúng ngay.
  - Test xanh chưa đủ: phải ghép thử nhánh người khác, chơi thật, kiểm tất định.

# trinhtuanphong123 — phản tư cá nhân (≤ 200 từ)

- Tôi đã làm (kèm link commit):
  - `gather`: oxy, ngạt, ngất [`eb4885d`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/eb4885d) (PR #4); hái, bắt cá [`a9f2305`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/a9f2305) (PR #7); cá bơi, Cá Sấu [`252d8e3`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/252d8e3) (PR #19); giỏ cá thể, độ tươi [`4a0239e`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/4a0239e) (PR #26).
  - P4: `bench_cmd` đo render thật, 3 cảnh báo, tương phản cao [`5e5ca16`](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/commit/5e5ca16) (PR #30).
  - README; proof phase-1, phase-2; ảnh chơi thử HUD P3, P4.
- Đã review / giúp ai:
  - PR [#8](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/pull/8) (Khuê), [#23](https://github.com/mKhaiTruong/K5-L3B-LAB-Day12-AI-SDLC-G2026/pull/23) (Khánh): gộp thử, chạy toàn bộ test; ở #23 tìm ra Ngày 2 dùng lại id `I1`, kỳ vọng `u` sai.
  - Sửa giúp dòng ai-usage-log của Khánh khi Khánh hết token.
- AI sai ở đâu và tôi phát hiện thế nào:
  - Test so `fresh` tuyệt đối, hỏng vì JSONL làm tròn: phát hiện khi ghép nhánh.
  - AI tưởng `--window-size` cho viewport 1280×720; lần đo đầu báo 1258×622, phải cố định canvas.
- Điều tôi học được:
  - Spec có số tham chiếu chạy thử giúp model nhỏ code đúng ngay.
  - Test xanh chưa đủ: phải ghép nhánh, chơi thật và xem lại từng bằng chứng.

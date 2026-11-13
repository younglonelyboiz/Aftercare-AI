# Biên bản Thẩm định Lâm sàng và Ký duyệt Bộ Quy tắc An toàn (W07 Clinical Review Signoff)

## 1. Thông tin Phiên bản Thẩm định
- **Mã hạng mục**: `W07-T6.6` (Thẩm định chuyên môn các mẫu phản hồi tiếng Việt và bộ quy tắc kiểm soát chính sách)
- **Phiên bản bộ quy tắc**: `v1.0.0`
- **Ngày hoàn tất thẩm định**: `2026-11-13`
- **Tài liệu chuẩn tham chiếu**:
  1. Quyết định số `1851/QĐ-BYT` ngày `24/04/2020` của Bộ Y tế về việc ban hành tài liệu chuyên môn "Hướng dẫn chẩn đoán và điều trị Hen phế quản người lớn và trẻ em trên 12 tuổi".
  2. Hướng dẫn Toàn cầu về Quản lý và Dự phòng Hen phế quản (`GINA 2024` — Global Initiative for Asthma).

---

## 2. Danh mục Tệp Cấu hình và Mẫu Phản hồi được Ký duyệt

| Số thứ tự | Đường dẫn tệp | Phiên bản | Nội dung thẩm định chuyên môn | Trạng thái |
|---|---|---|---|---|
| 1 | `backend/app/guardrails/templates_vi.py` | `v1.0.0` | Mẫu hướng dẫn xử trí cấp cứu Vùng Đỏ (`RED_ZONE`), mẫu kế hoạch hành động Vùng Vàng (`YELLOW_ZONE`), mẫu từ chối an toàn (`SAFE_REFUSAL`), mẫu không đủ bằng chứng (`NO_EVIDENCE_MESSAGE`) và mẫu dự phòng hệ thống (`SAFE_FALLBACK_MESSAGE`). | Đã phê duyệt |
| 2 | `backend/app/guardrails/policies/input_policies.yaml` | `v1.0.0` | Bộ 7 quy tắc kiểm soát chính sách đầu vào (`POL-SELFHARM`, `POL-INJECT`, `POL-MED-STOP`, `POL-MED-DOSE`, `POL-RX-NEW`, `POL-DIAG`, `POL-OOS`) có hỗ trợ cả tiếng Việt có dấu, không dấu và từ ngữ thông dụng của người bệnh. | Đã phê duyệt |
| 3 | `backend/app/guardrails/policies/output_policies.yaml` | `v1.0.0` | Bộ 9 quy tắc kiểm soát an toàn đầu ra (`OUT-LEAK`, `OUT-RESCREEN`, `OUT-FALSE-REASSURE`, `OUT-STOP-MED`, `OUT-DIAG`, `OUT-DOSE-LEAK`, `OUT-MED-ALLOW`, `OUT-CITE`, `OUT-DISCLAIMER`) cùng danh mục 76 hoạt chất và biệt dược kiểm soát. | Đã phê duyệt |

---

## 3. Các Nguyên tắc Y khoa Bắt buộc đã được Kiểm chứng

1. **Nguyên tắc Cấp cứu Vùng Đỏ (`RED_ZONE`)**:
   - Khi người bệnh có dấu hiệu khó thở dữ dội, chỉ nói được từng từ, tím môi, rút lõm lồng ngực, SpO2 dưới 90%, PEF dưới 60% hoặc xịt thuốc cắt cơn không giảm: hệ thống hướng dẫn sử dụng ngay thuốc cắt cơn tác dụng nhanh theo Kế hoạch hành động hen cá nhân hóa, giữ tư thế ngồi thẳng hơi cúi về phía trước (tuyệt đối không nằm ngửa), gọi ngay Cấp cứu `115` và kích hoạt cảnh báo `P0_CRITICAL` tới điều dưỡng phụ trách.
2. **Nguyên tắc Cơn hen Trở nặng Vùng Vàng (`YELLOW_ZONE`)**:
   - Khi người bệnh thức giấc ban đêm do ho hoặc khò khè, nặng ngực, hạn chế vận động, PEF từ 60% đến 80%: hệ thống hướng dẫn dùng thuốc cắt cơn theo chỉ dẫn Vùng Vàng, nghỉ ngơi tại chỗ, đánh giá lại sau `20 phút` và kích hoạt cảnh báo `P1_HIGH`.
3. **Nguyên tắc Tuân thủ Thuốc Kiểm soát (`POL-MED-STOP` và `OUT-STOP-MED`)**:
   - Nghiêm cấm tự ý ngưng thuốc kiểm soát chứa Corticosteroid dạng hít (`Symbicort`, `Seretide`, `Pulmicort`) hoặc thuốc kháng viêm đường uống (`Prednisolone`, `Methylprednisolone`) khi thấy hết triệu chứng, theo đúng Mục `2.7.2` của Quyết định `1851/QĐ-BYT`. Mọi ý định tự ý bỏ thuốc đều được cảnh báo mức `P2_MEDIUM` để điều dưỡng can thiệp tư vấn.
4. **Nguyên tắc Không Kê đơn và Không Chẩn đoán Thay Bác sĩ (`POL-MED-DOSE`, `POL-RX-NEW`, `POL-DIAG`, `OUT-DOSE-LEAK`)**:
   - Trợ lý tuyệt đối không đưa ra hàm lượng miligam hoặc số nhát xịt chưa có trong hồ sơ bệnh án hoặc đoạn tài liệu Bộ Y tế vừa truy xuất, không khuyên mua kháng sinh hay thuốc đông y ngoài đơn xuất viện.


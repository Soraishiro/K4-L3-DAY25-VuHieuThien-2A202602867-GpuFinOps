# Bài viết ngắn - Lab 25: GPU FinOps Cost Optimization

**Học sinh:** Vũ Hiếu Thiên - MSSV: 2A202602867

---

## 1. Baseline vs. Optimized

**Chi phí trước tối ưu (Baseline):** $18,005/tháng
**Chi phí sau tối ưu (Optimized):** $10,331/tháng
**Tỷ lệ tiết kiệm:** 43% ($7,674/năm)

Đơn vị $/1M-token:
- **Trước tối ưu:** $6.488/1M-token
- **Sau tối ưu:** $1.126/1M-token

So với cách tính truyền thống dựa trên $/GPU-giờ, việc sử dụng $/1M-token giúp chúng ta nhìn thấy rõ hơn hiệu quả thực sự của việc tối ưu. Nếu chỉ nhìn vào $/GPU-giờ, chúng ta có thể nghĩ rằng việc thuê GPU là đắt đỏ, nhưng với $/1M-token, chúng ta thấy rằng việc áp dụng cascade routing, prompt caching và batch API có thể giảm chi phí xử lý token xuống còn 1/6 so với phương pháp truyền thống.

---

## 2. Phân tích từng đòn bẩy

Dưới đây là bảng phân tích chi tiết từng đòn bẩy tiết kiệm chi phí:

| Đòn bẩy | Số tiền tiết kiệm (USD/tháng) | Phần trăm |
|--------|-----------------------------|-----------|
| Inference (cascade/cache/batch) | $1,212 | ~7% tổng |
| Purchasing (spot/reserved) | $4,638 | ~26% tổng |
| Right-size util-lies | $1,224 | ~7% tổng |
| Kill idle GPUs | $600 | ~3% tổng |

**Đòn bẩy có đóng góp lớn nhất: Purchasing (spot/reserved)** với số tiền tiết kiệm lên đến $4,638/tháng (chiếm ~26% tổng tiết kiệm). Đây là lĩnh vực có tiềm năng tiết kiệm lớn nhất vì:

1. **Spot instances:** 5/8 jobs được đề xuất sử dụng spot instances, giảm chi phí từ $2.50 xuống còn $1.50/GPU-giờ cho H100 (giảm 40%).
2. **Reserved instances:** 3/8 jobs không thể dùng spot (non-interruptible) được đề xuất reserved 1-year, giảm chi phí trung bình 20% so với on-demand.

Đòn bẩy thứ hai mạnh mẽ nhất là **Right-size util-lies** ($1,224/tháng). Hai GPU bị "lie" (gpu-h100-4 và gpu-a10g-1) đang được trả tiền mỗi giờ nhưng chỉ thực hiện ~20-27% công việc thực tế. Việc hạ cấp H100 xuống A10G và A10G xuống L4 giúp tiết kiệm đáng kể.

---

## 3. GPU-Util Lie

**Hai GPU bị "lie":**
1. **gpu-h100-4:** GPU-Util đạt 98.2%, nhưng MFU chỉ 0.194 (19.4%)
2. **gpu-a10g-1:** GPU-Util đạt 96.9%, nhưng MFU chỉ 0.268 (26.8%)

**Tác động tài chính:**
- gpu-h100-4: Được trả $2.50/GPU-giờ nhưng chỉ thực hiện 20% công việc → lãng phí $2.00 mỗi giờ
- gpu-a10g-1: Được trả $1.00/GPU-giờ nhưng chỉ thực hiện 27% công việc → lãng phí $0.73 mỗi giờ

GPU "bận" (GPU-Util cao) nhưng không làm việc hiệu quả (MFU thấp) một bằng chứng của việc GPU đang chờ đợi I/O, băng thông bộ nhớ hoặc có vấn đề trong pipeline. Tương tác này nghĩa là chúng ta đang trả tiền cho toàn bộ giờ GPU nhưng chỉ nhận được phần nhỏ công việc thực tế.

---

## 4. Phần mở rộng đã thực hiện

### Extension 1: Cải thiện `recommend_tier()` trong `finops/pricing.py`

**Những thay đổi:**
- Thêm tham số `gpu_type` để cân nhắc interruption rate khác nhau theo loại GPU
- Thêm tham số `job_days` để chọn giữa 1-year và 3-year reserved tương ứng với thời gian job
- Logic nâng cao: Chỉ đề xuất reserved khi job_days >= 7 ngày

**Kết quả đo được:**
- Trước tối ưu: monthly on-demand $16,539 → optimized $13,197 (20.2% saved)
- Logic này đưa ra quyết định mua GPU dựa trên thời gian dài và loại GPU, thay vì chỉ dựa vào duty cycle đơn thuần

**Insight quan trọng:** Việc cân nhắc thời gian job tránh được việc cam kết reserved không cần thiết cho các job ngắn hạn, trong khi vẫn giữ được khuyến cáo spot cho các job có thể gián đoạn.

### Extension 2: Right-sizing dựa trên MBU trong `missions/m1_efficiency_audit.py`

**Những thay đổers:**
- Thêm logic đề xuất GPU thay thế cho workload memory-bound dựa trên MBU
- Tính toán $/GB-VRAM cho từng loại GPU
- Đề xuất GPU rẻ hơn với MBU target tương đương

**Kết quả đo được:**
- Mở rộng bảng M1 để bao gồm bảng đề xuất right-sizing:
  - gpu-h100-4: H100 → MI300X (MBU=0.21), tiết kiệm $396/tháng
  - gpu-h100-5: H100 → MI300X (MBU=0.27), tiết kiệm $396/tháng
  - Nhiều GPU khác cũng được đề xuất

**Insight quan trọng:** Đối với các workload bị memory-bound (MBU thấp), việc chọn GPU dựa trên $/GB-VRAM và bandwidth thay vì chỉ dựa trên giá thành có thể dẫn đến lựa chọn GPU tối ưu hơn.

---

## 5. Khuyến nghị cho NimbusAI (FinOps Lead)

**3 hành động đầu tiên:**

1. **Triển khai ngay spot + checkpoint cho các job interruptible:** 5/8 jobs đều là interruptible và có thể chuyển sang spot instances ngay. Với chiết khấu 40% so với on-demand và checkpoint overhead chỉ ~3%, tiết kiệm ngay 30-40% cho các team training. Cần triển khai checkpoint pipeline trước.

2. **Ngừng ngay các GPU bị "idle" và "lie":** gpu-h100-5 đang idling 8 giờ/ngày (sáng sớm) → tắt ho hoặc downscale nguay. Hai GPU bị "tell" (gpu-h100-4, gpu-a10g-1) cần được hạ cấp hoặc workload được tối ưu để tăng MFU. Tiết kiệm tiềm tại: $600/tháng (idle) + $1,224/tháng (right-size).

3. **Áp dụng cascade + caching cho inference:** 82.6% tiết kiệm từ $/1M-token này là cơ hội lớn nhất chưa khai thác. Cần đưy 80% traffic qua model nhỏ, bật prompt caching cho system prompt chung, và batch API cho các request không realtime. Mục tiêu: giảm $/1M-token từ $6.49 xuống dưới $1.50 trong 30 ngày tới.

**Bonus:** Nên triển khai tag coverage monitoring và FOCUS export để đảm bảo chargeback chính xác trước khi áp dụng chính sách chi phí cho các team.

# Bài thu hoạch — Lab 25: GPU FinOps

## 1. Phạm vi và kết quả

Bài lab sử dụng dữ liệu mô phỏng để phân tích chi phí GPU và xử lý yêu cầu bằng mô hình ngôn ngữ. Kết quả sau khi sửa được tổng hợp trong `outputs/report.md`. Mức chi phí giả định ban đầu là **18.005 USD**, chi phí sau các phương án là **10.756 USD**, tương ứng cơ hội tiết kiệm **7.249 USD (40,3%)** trong kỳ mô phỏng. Đây là **kịch bản kết hợp có điều kiện**, không phải số tiền doanh nghiệp đã tiết kiệm.

Cần đặc biệt lưu ý: dữ liệu chi phí theo token, chi phí thuê GPU theo công việc và dữ liệu theo dõi từng GPU chưa có định danh hóa đơn chung. Vì vậy chưa chứng minh được ba phạm vi này độc lập để cộng toàn bộ thành mức tiết kiệm thực tế. Riêng bài toán lựa chọn cách thuê GPU (M3), chi phí giả định giảm từ khoảng **16.539 USD xuống 11.906 USD**, tương đương **28%**, với giả định một số công việc đã có sẵn quyền sử dụng tài nguyên theo hợp đồng cam kết.

Khi đo riêng hoạt động suy luận (M2), chi phí giảm từ **6,488 USD** xuống **1,126 USD trên một triệu token**, tương đương **82,6%**. Đây là tác động kết hợp của định tuyến yêu cầu, sử dụng bộ nhớ đệm và xử lý theo lô; bài chưa tách được hiệu quả riêng của từng biện pháp và chưa kiểm chứng chất lượng đầu ra.

## 2. Những phát hiện quan trọng

Mức sử dụng GPU cao không phản ánh trực tiếp hiệu quả tính toán. `gpu-h100-4` có GPU-Util khoảng 98,2% nhưng MFU chỉ 19,4%; `gpu-a10g-1` có GPU-Util khoảng 96,9% nhưng MFU chỉ 26,8%. Chỉ số này giúp xác định những thiết bị cần điều tra nguyên nhân, nhưng **không đủ để kết luận có thể thu hồi ngay 80% chi phí**. Cần phân tích độ trễ, thời gian chờ bộ nhớ, truyền dữ liệu và cấu hình xử lý. Ngoài ra, `gpu-h100-5` có tám giờ sử dụng rất thấp mỗi ngày, tương ứng cơ hội loại bỏ khoảng **600 USD/tháng** theo giá mô phỏng, nếu có thể dừng thiết bị mà không ảnh hưởng công việc.

Trong kịch bản tổng hợp có điều kiện, bốn khoản được mô hình hóa gồm: tối ưu suy luận **1.212 USD**, lựa chọn hình thức thuê **4.633 USD**, thay GPU sau bước sàng lọc **804 USD**, và loại bỏ giờ nhàn rỗi **600 USD**. Các khoản này chỉ được cộng khi có thể đối chiếu hóa đơn và chứng minh không trùng nguồn chi phí.

## 3. Hai phần mở rộng

**Phần mở rộng thứ nhất — chính sách thuê GPU.** Hàm `recommend_tier()` đã bổ sung loại GPU, số ngày chạy và rủi ro gián đoạn giả định theo GPU. Khi xét Spot, công thức tính cả chi phí lưu trạng thái và chạy lại công việc. Khi xét Reserved, công việc dưới một năm chỉ được áp đơn giá có cam kết nếu **đã có sẵn phần tài nguyên cam kết chưa dùng**. Nếu phải mua hợp đồng mới, cần xét chi phí của toàn bộ thời hạn 1–3 năm, không lấy mức giá giờ rẻ hơn rồi nhân với số ngày của một công việc ngắn. Dữ liệu bài lab chưa cho biết các hợp đồng hiện hữu, nên kết quả giảm 28% vẫn phụ thuộc giả định này.

**Phần mở rộng thứ hai — lựa chọn GPU phù hợp.** M1 sử dụng MBU cùng số liệu về bộ nhớ sử dụng, lượng phép tính và băng thông thực tế để lập danh sách GPU thay thế. Ứng viên phải có bộ nhớ đủ chứa công việc, thông lượng và băng thông tối thiểu cao hơn nhu cầu quan sát được 10%, đồng thời có giá thuê thấp hơn. Chỉ tính tiền tiết kiệm trên giờ hoạt động để không tính trùng với giờ nhàn rỗi. Đây vẫn chỉ là bước sàng lọc: nếu thay H100 bằng MI300X còn phải đánh giá khả năng tương thích phần mềm CUDA/ROCm, chất lượng đầu ra và thời gian hoàn thành. MBU thấp tự nó **không chứng minh** một công việc bị giới hạn bởi băng thông.

## 4. Phân bổ chi phí và tính bền vững

M4 phân bổ chi phí theo nhóm và dự án, với tỷ lệ bản ghi có đủ nhãn khoảng **91,8%**. Tệp `outputs/focus_export.csv` chứa đầy đủ 2.400 bản ghi mô phỏng, có mã tài nguyên riêng cho từng yêu cầu và một số trường theo cách trình bày FOCUS. Tuy nhiên, tệp này **chưa phải dữ liệu tuân thủ đầy đủ FOCUS 1.2** vì không có dữ liệu hóa đơn, điều khoản hợp đồng và các trường bắt buộc khác do nhà cung cấp xác nhận.

Các phép tính điện năng và carbon được xây dựng từ hệ số giả định. Trong bảng dữ liệu, `europe-north1` có cường độ phát thải thấp nhất, còn `us-east-wa` có giá điện thấp nhất. Không thể xác định vùng triển khai tốt nhất chỉ từ một trong hai chỉ số này mà bỏ qua chi phí GPU, độ trễ và khả năng cung cấp tài nguyên.

## 5. Khuyến nghị và bài học

Nếu phụ trách FinOps của NimbusAI, tôi sẽ ưu tiên kiểm tra hóa đơn và định danh tài nguyên để xác lập chi phí ban đầu đáng tin cậy; xử lý các giờ GPU nhàn rỗi có thể dừng an toàn; sau đó thử nghiệm Spot cho các công việc chấp nhận gián đoạn và đánh giá thực tế các GPU đề xuất thay thế. Chỉ mua cam kết dài hạn khi có dự báo khối lượng công việc ổn định trong toàn bộ thời hạn; chỉ chuyển yêu cầu sang mô hình nhỏ hơn nếu chất lượng vẫn đáp ứng mục tiêu.

Bài lab giúp tôi hiểu rằng **FinOps là tối ưu chi phí cho một kết quả hữu ích, chứ không chỉ giảm giá thuê GPU hoặc giảm tổng tiền trên giấy**. Để đưa ra quyết định thực tế, cần kiểm soát chất lượng dữ liệu, phạm vi hạch toán, rủi ro, thông lượng, độ trễ và chất lượng đầu ra, đồng thời công khai những giả định chưa được kiểm chứng.

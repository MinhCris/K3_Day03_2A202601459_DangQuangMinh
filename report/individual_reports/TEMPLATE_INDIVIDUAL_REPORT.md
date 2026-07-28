# Báo cáo cá nhân: Lab 3 - Chatbot vs ReAct Agent

- **Tên sinh viên**: Dang Quang Minh
- **Mã sinh viên**: 2A202601459
- **Ngày**: 2026-07-28

---

## I. Đóng góp kỹ thuật (15 điểm)

- **Các mô-đun đã triển khai**:
  - `src/agent/agent.py`: xây dựng vòng lặp ReAct, trích xuất `Action`/`Final Answer`, parsing đối số an toàn, dispatch callable, guardrail cho hành động lặp lại và hệ thống telemetry.
  - `src/tools/ecommerce.py`: triển khai các tool thương mại với kiểm tra tồn kho, mã giảm giá, phí vận chuyển và tính tổng đơn hàng rõ ràng.
  - `src/chatbot.py`: tạo baseline Chatbot một lần gọi để so sánh công bằng với ReAct agent.
  - `src/core/provider_factory.py` và `src/main.py`: cấu hình provider linh hoạt và giao diện dòng lệnh cho cả OpenAI/Gemini/Local.
  - `scripts/analyze_logs.py` và `tests/`: phân tích số liệu telemetry và chạy 10 bài kiểm tra offline.

- **Điểm nhấn code**: các đối số tool được giải mã bằng `json.loads` và `ast.literal_eval`, không dùng `eval`; tool chỉ được gọi khi handler đã đăng ký trong danh sách. Kết quả tool được chuyển thành `Observation` và gửi lại cho LLM trong bước tiếp theo.

- **Tài liệu**: README hướng dẫn cài đặt, chuyển đổi provider, lệnh CLI, chạy test, phân tích telemetry và định nghĩa tool. Báo cáo nhóm ghi nhận thay đổi thiết kế từ v1 sang v2 và một trace lỗi cụ thể.

## II. Case study gỡ lỗi (10 điểm)

- **Mô tả sự cố**: model trả về `Action: check_stock {item_name: iPhone 15}` thay vì định dạng gọi hàm đúng và JSON hợp lệ.
- **Nguồn log**: khi chạy `tests/test_agent.py`, có sự kiện `AGENT_PARSE_ERROR` trong file log `logs/YYYY-MM-DD.log`; sự kiện ghi lại phản hồi lỗi và bước thực hiện.
- **Chẩn đoán**: lỗi thuộc về sự không khớp giữa parser và hợp đồng định dạng tool, không phải lỗi dữ liệu kho. Mô hình nhận prompt thiếu cấu trúc đủ mạnh để cung cấp đối số đúng định dạng.
- **Giải pháp**: cập nhật prompt hệ thống v2 và phần mô tả tool để luôn cho ví dụ JSON. Agent giờ nhận diện được action không hợp lệ, trả về observation `PARSER_ERROR` và cho phép phiên tiếp theo sửa lại action hoặc trả lời trực tiếp. Trace lỗi hiện được ghi lại rõ ràng thay vì bị ẩn.

## III. Nhận xét cá nhân: Chatbot vs ReAct (10 điểm)

1. **Reasoning**: `Thought` thể hiện ý định trung gian, nhưng giá trị thực sự nằm ở việc quyết định sử dụng tool nào. Sự khác biệt quan trọng là agent dùng các bước rõ ràng để lấy dữ liệu tồn kho, mã giảm giá, trọng lượng, phí vận chuyển rồi mới tính tổng.
2. **Độ tin cậy**: agent có thể kém hơn chatbot khi câu hỏi đơn giản không cần tool, vì agent tăng thêm độ trễ, chi phí token và rủi ro parse. Chatbot một lần gọi tốt hơn với yêu cầu không cần dữ liệu ngoài.
3. **Quan sát**: observation cung cấp phản hồi thực tế cho bước tiếp theo. Ví dụ, agent nhận `unit_price_vnd` và `unit_weight_kg` chính xác từ `check_stock` thay vì tự đoán. Khi lỗi xảy ra, observation giúp agent sửa lại an toàn.

## IV. Cải tiến trong tương lai (5 điểm)

- **Khả năng mở rộng**: dùng gọi tool bất đồng bộ và hàng đợi cho dịch vụ chậm.
- **An toàn**: thêm kiểm tra phân quyền người dùng, validate đầu vào, giới hạn tỷ lệ, timeout và policy audit trước các tool thay đổi trạng thái.
- **Hiệu năng**: chỉ truy xuất tool liên quan trong kho tool lớn và cache kết quả ổn định.
- **Chất lượng**: đánh giá nhà cung cấp thực tế bằng bộ test versioned, lưu trace vào cơ sở dữ liệu và dùng thống kê lỗi để cải thiện mô tả tool và prompt liên tục.


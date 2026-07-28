# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: DatMinhQuyen
- **Team Members**: La The Quyen, Dang Quang Minh, Nguyen Duc Dat
- **Deployment Date**: 2026-07-28

---

## 1. Executive Summary

Chúng tôi xây dựng một hệ thống agent ReAct chuyên xử lý các truy vấn thương mại điện tử nhiều bước, so sánh với baseline chatbot một lần gọi. Agent sử dụng các tool nội bộ để kiểm tra tồn kho, mã giảm giá, phí vận chuyển và tính tổng đơn hàng.

- **Success Rate**: Agent đạt hiệu quả cao hơn trong các câu hỏi nhiều bước có công việc tính toán và kiểm tra dữ liệu so với chatbot. Chatbot baseline phù hợp với các câu hỏi đơn giản, nhưng agent mạnh hơn khi cần nhiều hành động liên tiếp.
- **Key Outcome**: Agent xử lý tốt các truy vấn multi-step nhờ kết hợp Thought-Action-Observation và tool inventory, giảm rủi ro tự suy luận sai giá trị đơn hàng.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

Hệ thống agent của dự án triển khai vòng lặp ReAct trong `src/agent/agent.py`:

1. Người dùng gửi truy vấn qua CLI trong `src/main.py`.
2. `create_provider()` chọn provider LLM (Gemini, OpenAI, Local).
3. `ReActAgent.run()` xây dựng prompt và gọi `llm.generate()` với `system_prompt` mô tả các tool.
4. Nếu LLM trả về `Final Answer`, agent kết thúc.
5. Nếu LLM trả về `Action: tool_name(...)`, agent parse action rồi gọi tool.
6. Kết quả tool được chuyển thành `Observation` và nối vào prompt.
7. Vòng lặp tiếp tục đến khi trả về câu trả lời cuối hoặc vượt quá `max_steps`.


#### Workflow diagram

```text
User Query
   ↓
src/main.py
---> create_provider(provider, model)
   ↓
ReActAgent(provider, tools).run(query)
   ↓
system prompt + user query → LLM.generate()
   ↓
┌───────────────┐        ┌────────────────────┐
│ Final Answer? │──Yes──▶│ Return result      │
└──────┬────────┘        └────────────────────┘
       │No
       ↓
Parse Action
       ↓
Execute Tool (check_stock / get_discount / calc_shipping / calculate_order_total)
       ↓
Observation
       ↓
Append observation to prompt
       ↺ Back to LLM.generate()
``` 

### 2.2 Tool Definitions (Inventory)

| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `check_stock` | `{"item_name": "iPhone 15"}` | Kiểm tra tồn kho, giá và trọng lượng sản phẩm trong catalog. |
| `get_discount` | `{"coupon_code": "WINNER"}` | Kiểm tra mã giảm giá và phần trăm chiết khấu. |
| `calc_shipping` | `{"weight_kg": 0.342, "destination": "Hanoi"}` | Tính phí vận chuyển nội địa theo cân nặng và thành phố. |
| `calculate_order_total` | `{"unit_price_vnd": 22990000, "quantity": 2, "discount_percent": 10, "shipping_fee_vnd": 30000}` | Tính subtotal, chiết khấu và tổng thanh toán rõ ràng. |

### 2.3 LLM Providers Used
- **Primary**: Gemini (`gemini-2.5-flash`) — provider mặc định trong dự án.
- **Secondary (Backup)**: OpenAI (`gpt-4o`) — có thể bật lại bằng cấu hình CLI.
- **Local**: `LocalProvider` dùng model GGUF khi có `LOCAL_MODEL_PATH` và môi trường offline.

---

## 3. Telemetry & Performance Dashboard

Hệ thống ghi telemetry qua `src/telemetry/logger.py` và `src/telemetry/metrics.py`:

- Ghi event `AGENT_START`, `AGENT_RESPONSE`, `AGENT_TOOL_CALL`, `AGENT_PARSE_ERROR`, `AGENT_END`.
- Theo dõi `provider`, `model`, `usage`, `latency_ms` cho mỗi request.
- Vì repo hiện chưa có báo cáo số thực, chúng tôi tổng hợp các chỉ số key như sau:
  - **Average Latency (P50)**: Thu thập từ `latency_ms` trả về từ provider.
  - **Max Latency (P99)**: Có thể xác định từ traced values nếu chạy benchmark.
  - **Average Tokens per Task**: tiêu thụ token được lưu trong `usage` trả về từ LLM.
  - **Total Cost of Test Suite**: phụ thuộc provider; với Gemini local và tool nội bộ, chi phí thấp.

### Performance notes
- Agent có cơ chế spinner trong CLI (`src/agent/agent.py`) để giảm log tường thuật và cải thiện UX.
- Telemetry tập trung vào độ trễ và usage, phù hợp để giám sát chi phí khi chuyển lên production.

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### Case Study: Parser action lỗi định dạng
- **Input**: Ví dụ model trả về `Action: check_stock {item_name: iPhone 15}`.
- **Observation**: Khoảng cách giữa định dạng LLM và tool contract khiến agent không thể parse action.
- **Root Cause**: Prompt hệ thống ban đầu thiếu ví dụ JSON rõ ràng, nên model có thể đưa ra action không theo cú pháp yêu cầu.
- **Giải pháp**: Cập nhật prompt hệ thống trong `ReActAgent.get_system_prompt()` để luôn yêu cầu định dạng:
  - `Thought: ...`
  - `Action: tool_name(<JSON object or JSON array of arguments>)`
- **Kết quả**: Agent bắt lỗi `PARSER_ERROR`, tạo observation sửa lỗi và cho phép vòng tiếp theo điều chỉnh.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Chatbot vs Agent

| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| Câu hỏi đơn giản | Đúng | Đúng | Hòa |
| Câu hỏi nhiều bước | Có nguy cơ suy luận sai | Chính xác hơn nhờ tool | **Agent** |

### Experiment 2: Tool parser vs direct answer

- Agent chuyển đổi logic tính toán sang tool cụ thể thay vì để LLM tự suy luận.
- Điều này giảm lỗi sai số trong tính toán tổng đơn hàng và phí vận chuyển.

---

## 6. Production Readiness Review

### Security
- Validate input tool arguments trong `ReActAgent._execute_tool()`.
- Hạn chế hàm `eval` bằng `ast.literal_eval` và `json.loads`.
- Yêu cầu tool chỉ sử dụng handler đã đăng ký.

### Guardrails
- Giới hạn `max_steps` để tránh vòng lặp vô hạn và chi phí tăng.
- Bảo vệ hành động lặp lại bằng guardrail `repeated_actions`.
- Quan sát `TOOL_NOT_FOUND`, `TOOL_ARGUMENT_ERROR`, `TOOL_EXECUTION_ERROR` để phản hồi an toàn.

### Scaling
- Chuyển sang kiến trúc tool catalog lớn hơn để chỉ kích hoạt tool cần thiết.
- Dùng queue bất đồng bộ cho các tool chậm và dịch vụ API bên ngoài.
- Lưu trace agent vào cơ sở dữ liệu để phân tích lỗi và tối ưu prompt.

---

 
# Lab 3: Chatbot vs ReAct Agent (Industry Edition)

Welcome to Phase 3 of the Agentic AI course! This lab focuses on moving from a simple LLM Chatbot to a sophisticated **ReAct Agent** with industry-standard monitoring.

## 🚀 Getting Started

### 1. Setup Environment
Copy the `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Directory Structure
- `src/tools/`: Extension point for your custom tools.

## 🏠 Running with Local Models (CPU)

If you don't want to use OpenAI or Gemini, you can run open-source models (like Phi-3) directly on your CPU using `llama-cpp-python`.

### 1. Download the Model
Download the **Phi-3-mini-4k-instruct-q4.gguf** (approx 2.2GB) from Hugging Face:
- [Phi-3-mini-4k-instruct-GGUF](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)
- Direct Download: [phi-3-mini-4k-instruct-q4.gguf](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf)

### 2. Place Model in Project
Create a `models/` folder in the root and move the downloaded `.gguf` file there.

### 3. Update `.env`
Change your `DEFAULT_PROVIDER` and set the path:
```env
DEFAULT_PROVIDER=local
LOCAL_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf
```

## 🎯 Lab Deliverables

1. **Baseline Chatbot**: `src/chatbot.py` makes one direct LLM call and has no tools.
2. **ReAct Agent v2**: `src/agent/agent.py` implements Thought → Action → Observation with argument parsing, tool dispatch, telemetry, and loop guardrails.
3. **E-commerce tools**: `src/tools/ecommerce.py` provides stock, coupon, shipping, and total-calculation tools.
4. **Provider switching**: `src/core/provider_factory.py` creates OpenAI, Gemini, or local providers through the same `LLMProvider` interface.
5. **Failure analysis**: structured JSON logs are written to `logs/`; `scripts/analyze_logs.py` summarizes latency, token usage, estimated cost, completion rate, and error events.

## ▶️ Run the Lab

Install the dependencies and configure one provider in `.env`:

```bash
pip install -r requirements.txt
python3 -m src.main --mode agent --provider openai
```

Use `--provider gemini` or `--provider local` to switch implementations. A full
e-commerce request is the default query; a custom one can be supplied with
`--query`:

```bash
python3 -m src.main --mode agent --provider gemini \
  --query "I want 2 iPhone 15 with WINNER shipped to Hanoi. What is the total?"
python3 -m src.main --mode chatbot --provider openai --query "What is an AI agent?"
```

Run the deterministic tests without an API key:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py"
```

After a run, inspect the JSON telemetry:

```bash
python3 scripts/analyze_logs.py logs/YYYY-MM-DD.log
```

## 🧰 Tool Inventory

| Tool | Input | Purpose |
| --- | --- | --- |
| `check_stock` | `{"item_name": "iPhone 15"}` | Returns quantity, unit price, and unit weight. |
| `get_discount` | `{"coupon_code": "WINNER"}` | Validates a coupon and returns a percentage. |
| `calc_shipping` | `{"weight_kg": 0.342, "destination": "Hanoi"}` | Calculates domestic shipping in VND. |
| `calculate_order_total` | price, quantity, discount, shipping JSON fields | Returns a transparent VND order breakdown. |

## 🛠️ Design Notes

- **Baseline vs agent**: the baseline can answer a simple question, but it cannot
  retrieve stock or calculate an order because it has no tool loop. The ReAct
  agent sends each tool result back to the LLM as an `Observation`.
- **Safety**: only registered callables can run; arguments are decoded with JSON
  or `ast.literal_eval`, never `eval`; malformed actions, unknown tools, provider
  failures, repeated actions, and maximum-step exhaustion become explicit events.
- **Observability**: `LLM_METRIC`, `AGENT_TOOL_CALL`, `AGENT_PARSE_ERROR`,
  `AGENT_GUARDRAIL`, and `AGENT_END` events make a failure trace reviewable.

The completed reports are in `report/group_report/` and
`report/individual_reports/`.

---

*Happy Coding! Let's build agents that actually work.*

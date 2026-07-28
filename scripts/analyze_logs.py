"""Summarise JSON telemetry events emitted by the chatbot and ReAct agent.

Usage: python3 scripts/analyze_logs.py logs/2026-07-28.log
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def load_events(path: Path) -> List[Dict[str, Any]]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def percentile(values: List[int], percentile_value: int) -> int:
    if not values:
        return 0
    sorted_values = sorted(values)
    index = min(len(sorted_values) - 1, round((percentile_value / 100) * (len(sorted_values) - 1)))
    return sorted_values[index]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/analyze_logs.py <log-file>")

    events = load_events(Path(sys.argv[1]))
    metrics = [event["data"] for event in events if event.get("event") == "LLM_METRIC"]
    endings = [event["data"] for event in events if event.get("event") == "AGENT_END"]
    errors = Counter(event.get("event") for event in events if "ERROR" in event.get("event", ""))

    latencies = [int(metric.get("latency_ms", 0)) for metric in metrics]
    total_tokens = [int(metric.get("total_tokens", 0)) for metric in metrics]
    total_cost = sum(float(metric.get("cost_estimate", 0)) for metric in metrics)
    successful = sum(ending.get("reason") == "final_answer" for ending in endings)

    print(f"LLM requests: {len(metrics)}")
    print(f"Latency P50/P99 (ms): {percentile(latencies, 50)}/{percentile(latencies, 99)}")
    print(f"Average tokens per request: {statistics.mean(total_tokens) if total_tokens else 0:.1f}")
    print(f"Estimated total cost: ${total_cost:.6f}")
    print(f"Agent final-answer rate: {successful}/{len(endings)}")
    print(f"Error events: {dict(errors) or 'none'}")


if __name__ == "__main__":
    main()

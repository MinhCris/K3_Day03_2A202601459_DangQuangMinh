import unittest
from typing import Any, Dict, Generator, Optional

from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider
from src.tools.ecommerce import get_ecommerce_tools


class ScriptedProvider(LLMProvider):
    """A predictable provider for testing the agent without network access."""

    def __init__(self, responses):
        super().__init__(model_name="scripted-test-model")
        self.responses = iter(responses)
        self.prompts = []

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        self.prompts.append({"prompt": prompt, "system_prompt": system_prompt})
        return {
            "content": next(self.responses),
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "latency_ms": 1,
            "provider": "scripted",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield ""


class ReActAgentTests(unittest.TestCase):
    def test_multistep_tool_observation_is_sent_back_to_model(self):
        provider = ScriptedProvider([
            'Thought: I need product data.\nAction: check_stock({"item_name": "iPhone 15"})',
            "Final Answer: iPhone 15 is available.",
        ])
        agent = ReActAgent(provider, get_ecommerce_tools())

        self.assertEqual(agent.run("Is iPhone 15 available?"), "iPhone 15 is available.")
        self.assertIn('"available_quantity": 5', provider.prompts[1]["prompt"])
        self.assertEqual(agent.history[-1]["role"], "assistant")

    def test_keyword_arguments_and_total_calculation(self):
        agent = ReActAgent(ScriptedProvider([]), get_ecommerce_tools())
        result = agent._execute_tool(
            "calculate_order_total",
            "unit_price_vnd=22990000, quantity=2, discount_percent=10, shipping_fee_vnd=30000",
        )
        self.assertIn('"total_vnd": 41412000', result)

    def test_unknown_tool_becomes_an_observation(self):
        provider = ScriptedProvider([
            "Thought: Try a tool.\nAction: search_web({\"query\": \"price\"})",
            "Final Answer: That tool is unavailable, so I cannot look it up.",
        ])
        agent = ReActAgent(provider, get_ecommerce_tools())

        self.assertIn("unavailable", agent.run("Look up a price."))
        self.assertIn("TOOL_NOT_FOUND", provider.prompts[1]["prompt"])

    def test_malformed_action_is_retried_then_finalized(self):
        provider = ScriptedProvider([
            "Thought: I need stock.\nAction: check_stock {item_name: iPhone 15}",
            "Final Answer: I need a valid product identifier.",
        ])
        agent = ReActAgent(provider, get_ecommerce_tools())

        self.assertEqual(agent.run("Check stock"), "I need a valid product identifier.")
        self.assertIn("PARSER_ERROR", provider.prompts[1]["prompt"])

    def test_max_steps_prevents_infinite_loop(self):
        provider = ScriptedProvider([
            'Thought: Repeat.\nAction: check_stock({"item_name": "iPhone 15"})',
            'Thought: Repeat.\nAction: check_stock({"item_name": "iPhone 15"})',
        ])
        agent = ReActAgent(provider, get_ecommerce_tools(), max_steps=2)

        self.assertIn("within 2 steps", agent.run("Check stock"))
        self.assertEqual(len(provider.prompts), 2)


if __name__ == "__main__":
    unittest.main()

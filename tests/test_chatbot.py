import unittest
from typing import Any, Dict, Generator, Optional

from src.chatbot import Chatbot
from src.core.llm_provider import LLMProvider


class OneShotProvider(LLMProvider):
    def __init__(self):
        super().__init__(model_name="one-shot-test-model")
        self.calls = 0

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        self.calls += 1
        return {
            "content": "A direct answer.",
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            "latency_ms": 1,
            "provider": "scripted",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield ""


class ChatbotTests(unittest.TestCase):
    def test_chatbot_is_a_single_llm_call_without_tools(self):
        provider = OneShotProvider()
        self.assertEqual(Chatbot(provider).run("Hello"), "A direct answer.")
        self.assertEqual(provider.calls, 1)


if __name__ == "__main__":
    unittest.main()

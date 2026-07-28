"""Minimal direct-answer chatbot used as the lab baseline."""

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class Chatbot:
    """Ask the LLM once without access to tool execution or observations."""

    SYSTEM_PROMPT = (
        "You are a helpful e-commerce assistant. Answer directly using only the "
        "information in the user's message. If data is missing, say that you do not know it."
    )

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, user_input: str) -> str:
        logger.log_event("CHATBOT_START", {"input": user_input, "model": self.llm.model_name})
        try:
            result = self.llm.generate(user_input, system_prompt=self.SYSTEM_PROMPT)
            tracker.track_request(
                provider=str(result.get("provider", self.llm.__class__.__name__)),
                model=self.llm.model_name,
                usage=result.get("usage", {}),
                latency_ms=int(result.get("latency_ms", 0)),
            )
            answer = str(result.get("content", "")).strip()
            logger.log_event("CHATBOT_END", {"reason": "response"})
            return answer or "I could not generate an answer."
        except Exception as exc:
            logger.error("Chatbot generation failed", exc_info=True)
            logger.log_event("CHATBOT_ERROR", {"error": str(exc)})
            return "I could not generate an answer. Please try again."

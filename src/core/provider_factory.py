"""Create one of the interchangeable providers from environment configuration."""

import os
from typing import Optional

from dotenv import load_dotenv

from src.core.llm_provider import LLMProvider


def create_provider(provider_name: Optional[str] = None, model_name: Optional[str] = None) -> LLMProvider:
    """Create an OpenAI, Gemini, or local provider using ``.env`` values.

    Imports are intentionally lazy so users only need to install the SDK for the
    provider they selected.
    """
    load_dotenv()
    provider = (provider_name or os.getenv("DEFAULT_PROVIDER", "openai")).strip().lower()

    if provider == "openai":
        from src.core.openai_provider import OpenAIProvider

        return OpenAIProvider(
            model_name=model_name or os.getenv("DEFAULT_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    if provider in {"gemini", "google"}:
        from src.core.gemini_provider import GeminiProvider

        return GeminiProvider(
            model_name=model_name or os.getenv("DEFAULT_MODEL", "gemini-2.5-flash"),
            api_key=os.getenv("GEMINI_API_KEY"),
        )
    if provider == "local":
        from src.core.local_provider import LocalProvider

        model_path = os.getenv("LOCAL_MODEL_PATH")
        if not model_path:
            raise ValueError("LOCAL_MODEL_PATH must be configured when DEFAULT_PROVIDER=local")
        return LocalProvider(model_path=model_path)

    raise ValueError("Unsupported provider. Choose one of: openai, gemini, local.")

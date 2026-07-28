"""Command-line entry point for comparing the chatbot baseline and ReAct agent."""

import argparse

from src.agent.agent import ReActAgent
from src.chatbot import Chatbot
from src.core.provider_factory import create_provider
from src.tools import get_ecommerce_tools


def main() -> None:
    parser = argparse.ArgumentParser(description="Lab 3 chatbot vs ReAct agent")
    parser.add_argument("--mode", choices=("chatbot", "agent"), default="agent")
    parser.add_argument("--provider", choices=("openai", "gemini", "local"))
    parser.add_argument("--model", help="Override the provider's default model")
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument(
        "--query",
        default="I want to buy 2 iPhone 15 using code WINNER and ship to Hanoi. What is the total?",
    )
    args = parser.parse_args()

    provider = create_provider(args.provider, args.model)
    if args.mode == "chatbot":
        answer = Chatbot(provider).run(args.query)
    else:
        answer = ReActAgent(provider, get_ecommerce_tools(), max_steps=args.max_steps).run(args.query)
    print(answer)


if __name__ == "__main__":
    main()

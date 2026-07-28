"""A small, observable ReAct agent implementation for the lab."""

import ast
import json
import re
import sys
import threading
import time
import itertools
from typing import Any, Dict, List, Optional, Tuple

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class Spinner:
    def __init__(self, message: str = "Loading"):
        self.message = message
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _spin(self) -> None:
        for char in itertools.cycle("|/-\\"):
            if not self._running:
                break
            sys.stdout.write(f"\r{self.message} {char}")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stdout.flush()

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join()


class ReActAgent:
    """Execute a Thought -> Action -> Observation -> Final Answer loop.

    Each tool is a dictionary with ``name``, ``description``, and one callable
    field: ``func``, ``function``, ``callable``, or ``handler``.  The deliberately
    simple contract makes it easy for students to add tools without a framework.
    """

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")

        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history: List[Dict[str, str]] = []

    def get_system_prompt(self) -> str:
        """Return a precise prompt describing tools and the ReAct output format."""
        tool_descriptions = "\n".join(
            f"- {tool['name']}: {tool['description']}" for tool in self.tools
        ) or "- No tools are available."

        return f"""You are a reliable e-commerce assistant that uses a ReAct loop.

Available tools:
{tool_descriptions}

When external information or a calculation is needed, respond with exactly:
Thought: <brief reason for the next step>
Action: <tool_name>(<a JSON object or JSON array of arguments>)

Use only the listed tools. Do not invent an Observation: the application will
provide it after every action. Read each Observation before choosing the next
action. If an observation reports an error, correct the arguments or choose a
different tool. Once the request is fully solved, respond with exactly:
Final Answer: <clear answer for the user>
"""

    def run(self, user_input: str) -> str:
        """Run the agent until it returns a final answer or reaches ``max_steps``."""
        current_prompt = user_input.strip()
        self.history = [{"role": "user", "content": current_prompt}]
        logger.log_event("AGENT_START", {"input": current_prompt, "model": self.llm.model_name})

        previous_action: Optional[Tuple[str, str]] = None
        repeated_actions = 0

        for step in range(1, self.max_steps + 1):
            response = self._generate(current_prompt, step)
            if response is None:
                return "I could not generate a response. Please try again."

            self.history.append({"role": "assistant", "content": response})
            logger.log_event("AGENT_RESPONSE", {"step": step, "response": response})

            final_answer = self._extract_final_answer(response)
            if final_answer is not None:
                logger.log_event("AGENT_END", {"steps": step, "reason": "final_answer"})
                return final_answer or "I could not produce a final answer."

            action = self._extract_action(response)
            if action is None:
                observation = (
                    "PARSER_ERROR: No valid Action was found. Use "
                    "Action: tool_name({\"argument\": \"value\"}) or provide Final Answer:."
                )
                logger.log_event("AGENT_PARSE_ERROR", {"step": step, "response": response})
            elif action == previous_action:
                repeated_actions += 1
                observation = (
                    "GUARDRAIL: The identical action was requested twice in a row. "
                    "Use the previous observation to choose a different action or give a Final Answer."
                )
                logger.log_event("AGENT_GUARDRAIL", {
                    "step": step,
                    "reason": "repeated_action",
                    "tool": action[0],
                    "arguments": action[1],
                })
            else:
                repeated_actions = 0
                observation = self._execute_tool(*action)
                logger.log_event("AGENT_TOOL_CALL", {
                    "step": step,
                    "tool": action[0],
                    "arguments": action[1],
                    "observation": observation,
                })

            if repeated_actions >= 2:
                logger.log_event("AGENT_END", {"steps": step, "reason": "repeated_action"})
                return "I stopped because the same tool action kept repeating. Please rephrase your request."

            previous_action = action
            self.history.append({"role": "tool", "content": observation})
            current_prompt += (
                f"\n\nAssistant response:\n{response}\n"
                f"Observation: {observation}\n"
                "Continue with the next Thought and Action, or Final Answer."
            )

        logger.log_event("AGENT_END", {"steps": self.max_steps, "reason": "max_steps"})
        return f"I could not complete the request within {self.max_steps} steps."

    def _generate(self, prompt: str, step: int) -> Optional[str]:
        """Call the provider and record its standard performance metrics."""
        spinner = Spinner(f"Step {step}/{self.max_steps}: generating")
        spinner.start()
        try:
            result = self.llm.generate(prompt, system_prompt=self.get_system_prompt())
        finally:
            spinner.stop()

        try:
            tracker.track_request(
                provider=str(result.get("provider", self.llm.__class__.__name__)),
                model=self.llm.model_name,
                usage=result.get("usage", {}),
                latency_ms=int(result.get("latency_ms", 0)),
            )
            return str(result.get("content", "")).strip()
        except Exception as exc:  # Provider errors must not crash the application.
            logger.error("LLM generation failed", exc_info=True)
            logger.log_event("AGENT_ERROR", {"step": step, "stage": "generation", "error": str(exc)})
            return None

    def _execute_tool(self, tool_name: str, raw_args: str) -> str:
        """Find a registered tool, safely parse its arguments, and execute it."""
        tool = next((item for item in self.tools if item.get("name") == tool_name), None)
        if tool is None:
            return f"TOOL_NOT_FOUND: '{tool_name}' is not an available tool."

        function = next(
            (
                tool.get(key)
                for key in ("func", "function", "callable", "handler")
                if callable(tool.get(key))
            ),
            None,
        )
        if function is None:
            return f"TOOL_CONFIGURATION_ERROR: '{tool_name}' has no callable handler."

        try:
            positional, keyword = self._parse_arguments(raw_args)
            result = function(*positional, **keyword)
            return self._serialise_observation(result)
        except (TypeError, ValueError, SyntaxError, json.JSONDecodeError) as exc:
            return f"TOOL_ARGUMENT_ERROR: {tool_name} could not use the supplied arguments: {exc}"
        except Exception as exc:  # Tool bugs are returned as an observation for recovery.
            logger.error(f"Tool {tool_name} failed", exc_info=True)
            return f"TOOL_EXECUTION_ERROR: {tool_name} failed: {exc}"

    @staticmethod
    def _extract_final_answer(response: str) -> Optional[str]:
        match = re.search(
            r"^\s*Final\s*Answer\s*:\s*(.*)$",
            response,
            flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_action(response: str) -> Optional[Tuple[str, str]]:
        """Extract one action line, including arguments wrapped in parentheses."""
        match = re.search(
            r"^\s*Action\s*:\s*([A-Za-z_]\w*)\s*\((.*)\)\s*$",
            response,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if not match:
            return None
        return match.group(1), match.group(2).strip()

    @staticmethod
    def _parse_arguments(raw_args: str) -> Tuple[List[Any], Dict[str, Any]]:
        """Parse JSON first, then safe Python literal positional/keyword arguments."""
        raw_args = raw_args.strip()
        if not raw_args:
            return [], {}

        if raw_args.startswith("```") and raw_args.endswith("```"):
            raw_args = re.sub(r"^```(?:json|python)?\s*|\s*```$", "", raw_args).strip()

        try:
            value = json.loads(raw_args)
        except json.JSONDecodeError:
            value = None
        else:
            if isinstance(value, dict):
                return [], value
            if isinstance(value, list):
                return value, {}
            return [value], {}

        try:
            value = ast.literal_eval(raw_args)
        except (ValueError, SyntaxError):
            value = None
        else:
            if isinstance(value, dict):
                return [], value
            if isinstance(value, (list, tuple)):
                return list(value), {}
            return [value], {}

        expression = ast.parse(f"tool({raw_args})", mode="eval").body
        if not isinstance(expression, ast.Call) or any(keyword.arg is None for keyword in expression.keywords):
            raise ValueError("arguments must be JSON or literal values")
        return (
            [ast.literal_eval(argument) for argument in expression.args],
            {keyword.arg: ast.literal_eval(keyword.value) for keyword in expression.keywords},
        )

    @staticmethod
    def _serialise_observation(result: Any) -> str:
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            return str(result)

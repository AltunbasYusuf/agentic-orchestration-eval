"""LangChain chat model backed by the Claude Code CLI's headless mode
(``claude -p``), used as an alternative to a pay-per-token Anthropic API
key. Selected via ``BMAD_MODEL=claude-code[:<model-alias>]`` (see
``.env.example``) -- billed against a Claude Code / claude.ai subscription
instead of a separate API key.

Every call is stateless (``--no-session-persistence``): the full message
history is flattened into one prompt per invocation, since nodes in this
port already build their own context string per call rather than relying
on multi-turn session memory.

Structured output (``with_structured_output``) uses the CLI's native
``--json-schema`` validation instead of LangChain's usual tool-calling
route, since a subprocess-backed model has no bind_tools support of its
own for that path.

Tool calling (``bind_tools``, used by ``build.py``'s ``create_react_agent``
coding loop) is emulated: each turn asks the model to pick one bound tool
(or answer directly) via a small routing JSON schema, translating the
result into a proper ``AIMessage.tool_calls`` entry so LangGraph's
prebuilt ``ToolNode`` can execute it exactly as it would for any other
tool-calling model.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from typing import Any, List, Optional, Sequence, Type

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import BaseTool
from pydantic import BaseModel

_CLAUDE_BIN = shutil.which("claude") or "claude"


def _flatten(messages: Sequence[BaseMessage]) -> tuple[str, str]:
    """Split messages into (system_prompt, transcript) -- system messages go
    to ``--system-prompt``, everything else is rendered as plain text since
    each call is stateless and must carry its own history."""
    system_parts: list[str] = []
    transcript_parts: list[str] = []
    for m in messages:
        if isinstance(m, SystemMessage):
            system_parts.append(str(m.content))
        elif isinstance(m, HumanMessage):
            transcript_parts.append(f"Human: {m.content}")
        elif isinstance(m, ToolMessage):
            transcript_parts.append(f"Tool result ({m.name}): {m.content}")
        elif isinstance(m, AIMessage):
            if m.tool_calls:
                calls = ", ".join(f"{tc['name']}({tc['args']})" for tc in m.tool_calls)
                transcript_parts.append(f"Assistant (tool call): {calls}")
            elif m.content:
                transcript_parts.append(f"Assistant: {m.content}")
        else:
            transcript_parts.append(str(m.content))
    return "\n\n".join(system_parts), "\n\n".join(transcript_parts)


def _run_claude(
    transcript: str,
    system_prompt: str,
    model: str,
    json_schema: Optional[dict] = None,
    timeout: int = 300,
) -> dict:
    cmd = [_CLAUDE_BIN, "-p", "--output-format", "json", "--no-session-persistence", "--tools", ""]
    if model:
        cmd += ["--model", model]
    if system_prompt:
        cmd += ["--system-prompt", system_prompt]
    if json_schema:
        cmd += ["--json-schema", json.dumps(json_schema)]

    result = subprocess.run(
        cmd,
        input=transcript or "Proceed.",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr[:2000] or result.stdout[:2000]}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"claude CLI returned non-JSON output: {result.stdout[:2000]!r}") from exc
    if payload.get("is_error"):
        raise RuntimeError(f"claude CLI reported an error: {payload.get('result') or payload}")
    return payload


def _tool_router_schema(tools: Sequence[BaseTool]) -> dict:
    tool_names = [t.name for t in tools] + ["final_answer"]
    descriptions = "\n".join(f"- {t.name}: {t.description}" for t in tools)
    return {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "enum": tool_names,
                "description": f"Which tool to call next, or 'final_answer' when done. Available tools:\n{descriptions}",
            },
            "tool_input": {
                "type": "object",
                "description": "Arguments for the chosen tool, keyed by its parameter names. Omit when tool='final_answer'.",
            },
            "final_answer": {
                "type": "string",
                "description": "Your final response text. Only set when tool='final_answer'.",
            },
        },
        "required": ["tool"],
    }


class ClaudeCodeChatModel(BaseChatModel):
    """Chat model that shells out to ``claude -p`` for every call."""

    model: str = ""
    temperature: float = 0.4
    timeout: int = 300

    @property
    def _llm_type(self) -> str:
        return "claude-code-cli"

    def bind_tools(self, tools: Sequence[BaseTool], **kwargs: Any) -> Runnable:
        return self.bind(tools=list(tools), **kwargs)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        tools: Optional[Sequence[BaseTool]] = kwargs.pop("tools", None)
        system_prompt, transcript = _flatten(messages)

        if tools:
            payload = _run_claude(
                transcript, system_prompt, self.model, json_schema=_tool_router_schema(tools), timeout=self.timeout
            )
            decision = payload.get("structured_output") or json.loads(payload["result"])
            if decision.get("tool") and decision["tool"] != "final_answer":
                tool_call = {
                    "name": decision["tool"],
                    "args": decision.get("tool_input") or {},
                    "id": f"call_{uuid.uuid4().hex[:12]}",
                    "type": "tool_call",
                }
                ai_message = AIMessage(content="", tool_calls=[tool_call])
            else:
                ai_message = AIMessage(content=decision.get("final_answer", ""))
        else:
            payload = _run_claude(transcript, system_prompt, self.model, timeout=self.timeout)
            ai_message = AIMessage(content=payload.get("result", ""))

        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    def with_structured_output(self, schema: Type[BaseModel], **kwargs: Any) -> Runnable:
        json_schema = schema.model_json_schema()

        def _invoke(messages: List[BaseMessage]) -> BaseModel:
            system_prompt, transcript = _flatten(messages)
            payload = _run_claude(transcript, system_prompt, self.model, json_schema=json_schema, timeout=self.timeout)
            data = payload.get("structured_output")
            if data is None:
                data = json.loads(payload["result"])
            return schema.model_validate(data)

        return RunnableLambda(_invoke)

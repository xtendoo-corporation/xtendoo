"""Scriptable provider for deterministic tests (no network, no cost).

A script is a list of steps consumed in order, one per ``complete`` call. A step is:
- an ``LLMResponse``;
- an ``Exception`` instance (raised);
- a callable ``(LLMRequest) -> LLMResponse | Exception``.

Select it with the provider setting ``fake`` and a JSON script in the parameter
``xtd_ai.fake_script`` (a file path).
JSON format: a list of objects
``{"text": str, "tool_calls": [{"name", "arguments", "id"?}], "stop_reason"?,
"usage"?, "raise"?}``.
"""

from __future__ import annotations

import itertools
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ..agent.errors import ProviderError
from ..agent.types import LLMRequest, LLMResponse, Message, StopReason, ToolCall, Usage

Step = LLMResponse | Exception | Callable[[LLMRequest], "LLMResponse | Exception"]


def text_response(
    text: str, usage: Usage | None = None, stop: StopReason = StopReason.END_TURN
) -> LLMResponse:
    return LLMResponse(
        message=Message(role="assistant", text=text),
        stop_reason=stop,
        usage=usage or Usage(input_tokens=10, output_tokens=5),
        model="fake-model",
    )


_ids = itertools.count(1)


def tool_response(
    *calls: tuple[str, dict[str, Any]] | ToolCall,
    text: str = "",
    usage: Usage | None = None,
) -> LLMResponse:
    built = tuple(
        c
        if isinstance(c, ToolCall)
        else ToolCall(id=f"toolu_fake_{next(_ids)}", name=c[0], arguments=c[1])
        for c in calls
    )
    return LLMResponse(
        message=Message(role="assistant", text=text, tool_calls=built),
        stop_reason=StopReason.TOOL_USE,
        usage=usage or Usage(input_tokens=10, output_tokens=5),
        model="fake-model",
    )


class FakeProvider:
    name = "fake"

    def __init__(self, script: Sequence[Step], model: str = "fake-model"):
        self.model = model
        self._script = list(script)
        self._pos = 0
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if self._pos >= len(self._script):
            raise ProviderError("fake provider script exhausted")
        step = self._script[self._pos]
        self._pos += 1
        if callable(step) and not isinstance(step, (LLMResponse, Exception)):
            step = step(request)
        if isinstance(step, Exception):
            raise step
        return step

    @classmethod
    def from_file(cls, path: str | Path, model: str = "fake-model") -> FakeProvider:
        steps: list[Step] = []
        for item in json.loads(Path(path).read_text(encoding="utf-8")):
            if "raise" in item:
                steps.append(ProviderError(str(item["raise"])))
                continue
            usage = Usage(**item["usage"]) if "usage" in item else None
            if item.get("tool_calls"):
                calls = [
                    ToolCall(
                        id=c.get("id") or f"toolu_fake_{next(_ids)}",
                        name=c["name"],
                        arguments=c.get("arguments", {}),
                    )
                    for c in item["tool_calls"]
                ]
                steps.append(
                    tool_response(*calls, text=item.get("text", ""), usage=usage)
                )
            else:
                steps.append(
                    text_response(
                        item.get("text", ""),
                        usage,
                        StopReason(item.get("stop_reason", "end_turn")),
                    )
                )
        return cls(steps, model=model)

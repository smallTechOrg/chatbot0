"""Providers such as Gemini behind an OpenAI-compatible router reject a request
with only a system message ("at least one contents field is required"). Every
single-prompt call must carry a human message."""

import pytest
from langchain_core.messages import HumanMessage

from chat import lead_capture
from summary import periodic


class _Response:
    def __init__(self, content):
        self.content = content


class _StrictModel:
    """Fake chat model that behaves like a provider rejecting system-only input."""

    def __init__(self, reply):
        self.reply = reply
        self.seen = []

    def invoke(self, messages):
        self.seen.append(messages)
        if not any(isinstance(m, HumanMessage) for m in messages):
            raise RuntimeError("400 upstream_rejected_request: at least one contents field is required")
        return _Response(self.reply)


def test_summarise_conversation_sends_a_human_message(monkeypatch):
    model = _StrictModel("  A short summary.  ")
    monkeypatch.setattr(periodic, "get_chat_model", lambda: model)
    monkeypatch.setattr(periodic, "_get_summary_prompt_template", lambda: "Summarise: {conversation}")

    summary = periodic.summarise_conversation([{"type": "human", "content": "hello there"}])

    assert summary == "A short summary."
    assert "hello there" in model.seen[0][0].content


@pytest.mark.parametrize("request_type", ["sales", "support"])
def test_lead_detection_sends_a_human_message(monkeypatch, request_type):
    model = _StrictModel('{"contact_name": "Test", "email": "t@example.org", "mobile": "", "country": ""}')
    monkeypatch.setattr(lead_capture, "get_chat_model", lambda: model)
    monkeypatch.setattr(lead_capture, "get_prompt", lambda *a: "Extract from: {message}")

    info = lead_capture._detect_info_with_llm("I'm Test, t@example.org", request_type, "example.com")

    assert info["contact_name"] == "Test"
    assert "I'm Test" in model.seen[0][0].content


def test_strict_model_rejects_system_only():
    from langchain_core.messages import SystemMessage

    with pytest.raises(RuntimeError):
        _StrictModel("x").invoke([SystemMessage(content="only system")])

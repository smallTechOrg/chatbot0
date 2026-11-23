"""chat.engine: the reply and the lead capture run at the same time, and a capture failure never loses the reply."""

import time

from chat import engine

DELAY = 0.3


def _slow(name, calls):
    def run(*args):
        calls.append(name)
        time.sleep(DELAY)
        return "the reply"

    return run


def test_reply_and_lead_capture_overlap(monkeypatch):
    calls = []
    monkeypatch.setattr(engine, "_generate_reply", _slow("reply", calls))
    monkeypatch.setattr(engine, "process_conversation", _slow("capture", calls))

    started = time.monotonic()
    reply = engine.get_groq_response("hi", "s1", "sales", "COMMON")
    elapsed = time.monotonic() - started

    assert reply == "the reply"
    assert sorted(calls) == ["capture", "reply"]
    assert elapsed < DELAY * 1.7, f"took {elapsed:.2f}s: the two calls ran one after the other"


def test_a_failing_lead_capture_does_not_lose_the_reply(monkeypatch):
    def boom(*args):
        raise RuntimeError("detection LLM down")

    monkeypatch.setattr(engine, "_generate_reply", lambda *a: "the reply")
    monkeypatch.setattr(engine, "process_conversation", boom)
    assert engine.get_groq_response("hi", "s1", "sales", "COMMON") == "the reply"


def test_the_request_waits_for_lead_capture_to_finish(monkeypatch):
    done = []
    monkeypatch.setattr(engine, "_generate_reply", lambda *a: "the reply")
    monkeypatch.setattr(engine, "process_conversation", lambda *a: (time.sleep(DELAY), done.append(1)))
    engine.get_groq_response("hi", "s1", "sales", "COMMON")
    assert done == [1], "capture must finish inside the request (Cloud Run freezes CPU afterwards)"

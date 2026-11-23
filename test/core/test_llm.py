"""core.llm: one model factory, with the backup model as a fallback when configured."""

from langchain_core.runnables import RunnableWithFallbacks

from core import config, llm


class _Groq:
    def __init__(self, groq_api_key, model):
        self.model = model

    def with_fallbacks(self, others):
        return ("fallbacks", self.model, [o.model for o in others])


def test_single_model_without_a_backup(monkeypatch):
    monkeypatch.setattr(llm, "ChatGroq", _Groq)
    monkeypatch.setattr(config, "GROQ_MODEL_NAME", "primary-model")
    monkeypatch.setattr(config, "GROQ_BACKUP_MODEL_NAME", None)
    assert llm.get_chat_model().model == "primary-model"


def test_backup_model_becomes_a_fallback(monkeypatch):
    monkeypatch.setattr(llm, "ChatGroq", _Groq)
    monkeypatch.setattr(config, "GROQ_MODEL_NAME", "primary-model")
    monkeypatch.setattr(config, "GROQ_BACKUP_MODEL_NAME", "backup-model")
    assert llm.get_chat_model() == ("fallbacks", "primary-model", ["backup-model"])


def test_real_fallback_runnable_is_returned(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "dummy")
    monkeypatch.setattr(config, "GROQ_BACKUP_MODEL_NAME", "backup-model")
    assert isinstance(llm.get_chat_model(), RunnableWithFallbacks)

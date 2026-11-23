"""The one place a chat model is built, so the provider, model and fallback are decided once."""

from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq

from core import config


def _groq(model: str) -> ChatGroq:
    return ChatGroq(groq_api_key=config.GROQ_API_KEY, model=model)


def get_chat_model() -> Runnable:
    """
    The chat model every LLM call uses: GROQ_MODEL_NAME, and when GROQ_BACKUP_MODEL_NAME is set, that model
    answers any call the first one fails (rate limit, outage).
    """
    primary = _groq(config.GROQ_MODEL_NAME)
    if config.GROQ_BACKUP_MODEL_NAME:
        return primary.with_fallbacks([_groq(config.GROQ_BACKUP_MODEL_NAME)])
    return primary

"""
The chat engine: one visitor message in, the bot's reply out.

The reply and the lead capture (spotting a name, email or phone in the message) are independent, so they run at
the same time and the request waits for both. They stay inside the request on purpose: Cloud Run gives an
instance CPU only while a request is open, so work left running after the response could freeze mid-way.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from chat.history import get_session_history
from chat.lead_capture import process_conversation
from chat.prompts import get_prompt
from core.llm import get_chat_model

logger = logging.getLogger(__name__)

_PROMPT = ChatPromptTemplate.from_messages(
    [("system", "{system}"), MessagesPlaceholder(variable_name="history"), ("human", "{input}")]
)


def get_groq_response(input_text: str, session_id: str, request_type: str, domain: str) -> str:
    """
    The bot's reply to *input_text*, with the session's earlier messages as memory. Lead capture runs
    concurrently and never raises: a failure there must not cost the visitor their answer.
    """
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_capture_lead, input_text, session_id, request_type, domain)
        return _generate_reply(input_text, session_id, request_type, domain)


def _generate_reply(input_text: str, session_id: str, request_type: str, domain: str) -> str:
    system_prompt = get_prompt(domain, request_type, "system")
    chain_with_history = RunnableWithMessageHistory(
        _PROMPT | get_chat_model(),
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )
    response = chain_with_history.invoke(
        {"input": input_text, "system": system_prompt},
        config={"configurable": {"session_id": session_id}},
    )
    return response.content


def _capture_lead(input_text: str, session_id: str, request_type: str, domain: str) -> None:
    try:
        process_conversation(input_text, session_id, request_type, domain)
        logger.info("[LLM_API] Lead capture completed")
    except Exception as exc:
        logger.warning(f"[LLM_API] Warning: lead capture failed: {exc}")

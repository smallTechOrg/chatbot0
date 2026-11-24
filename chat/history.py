"""Chat memory: per-session message history stored in Postgres, and the /history payload."""

from http import HTTPStatus

from langchain_core.messages import BaseMessage
from langchain_postgres import PostgresChatMessageHistory

from chat.prompts import get_prompt
from core.config import table_name
from core.db_pool import run_with_retry

# PostgresChatMessageHistory.__init__ only checks that a connection is given.
# Each method below puts a pooled connection in place of this one.
_UNBOUND = object()


class PooledChatMessageHistory(PostgresChatMessageHistory):
    """
    Chat history that takes a connection from the pool for each operation. The
    parent class keeps one connection for the life of the object, which a pool
    cannot do.
    """

    def __init__(self, table: str, session_id: str) -> None:
        super().__init__(table, session_id, sync_connection=_UNBOUND)

    def _run(self, operation, label):
        """
        Run one parent operation on a pooled connection, with retry. A retry
        can write a message two times, which is better than a failed request.
        """

        def with_connection(conn):
            self._connection = conn
            try:
                return operation()
            finally:
                self._connection = _UNBOUND

        return run_with_retry(with_connection, label=label)

    def get_messages(self) -> list[BaseMessage]:
        return self._run(super().get_messages, "chat history read")

    def add_messages(self, messages) -> None:
        self._run(lambda: super(PooledChatMessageHistory, self).add_messages(messages), "chat history write")

    def clear(self) -> None:
        self._run(super().clear, "chat history clear")


def get_session_history(session_id):
    return PooledChatMessageHistory(table_name, session_id)


def _message_mapping(messages):
    return [
        {
            "type": msg.type,  # "human" or "ai"
            "content": msg.content,
        }
        for msg in messages
    ]


def get_history(session_id: str, domain):
    """
    Get the chat history for a session_id as a list of dicts.

    Errors go to the caller. The endpoint makes the error response.
    """
    history = get_session_history(session_id)
    status = HTTPStatus.OK
    # Read one time. Each use of .messages goes to the database.
    messages = history.messages
    if not messages:
        # session exists
        first_message = get_prompt(domain, "sales", "intro-message")
        history.add_ai_message(first_message)
        messages = history.messages
        status = HTTPStatus.CREATED

    return {"session_id": session_id, "history": _message_mapping(messages)}, status


def read_history(session_id: str) -> list[dict[str, str]]:
    """The messages of a session, read-only. Unlike get_history it never adds the intro message."""
    return _message_mapping(get_session_history(session_id).get_messages())

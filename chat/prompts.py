"""Look up a domain's prompts, inheriting from its parent domain, and build the system prompt."""

import logging

from core.db_pool import with_connection

logger = logging.getLogger(__name__)

FORMATTING_INSTRUCTION = """

Formatting Rules:
- Use markdown formatting in your responses for readability.
- Use **bold** for key words, service names, or important phrases.
- Use *italic* for subtle emphasis such as names or side notes.
- Use line breaks to separate different points or sections.
- Use bullet points or numbered lists when listing multiple items.
- You may use headings (##, ###) when it improves clarity.
"""


def get_prompt(domain: str, agent_type: str, prompt_type: str) -> str:
    """The prompt text for a domain. A domain without its own prompt uses its parent domain's."""
    if prompt_type == "system" and agent_type == "sales":
        common_prompt = load_prompt_from_db(domain, agent_type, "base-prompt")
        company_prompt = load_prompt_from_db(domain, agent_type, "company")

        parts = []
        if common_prompt:
            parts.append(common_prompt)
        if company_prompt:
            parts.append(company_prompt)

        # Join them into one prompt string and append formatting instructions
        return "\n\n".join(parts) + FORMATTING_INSTRUCTION

    prompt = load_prompt_from_db(domain, agent_type, prompt_type)
    return prompt or ""


def load_prompt_from_db(domain: str, agent_type: str, prompt_type: str):
    """
    Fetch a prompt's text from the DB (JSON or plain text), cache for fast access.
    """
    try:
        row = find_prompt(domain, agent_type, prompt_type)

        if row is None:
            logger.info(f"Prompt not found in DB: {domain}/{agent_type}/{prompt_type}, looking for parent prompt")
            parent_domain = find_parent_key(domain)
            row = find_prompt(parent_domain, agent_type, prompt_type)
            if row is None:
                logger.info(f"Prompt not found in DB for parent Domain: {domain}/{agent_type}/{prompt_type}")
                return None

        return row[0]

    except Exception as e:
        raise RuntimeError(f"Failed to load prompt from DB: {e}") from e


@with_connection
def find_parent_key(conn, key):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT parent.key
            FROM domains child
            LEFT JOIN domains parent ON child.parent = parent.id
            WHERE child.key = %s;
        """,
            (key,),
        )
        row = cur.fetchone()
        return row[0] if row else None


@with_connection
def find_prompt(conn, domain, agent_type, prompt_type):
    # Errors propagate so @with_connection can retry a lost connection;
    # load_prompt_from_db wraps whatever survives the retries.
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT text
            FROM prompts
            WHERE domain = %s AND agent_type = %s AND type = %s
            LIMIT 1;
        """,
            (domain, agent_type, prompt_type),
        )

        return cur.fetchone()

"""Look up a domain's prompts, inheriting up its whole parent chain, and build the system prompt."""

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
    """The prompt text for a domain. A domain without its own prompt uses its nearest ancestor's."""
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


#: How many domains a chain can have. A real chain is two or three long; the cap stops a bad parent loop.
MAX_CHAIN = 10


def parent_chain(key: str) -> list[str]:
    """
    The domain keys a prompt is looked up through, nearest first: [key, its parent, the parent's parent, ...].
    The walk stops at a domain with no parent, at a key it has already seen (a parent loop), or at MAX_CHAIN.
    """
    chain = [key]
    current = key
    while len(chain) < MAX_CHAIN:
        parent = find_parent_key(current)
        if not parent or parent in chain:
            break
        chain.append(parent)
        current = parent
    return chain


def resolve_prompt(domain: str, agent_type: str, prompt_type: str) -> tuple[str | None, str | None]:
    """
    The effective prompt for a domain: (text, the key of the domain it comes from). The domain's own prompt wins;
    without one, the nearest ancestor's is used, all the way up the parent chain. (None, None) when no domain in
    the chain has it.
    """
    try:
        for key in parent_chain(domain):
            row = find_prompt(key, agent_type, prompt_type)
            if row is not None:
                return row[0], key
            logger.info(f"Prompt not found in DB: {key}/{agent_type}/{prompt_type}, looking at the parent domain")
        return None, None
    except Exception as e:
        raise RuntimeError(f"Failed to load prompt from DB: {e}") from e


def load_prompt_from_db(domain: str, agent_type: str, prompt_type: str):
    """The effective prompt text for a domain (see resolve_prompt), or None."""
    return resolve_prompt(domain, agent_type, prompt_type)[0]


@with_connection
def find_parent_key(conn, key):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT parent.key
            FROM domains child
            LEFT JOIN domains parent ON child.parent = parent.id
            WHERE child.key = %s
            ORDER BY child.id
            LIMIT 1;
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

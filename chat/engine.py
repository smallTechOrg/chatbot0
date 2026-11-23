from concurrent.futures import ThreadPoolExecutor

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from chat.history import get_session_history
from chat.lead_capture import process_conversation
from chat.prompts import get_prompt
from core.llm import get_chat_model


def get_groq_response(input_text, session_id, request_type, domain):
    # Choose prompt based on request type & domain
    prompt_type = "system"
    system_prompt = get_prompt(domain, request_type, prompt_type)

    # Rest of your existing code...
    prompt = ChatPromptTemplate.from_messages(
        [("system", "{system}"), MessagesPlaceholder(variable_name="history"), ("human", "{input}")]
    )

    """
    Generate a Groq LLM response using RunnableWithMessageHistory for chat memory.
    
    Args:
        input_text: User input text
        session_id: Session identifier
        process_async: Whether to process conversation asynchronously (default: True)
    """

    # Create the LLM
    llm = get_chat_model()
    # Create the chain
    chain = prompt | llm

    # Wrap the chain with message history
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )

    # Configure the session
    config = {"configurable": {"session_id": session_id}}

    # Get response with history
    response = chain_with_history.invoke({"input": input_text, "system": system_prompt}, config=config)

    bot_response = response.content

    # Handle conversation processing
    # Process conversation asynchronously to avoid blocking the response
    _process_conversation_async(input_text, session_id, request_type, domain)

    return bot_response


def _process_conversation_async(input_text, session_id, request_type, domain):
    """Process conversation asynchronously using ThreadPoolExecutor."""

    def process_in_background():
        try:
            process_conversation(input_text, session_id, request_type, domain)
            print("[LLM_API] Async conversation processing completed")
        except Exception as processing_error:
            print(f"[LLM_API] Warning: Async conversation processing failed: {processing_error}")

    # Submit to thread pool for background processing
    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(process_in_background)

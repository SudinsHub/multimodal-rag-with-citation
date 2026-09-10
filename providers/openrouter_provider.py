"""
OpenRouter provider — access any model via OpenRouter's unified API.

OpenRouter uses the OpenAI-compatible API format, so we reuse ChatOpenAI
with a custom base_url. Any model on OpenRouter can be used:
  - meta-llama/llama-3.1-70b-instruct
  - anthropic/claude-3.5-sonnet
  - google/gemini-2.0-flash-exp:free
  - etc.
"""

from langchain_openai import ChatOpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def create_chat_model(model: str, api_key: str):
    """Create a text chat model via OpenRouter."""
    return ChatOpenAI(
        model=model,
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        temperature=0.1,
        default_headers={
            "HTTP-Referer": "https://github.com/construction-rag",
            "X-Title": "Construction RAG",
        },
    )


def create_vision_model(model: str, api_key: str):
    """Create a vision/multimodal model via OpenRouter."""
    return ChatOpenAI(
        model=model,
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
        temperature=0.1,
        default_headers={
            "HTTP-Referer": "https://github.com/construction-rag",
            "X-Title": "Construction RAG",
        },
    )

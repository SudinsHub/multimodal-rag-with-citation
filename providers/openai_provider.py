"""OpenAI provider — direct OpenAI API access."""

from langchain_openai import ChatOpenAI


def create_chat_model(model: str, api_key: str):
    """Create a text chat model using OpenAI."""
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=0.1,
    )


def create_vision_model(model: str, api_key: str):
    """Create a vision/multimodal model using OpenAI (e.g., gpt-4o)."""
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=0.1,
    )

"""Ollama provider — local LLM via Ollama server."""

from langchain_ollama import ChatOllama


def create_chat_model(model: str, base_url: str):
    """Create a text chat model using Ollama."""
    return ChatOllama(
        model=model,
        base_url=base_url,
        temperature=0.1,
    )


def create_vision_model(model: str, base_url: str):
    """Create a vision/multimodal model using Ollama (e.g., llava, bakllava)."""
    return ChatOllama(
        model=model,
        base_url=base_url,
        temperature=0.1,
    )

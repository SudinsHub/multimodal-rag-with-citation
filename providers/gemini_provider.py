"""Google Gemini provider — via Google Generative AI API."""

from langchain_google_genai import ChatGoogleGenerativeAI


def create_chat_model(model: str, api_key: str):
    """Create a text chat model using Google Gemini."""
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.1,
    )


def create_vision_model(model: str, api_key: str):
    """
    Create a vision/multimodal model using Google Gemini.
    Gemini models natively support multimodal input (text + images).
    """
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.1,
    )

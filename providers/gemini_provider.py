from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings


def create_chat_model(model: str, api_key: str):
    """Create a text chat model using Google Gemini with dynamic output token allocation."""
    max_tokens = max(getattr(settings, "MAX_OUTPUT_TOKENS", 4096), 4096)
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.1,
        max_output_tokens=max_tokens,
    )


def create_vision_model(model: str, api_key: str):
    """
    Create a vision/multimodal model using Google Gemini.
    Gemini models natively support multimodal input (text + images).
    """
    max_tokens = max(getattr(settings, "MAX_OUTPUT_TOKENS", 4096), 4096)
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.1,
        max_output_tokens=max_tokens,
    )


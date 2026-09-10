"""
Provider Factory — the heart of the provider-agnostic design.

Returns LangChain-compatible LLM, VLM, and Embedding objects
based on .env configuration. The notebook never imports a specific provider.

Usage in notebook:
    from providers.factory import get_llm, get_vlm, get_embeddings

    llm = get_llm()              # Text generation
    vlm = get_vlm()              # Vision/multimodal (image → text)
    embeddings = get_embeddings() # Text embeddings

Switch providers by editing .env — zero code changes needed:
    LLM_PROVIDER=gemini          # was "ollama"
    LLM_MODEL=gemini-2.0-flash   # was "llama3.2"

You can even mix providers:
    LLM_PROVIDER=gemini          # Text generation via Gemini
    VLM_PROVIDER=openai          # Image summaries via GPT-4o
    EMBEDDING_PROVIDER=local     # Local sentence-transformers
"""

from config.settings import settings


def get_llm():
    """
    Returns a LangChain chat model for text generation.

    The returned object is always a BaseChatModel — compatible with
    all LangChain chains, prompts, and runnables.
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        from providers.ollama_provider import create_chat_model
        return create_chat_model(settings.LLM_MODEL, settings.OLLAMA_BASE_URL)

    elif provider == "gemini":
        from providers.gemini_provider import create_chat_model
        return create_chat_model(settings.LLM_MODEL, settings.GOOGLE_API_KEY)

    elif provider == "openrouter":
        from providers.openrouter_provider import create_chat_model
        return create_chat_model(settings.LLM_MODEL, settings.OPENROUTER_API_KEY)

    elif provider == "openai":
        from providers.openai_provider import create_chat_model
        return create_chat_model(settings.LLM_MODEL, settings.OPENAI_API_KEY)

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. "
            f"Supported: ollama, gemini, openrouter, openai"
        )


def get_vlm():
    """
    Returns a LangChain chat model capable of vision/multimodal input.

    Used for generating text summaries from images/figures extracted
    from PDFs. The model must support image input in its messages.
    """
    provider = settings.VLM_PROVIDER.lower()

    if provider == "ollama":
        from providers.ollama_provider import create_vision_model
        return create_vision_model(settings.VLM_MODEL, settings.OLLAMA_BASE_URL)

    elif provider == "gemini":
        from providers.gemini_provider import create_vision_model
        return create_vision_model(settings.VLM_MODEL, settings.GOOGLE_API_KEY)

    elif provider == "openrouter":
        from providers.openrouter_provider import create_vision_model
        return create_vision_model(settings.VLM_MODEL, settings.OPENROUTER_API_KEY)

    elif provider == "openai":
        from providers.openai_provider import create_vision_model
        return create_vision_model(settings.VLM_MODEL, settings.OPENAI_API_KEY)

    else:
        raise ValueError(
            f"Unknown VLM_PROVIDER: '{provider}'. "
            f"Supported: ollama, gemini, openrouter, openai"
        )


def get_embeddings():
    """
    Returns a LangChain embeddings model.

    The returned object is always a BaseEmbeddings — compatible with
    all LangChain vector stores.
    """
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "local":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
        )

    elif provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
        )

    else:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER: '{provider}'. "
            f"Supported: local, openai, gemini"
        )

from app.agent.llm.base import LLMClient, RetryingLLMClient
from app.agent.llm.fake import FakeLLMClient
from app.core.config import Settings


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_mode == "fake":
        return FakeLLMClient()

    # Imported lazily so fake mode (tests, CI, demo) never loads the provider SDK.
    from app.agent.llm.gemini import GeminiClient

    if settings.gemini_api_key is None:  # also enforced by Settings validation
        raise ValueError("GEMINI_API_KEY is required when LLM_MODE=live")
    gemini = GeminiClient(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.gemini_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    return RetryingLLMClient(gemini, max_attempts=settings.llm_max_attempts)

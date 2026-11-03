"""Gemini adapters (generation and embeddings). The only module that imports the Google SDK."""

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.agent.llm.base import (
    LLMError,
    LLMRateLimitError,
    LLMRequestError,
    LLMResponse,
    LLMRetryableError,
    LLMTimeoutError,
)


class GeminiClient:
    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self._model = model
        self._client = genai.Client(
            api_key=api_key,
            # Retries are handled by RetryingLLMClient, so they are visible and testable.
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )

    @property
    def model_name(self) -> str:
        return self._model

    def generate_structured(
        self, *, system_instruction: str, prompt: str, response_schema: type[BaseModel]
    ) -> LLMResponse:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_json_schema=response_schema.model_json_schema(),
            temperature=0.2,
        )
        try:
            response = self._client.models.generate_content(
                model=self._model, contents=prompt, config=config
            )
        except errors.APIError as exc:
            raise _map_api_error(exc) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Gemini isteği zaman aşımına uğradı") from exc
        except httpx.TransportError as exc:
            raise LLMRetryableError("Gemini'ye ulaşılamadı") from exc

        if not response.text:
            raise LLMRequestError("Gemini metin döndürmedi (güvenlik filtresine takılmış olabilir)")
        usage = response.usage_metadata
        return LLMResponse(
            text=response.text,
            model=self._model,
            input_tokens=usage.prompt_token_count if usage else None,
            output_tokens=usage.candidates_token_count if usage else None,
        )


class GeminiEmbedder:
    """Embeddings for policy retrieval (ADR-014). Documents and queries use different task
    types, which Gemini tunes separately."""

    def __init__(
        self, *, api_key: str, model: str, dimensions: int, timeout_seconds: float
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000))
        )

    @property
    def model_name(self) -> str:
        return f"{self._model}@{self._dimensions}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        config = types.EmbedContentConfig(
            task_type=task_type, output_dimensionality=self._dimensions
        )
        # One Content per text: gemini-embedding-2 is multimodal and would embed a plain
        # list of strings as the parts of a single content (one vector for all of them).
        contents = [types.Content(parts=[types.Part(text=text)]) for text in texts]
        try:
            response = self._client.models.embed_content(
                model=self._model, contents=contents, config=config
            )
        except errors.APIError as exc:
            raise _map_api_error(exc) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Gemini isteği zaman aşımına uğradı") from exc
        except httpx.TransportError as exc:
            raise LLMRetryableError("Gemini'ye ulaşılamadı") from exc
        vectors = [list(e.values or []) for e in (response.embeddings or [])]
        if len(vectors) != len(texts) or any(len(v) != self._dimensions for v in vectors):
            raise LLMRequestError("Gemini beklenen boyutta embedding döndürmedi")
        return vectors


def _map_api_error(exc: errors.APIError) -> LLMError:
    if exc.code == 429:
        return LLMRateLimitError("Gemini istek sınırı ya da kotası aşıldı")
    if exc.code in (408, 504):
        return LLMTimeoutError(f"Gemini zaman aşımı ({exc.code})")
    if isinstance(exc, errors.ServerError):
        return LLMRetryableError(f"Gemini sunucu hatası ({exc.code})")
    # Never include the provider message verbatim: it can echo request content.
    return LLMRequestError(f"Gemini isteği reddetti ({exc.code})")

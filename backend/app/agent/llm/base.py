"""Provider-independent LLM interface (ADR-009).

Nothing outside `app/agent/llm/` knows which provider is used. Adapters map
provider errors to the exceptions below, so retry and failure handling are
written once.
"""

import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    text: str  # raw model output; callers validate it, it is never trusted as-is
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMClient(Protocol):
    @property
    def model_name(self) -> str: ...

    def generate_structured(
        self, *, system_instruction: str, prompt: str, response_schema: type[BaseModel]
    ) -> LLMResponse:
        """Ask for JSON matching `response_schema`. Raises LLMError subclasses."""
        ...


class LLMError(Exception):
    """Base class; `code` is a stable, client-safe identifier stored on the run."""

    code = "llm_error"


class LLMRetryableError(LLMError):
    """Transient: rate limit, timeout, provider unavailable."""

    code = "llm_unavailable"


class LLMRateLimitError(LLMRetryableError):
    code = "llm_rate_limited"


class LLMTimeoutError(LLMRetryableError):
    code = "llm_timeout"


class LLMRequestError(LLMError):
    """Permanent: bad request, auth failure, blocked content. Retrying will not help."""

    code = "llm_request_failed"


class RetryingLLMClient:
    """Retries transient failures with exponential backoff and jitter."""

    def __init__(
        self,
        inner: LLMClient,
        *,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.inner = inner
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.sleep = sleep

    @property
    def model_name(self) -> str:
        return self.inner.model_name

    def generate_structured(
        self, *, system_instruction: str, prompt: str, response_schema: type[BaseModel]
    ) -> LLMResponse:
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.inner.generate_structured(
                    system_instruction=system_instruction,
                    prompt=prompt,
                    response_schema=response_schema,
                )
            except LLMRetryableError as exc:
                if attempt == self.max_attempts:
                    raise
                delay = self.base_delay_seconds * 2 ** (attempt - 1)
                delay += random.uniform(0, delay / 2)  # noqa: S311 - jitter, not security
                logger.warning(
                    "LLM call failed (%s), retry %d/%d in %.1fs",
                    exc.code,
                    attempt,
                    self.max_attempts - 1,
                    delay,
                )
                self.sleep(delay)
        raise AssertionError("unreachable")  # pragma: no cover

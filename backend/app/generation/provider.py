import importlib
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class GroundedPrompt:
    """System and user prompts sent to an answer provider."""

    system: str
    user: str


@dataclass(frozen=True)
class ProviderCompletion:
    """Raw completion returned by an answer provider."""

    text: str
    provider: str
    model: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    fallback_reason: str | None = None


class AnswerProvider(Protocol):
    """Interface for answer generation providers."""

    async def generate(
        self,
        prompt: GroundedPrompt,
        fallback_answer: str,
    ) -> ProviderCompletion:
        """Generate an answer from a grounded prompt."""


class DisabledAnswerProvider:
    """Deterministic answer provider used by default for local development and tests."""

    async def generate(
        self,
        prompt: GroundedPrompt,
        fallback_answer: str,
    ) -> ProviderCompletion:
        """Return the deterministic fallback answer without external calls."""
        settings = get_settings()
        return ProviderCompletion(
            text=fallback_answer,
            provider="disabled",
            model=settings.openai_model,
            fallback_reason="llm_provider_disabled",
        )


class OpenAIAnswerProvider:
    """OpenAI-backed answer provider for GPT-4o synthesis."""

    async def generate(
        self,
        prompt: GroundedPrompt,
        fallback_answer: str,
    ) -> ProviderCompletion:
        """Generate a grounded answer with GPT-4o, falling back safely on errors."""
        settings = get_settings()
        if not settings.openai_api_key:
            logger.info("OpenAI answer generation disabled because OPENAI_API_KEY is missing")
            return ProviderCompletion(
                text=fallback_answer,
                provider="disabled",
                model=settings.openai_model,
                fallback_reason="missing_openai_api_key",
            )

        try:
            openai_module: Any = importlib.import_module("openai")
            client = openai_module.AsyncOpenAI(api_key=settings.openai_api_key)
            response: Any = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": prompt.system},
                    {"role": "user", "content": prompt.user},
                ],
                temperature=0.0,
                max_tokens=700,
            )
        except Exception as error:
            logger.warning("OpenAI answer generation failed", extra={"error": str(error)})
            return ProviderCompletion(
                text=fallback_answer,
                provider="disabled",
                model=settings.openai_model,
                fallback_reason="openai_generation_failed",
            )

        text = str(response.choices[0].message.content or "").strip()
        if not text:
            return ProviderCompletion(
                text=fallback_answer,
                provider="disabled",
                model=settings.openai_model,
                fallback_reason="empty_openai_response",
            )

        usage = getattr(response, "usage", None)
        total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
        return ProviderCompletion(
            text=text,
            provider="openai",
            model=settings.openai_model,
            tokens_used=total_tokens,
        )


def get_generation_provider() -> AnswerProvider:
    """Return the configured answer provider."""
    settings = get_settings()
    if settings.llm_provider.lower() == "openai":
        return OpenAIAnswerProvider()
    return DisabledAnswerProvider()

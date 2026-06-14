"""Pricing catalog for all supported models.

Rates are in USD per token. The catalog is loaded from the routing.yaml
configuration at startup and can be updated without redeployment.

Author: Farruh
"""

from __future__ import annotations

from typing import Dict, Tuple


# Default pricing table (USD per token)
# Format: (provider, model) -> (input_rate, output_rate)
DEFAULT_PRICING: Dict[Tuple[str, str], Tuple[float, float]] = {
    # OpenAI
    ("openai", "gpt-4o"):                    (0.000005,   0.000015),
    ("openai", "gpt-4o-mini"):               (0.00000015, 0.00000060),
    ("openai", "gpt-4-turbo"):               (0.00001,    0.00003),
    ("openai", "gpt-4"):                     (0.00003,    0.00006),
    ("openai", "gpt-3.5-turbo"):             (0.0000005,  0.0000015),
    ("openai", "text-embedding-3-small"):    (0.00000002, 0.0),
    ("openai", "text-embedding-3-large"):    (0.00000013, 0.0),
    # Anthropic
    ("anthropic", "claude-3-5-sonnet-20241022"): (0.000003,  0.000015),
    ("anthropic", "claude-3-5-haiku-20241022"):  (0.0000008, 0.000004),
    ("anthropic", "claude-3-opus-20240229"):     (0.000015,  0.000075),
    ("anthropic", "claude-3-haiku-20240307"):    (0.00000025, 0.00000125),
    # Google
    ("google", "gemini-1.5-pro"):            (0.0000035, 0.0000105),
    ("google", "gemini-1.5-flash"):          (0.00000035, 0.00000105),
    # Mistral
    ("mistral", "mistral-large-latest"):     (0.000002, 0.000006),
    ("mistral", "mistral-small-latest"):     (0.0000002, 0.0000006),
}

_FALLBACK_RATE = (0.000001, 0.000002)


class PricingCatalog:
    """Calculates provider costs and applies platform markup."""

    def __init__(self, markup: float = 0.055) -> None:
        self._pricing = dict(DEFAULT_PRICING)
        self._markup = markup

    def calculate(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cached_tokens: int = 0,
    ) -> dict:
        """Calculate the full cost breakdown for a generation.

        Args:
            provider: Provider name (e.g. ``"openai"``).
            model: Model name (e.g. ``"gpt-4o"``).
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.
            cached_tokens: Number of tokens served from provider cache
                (Phase 3 — Task 3.2: these are billed at a discount).

        Returns:
            A dict with ``prompt_cost_usd``, ``completion_cost_usd``,
            ``cache_discount_usd``, ``total_cost_usd``, ``markup_usd``,
            and ``billed_usd``.
        """
        input_rate, output_rate = self._pricing.get(
            (provider, model), _FALLBACK_RATE
        )

        # Cached tokens are typically billed at 50% of the input rate
        non_cached_tokens = max(0, prompt_tokens - cached_tokens)
        prompt_cost = non_cached_tokens * input_rate
        cache_cost = cached_tokens * input_rate * 0.5
        cache_discount = cached_tokens * input_rate * 0.5  # savings vs full price
        completion_cost = completion_tokens * output_rate

        total_cost = prompt_cost + cache_cost + completion_cost
        markup = round(total_cost * self._markup, 8)
        billed = round(total_cost + markup, 8)

        return {
            "prompt_cost_usd": round(prompt_cost, 8),
            "completion_cost_usd": round(completion_cost, 8),
            "cache_discount_usd": round(cache_discount, 8),
            "total_cost_usd": round(total_cost, 8),
            "markup_usd": markup,
            "billed_usd": billed,
        }

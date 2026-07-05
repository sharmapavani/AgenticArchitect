"""Estimated model pricing for cost metrics (USD per 1M tokens)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

_DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    "gpt-4o": {"input_per_1m": 2.50, "output_per_1m": 10.00},
    "gpt-5-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    "text-embedding-3-small": {"input_per_1m": 0.02, "output_per_1m": 0.0},
    "text-embedding-3-large": {"input_per_1m": 0.13, "output_per_1m": 0.0},
}


@dataclass(frozen=True)
class ModelPricing:
    input_per_1m: float
    output_per_1m: float


def _load_pricing_table() -> dict[str, ModelPricing]:
    raw = os.getenv("METRICS_PRICING_JSON")
    source = _DEFAULT_PRICING if not raw else json.loads(raw)
    return {
        model: ModelPricing(
            input_per_1m=float(rates.get("input_per_1m", 0.0)),
            output_per_1m=float(rates.get("output_per_1m", 0.0)),
        )
        for model, rates in source.items()
    }


_PRICING = _load_pricing_table()


def compute_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost from token counts and model pricing table."""
    pricing = _PRICING.get(model)
    if pricing is None:
        # Fuzzy match on model family prefix
        for key, rates in _PRICING.items():
            if model.startswith(key.split("-")[0]):
                pricing = rates
                break
    if pricing is None:
        return 0.0
    input_cost = (input_tokens / 1_000_000) * pricing.input_per_1m
    output_cost = (output_tokens / 1_000_000) * pricing.output_per_1m
    return round(input_cost + output_cost, 6)

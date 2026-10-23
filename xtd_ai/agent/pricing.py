"""Cost estimation from a price table (USD per million tokens)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .types import Usage

CACHE_WRITE_FACTOR = 1.25


@dataclass(frozen=True)
class ModelPrice:
    input: float
    output: float
    cache_read: float | None = None  # default: 0.1 x input
    cache_write: float | None = None  # default: 1.25 x input

    def effective_cache_read(self) -> float:
        return self.cache_read if self.cache_read is not None else self.input * 0.1

    def effective_cache_write(self) -> float:
        return (
            self.cache_write
            if self.cache_write is not None
            else self.input * CACHE_WRITE_FACTOR
        )


# USD per million tokens (editable in Settings). cache_read None -> 0.1 x input;
# cache_write None -> 1.25 x input.
DEFAULT_PRICES: dict[str, ModelPrice] = {
    "claude-haiku-5-5": ModelPrice(input=0.10, output=0.50),
    "claude-sonnet-5-5": ModelPrice(input=2.00, output=10.00, cache_read=0.20),
    "claude-opus-5-5": ModelPrice(input=4.00, output=20.00, cache_read=0.20),
}


def parse_price_table(data: Mapping[str, Mapping]) -> dict[str, ModelPrice]:
    """Build a price table from ``{model: {input, output, cache_read?, cache_write?}}``.

    :raises: ``ValueError`` on malformed entries.
    """
    prices = {}
    for model, p in data.items():
        try:
            prices[model] = ModelPrice(
                input=float(p["input"]),
                output=float(p["output"]),
                cache_read=None
                if p.get("cache_read") is None
                else float(p["cache_read"]),
                cache_write=None
                if p.get("cache_write") is None
                else float(p["cache_write"]),
            )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ValueError(f"invalid price entry for {model!r}") from exc
    return prices


def lookup(prices: Mapping[str, ModelPrice], model: str) -> ModelPrice | None:
    if model in prices:
        return prices[model]
    # tolerate dated suffixes: longest matching prefix wins
    best = None
    for key in prices:
        if model.startswith(key) and (best is None or len(key) > len(best)):
            best = key
    return prices[best] if best else None


def estimate_cost(prices: Mapping[str, ModelPrice], model: str, usage: Usage) -> float:
    price = lookup(prices, model)
    if price is None:
        return 0.0
    total = (
        usage.input_tokens * price.input
        + usage.output_tokens * price.output
        + usage.cache_read_tokens * price.effective_cache_read()
        + usage.cache_write_tokens * price.effective_cache_write()
    )
    return round(total / 1_000_000, 6)

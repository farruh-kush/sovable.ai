from billing.pricing.catalog import PricingCatalog

def test_known_model_cost_and_markup() -> None:
    result = PricingCatalog(markup=0.10).calculate("openai", "gpt-4o-mini", 1000, 500)
    assert result["total_cost_usd"] == 0.00045
    assert result["markup_usd"] == 0.000045
    assert result["billed_usd"] == 0.000495

def test_cached_input_is_discounted_at_half_rate() -> None:
    result = PricingCatalog(markup=0.0).calculate("mistral", "mistral-small-latest", 1000, 0, cached_tokens=400)
    assert result["prompt_cost_usd"] == 0.00012
    assert result["cache_discount_usd"] == 0.00004
    assert result["total_cost_usd"] == 0.00016

def test_unknown_models_use_safe_fallback_rate() -> None:
    result = PricingCatalog(markup=0.0).calculate("unknown", "unknown", 100, 50)
    assert result["total_cost_usd"] == 0.0002

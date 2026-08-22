from ai_routing_shared.models import ApiKey, ApiKeyTier
from ai_routing_shared.utils import generate_api_key, hash_api_key

def test_generated_key_has_prefix_and_is_not_reused() -> None:
    first = generate_api_key()
    second = generate_api_key()
    assert first.startswith("sk-")
    assert len(first) > 40
    assert first != second

def test_hash_is_deterministic_and_one_way_shape() -> None:
    raw = "sk-test-value"
    assert hash_api_key(raw) == hash_api_key(raw)
    assert len(hash_api_key(raw)) == 64
    assert raw not in hash_api_key(raw)

def test_api_key_principal_preserves_limits_and_allowlist() -> None:
    principal = ApiKey(id="key_1", user_id="user_1", tier=ApiKeyTier.PRO, requests_per_minute=100, allowed_models=["gpt-4o-mini"])
    assert principal.tier is ApiKeyTier.PRO
    assert principal.requests_per_minute == 100
    assert principal.allowed_models == ["gpt-4o-mini"]

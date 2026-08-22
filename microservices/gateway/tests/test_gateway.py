import pytest
from ai_routing_shared.exceptions import ModelNotAllowedError
from ai_routing_shared.models import ApiKey, ChatCompletionRequest, ChatMessage
from gateway.api.v1.chat import _compute_cache_key
from gateway.core.auth import enforce_model_whitelist

def request() -> ChatCompletionRequest:
    return ChatCompletionRequest(model="gpt-4o-mini", messages=[ChatMessage(role="user", content="hello")])

def test_cache_key_is_deterministic_and_changes_with_prompt() -> None:
    first = _compute_cache_key(request())
    second = _compute_cache_key(request())
    changed = _compute_cache_key(request().model_copy(update={"messages": [ChatMessage(role="user", content="different")]}))
    assert first == second
    assert first != changed

def test_model_whitelist_allows_configured_model() -> None:
    principal = ApiKey(id="key_1", user_id="user_1", allowed_models=["gpt-4o-mini"])
    enforce_model_whitelist("gpt-4o-mini", principal)

def test_model_whitelist_rejects_unconfigured_model() -> None:
    principal = ApiKey(id="key_1", user_id="user_1", allowed_models=["gpt-4o-mini"])
    with pytest.raises(ModelNotAllowedError):
        enforce_model_whitelist("gpt-4o", principal)

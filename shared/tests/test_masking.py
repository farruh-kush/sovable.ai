from ai_routing_shared.models import ChatMessage
from ai_routing_shared.privacy import mask_chat_messages

def test_masking_replaces_common_sensitive_values_and_restores() -> None:
    messages = [ChatMessage(role="user", content="Email me at test@example.com or call +998 90 123 45 67.")]
    masked, session = mask_chat_messages(messages)
    masked_text = masked[0].content
    assert "test@example.com" not in masked_text
    assert "+998 90 123 45 67" not in masked_text
    assert session.restore_text(masked_text) == messages[0].content

def test_masking_keeps_non_text_content_unchanged() -> None:
    content = [{"type": "text", "text": "hello"}]
    messages = [ChatMessage(role="user", content=content)]
    masked, session = mask_chat_messages(messages)
    assert masked[0].content == content
    assert session.mapping == {}

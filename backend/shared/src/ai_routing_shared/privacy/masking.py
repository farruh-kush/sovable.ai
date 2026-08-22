"""Request-local masking for common sensitive text patterns. Author: Farruh"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from ai_routing_shared.models import ChatMessage

_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE", re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")),
    ("CARD", re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")),
    ("UZ_ID", re.compile(r"\b\d{9,14}\b")),
)

@dataclass
class MaskingSession:
    mapping: Dict[str, str] = field(default_factory=dict)
    _counter: int = 0

    def _token(self, label: str, value: str) -> str:
        self._counter += 1
        token = f"<PII_{label}_{self._counter}>"
        self.mapping[token] = value
        return token

    def mask_text(self, text: str) -> str:
        masked = text
        for label, pattern in _PATTERNS:
            masked = pattern.sub(lambda match: self._token(label, match.group(0)), masked)
        return masked

    def restore_text(self, text: str) -> str:
        restored = text
        for token, value in self.mapping.items():
            restored = restored.replace(token, value)
        return restored


def mask_chat_messages(messages: List[ChatMessage]) -> tuple[List[ChatMessage], MaskingSession]:
    session = MaskingSession()
    masked: List[ChatMessage] = []
    for message in messages:
        if isinstance(message.content, str):
            masked.append(message.model_copy(update={"content": session.mask_text(message.content)}))
        else:
            masked.append(message)
    return masked, session

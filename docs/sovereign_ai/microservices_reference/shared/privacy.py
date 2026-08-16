from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Entity:
    entity_type: str
    start: int
    end: int
    score: float


class PrivacyEngine:
    """Deterministic MVP privacy engine.

    The mapping is request-local in this reference implementation. Production use
    requires a tenant-scoped encrypted vault backed by KMS/HSM and audited access.
    """

    PATTERNS: tuple[tuple[str, str, float], ...] = (
        ("EMAIL", r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w-])", 0.99),
        ("PINFL", r"(?<!\d)\d{14}(?!\d)", 0.98),
        ("CARD", r"(?<!\d)(?:\d[ -]?){16}(?!\d)", 0.97),
        ("UZ_PASSPORT", r"(?<![A-Za-z])(?:[A-Z]{2}\s?\d{7})(?!\d)", 0.96),
        ("PHONE", r"(?<!\w)(?:\+998[ -]?)?\d{2}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}(?!\w)", 0.93),
        ("SECRET", r"(?i)(?<!\w)(?:api[_ -]?key|secret|password|token)\s*[:=]\s*[^\s,;]+", 0.99),
    )

    def detect(self, text: str) -> list[Entity]:
        found: list[Entity] = []
        for entity_type, pattern, score in self.PATTERNS:
            for match in re.finditer(pattern, text):
                found.append(Entity(entity_type, match.start(), match.end(), score))
        accepted: list[Entity] = []
        for candidate in sorted(found, key=lambda item: (item.start, -item.score, -(item.end - item.start))):
            if any(candidate.start < item.end and item.start < candidate.end for item in accepted):
                continue
            accepted.append(candidate)
        return sorted(accepted, key=lambda item: item.start)

    def mask_text(self, text: str) -> tuple[str, dict[str, str], list[Entity]]:
        entities = self.detect(text)
        mapping: dict[str, str] = {}
        counters: dict[str, int] = {}
        parts: list[str] = []
        cursor = 0
        for entity in entities:
            parts.append(text[cursor : entity.start])
            counters[entity.entity_type] = counters.get(entity.entity_type, 0) + 1
            token = f"<{entity.entity_type}_{counters[entity.entity_type]}>"
            mapping[token] = text[entity.start : entity.end]
            parts.append(token)
            cursor = entity.end
        parts.append(text[cursor:])
        return "".join(parts), mapping, entities

    @staticmethod
    def restore_text(text: str, mapping: dict[str, str]) -> str:
        restored = text
        for token in sorted(mapping, key=len, reverse=True):
            restored = restored.replace(token, mapping[token])
        return restored

    def mask_messages(self, messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str], list[Entity]]:
        masked = copy.deepcopy(messages)
        mapping: dict[str, str] = {}
        entities: list[Entity] = []
        for message in masked:
            content = message.get("content")
            if isinstance(content, str):
                new_content, local_mapping, local_entities = self.mask_text(content)
                message["content"] = new_content
                mapping.update(local_mapping)
                entities.extend(local_entities)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                        new_text, local_mapping, local_entities = self.mask_text(part["text"])
                        part["text"] = new_text
                        mapping.update(local_mapping)
                        entities.extend(local_entities)
        return masked, mapping, entities

    def restore_payload(self, payload: Any, mapping: dict[str, str]) -> Any:
        if isinstance(payload, str):
            return self.restore_text(payload, mapping)
        if isinstance(payload, list):
            return [self.restore_payload(item, mapping) for item in payload]
        if isinstance(payload, dict):
            return {key: self.restore_payload(value, mapping) for key, value in payload.items()}
        return payload

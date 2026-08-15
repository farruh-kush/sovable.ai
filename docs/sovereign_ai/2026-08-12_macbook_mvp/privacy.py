from __future__ import annotations

import copy
import os
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
    """Small, testable privacy boundary for the MacBook MVP.

    The deterministic recognizers make the tutorial runnable without downloading a
    language model. Set USE_PRESIDIO=true after installing Presidio and a compatible
    NLP model to add optional NER/context-aware detection.
    """

    PATTERNS: tuple[tuple[str, str, float], ...] = (
        ("EMAIL", r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w-])", 0.99),
        ("PINFL", r"(?<!\d)\d{14}(?!\d)", 0.98),
        ("CARD", r"(?<!\d)(?:\d[ -]?){16}(?!\d)", 0.97),
        ("UZ_PASSPORT", r"(?<![A-Za-z])(?:[A-Z]{2}\s?\d{7})(?!\d)", 0.96),
        ("PHONE", r"(?<!\w)(?:\+998[ -]?)?\d{2}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}(?!\w)", 0.93),
        ("TIN", r"(?i)(?<!\w)(?:TIN|STIR|INN)\s*[:#-]?\s*\d{9}(?!\d)", 0.95),
        ("SECRET", r"(?i)(?<!\w)(?:api[_ -]?key|secret|password|token)\s*[:=]\s*[^\s,;]+", 0.99),
    )

    def __init__(self, use_presidio: bool | None = None) -> None:
        self.use_presidio = (
            os.getenv("USE_PRESIDIO", "false").lower() in {"1", "true", "yes"}
            if use_presidio is None
            else use_presidio
        )
        self._presidio = None
        if self.use_presidio:
            try:
                from presidio_analyzer import AnalyzerEngine

                self._presidio = AnalyzerEngine()
            except Exception as exc:  # pragma: no cover - depends on optional local NLP setup
                raise RuntimeError(
                    "USE_PRESIDIO=true but Presidio/NLP setup failed. "
                    "Install the optional dependencies or set USE_PRESIDIO=false."
                ) from exc

    def _regex_entities(self, text: str) -> list[Entity]:
        entities: list[Entity] = []
        for entity_type, pattern, score in self.PATTERNS:
            for match in re.finditer(pattern, text):
                entities.append(Entity(entity_type, match.start(), match.end(), score))
        return entities

    def _presidio_entities(self, text: str) -> list[Entity]:
        if self._presidio is None:
            return []
        try:
            results = self._presidio.analyze(text=text, language="en")
        except Exception:
            return []
        return [Entity(r.entity_type, r.start, r.end, float(r.score)) for r in results]

    @staticmethod
    def _merge_entities(entities: list[Entity]) -> list[Entity]:
        # Prefer the highest-confidence, longest span when recognizers overlap.
        ordered = sorted(
            entities,
            key=lambda e: (e.start, -e.score, -(e.end - e.start)),
        )
        accepted: list[Entity] = []
        for candidate in ordered:
            if any(candidate.start < item.end and item.start < candidate.end for item in accepted):
                continue
            accepted.append(candidate)
        return sorted(accepted, key=lambda e: e.start)

    def detect(self, text: str) -> list[Entity]:
        return self._merge_entities(self._regex_entities(text) + self._presidio_entities(text))

    def mask_text(self, text: str) -> tuple[str, dict[str, str], list[Entity]]:
        entities = self.detect(text)
        mapping: dict[str, str] = {}
        pieces: list[str] = []
        cursor = 0
        counters: dict[str, int] = {}
        for entity in entities:
            pieces.append(text[cursor : entity.start])
            counters[entity.entity_type] = counters.get(entity.entity_type, 0) + 1
            token = f"<{entity.entity_type}_{counters[entity.entity_type]}>"
            mapping[token] = text[entity.start : entity.end]
            pieces.append(token)
            cursor = entity.end
        pieces.append(text[cursor:])
        return "".join(pieces), mapping, entities

    @staticmethod
    def restore_text(text: str, mapping: dict[str, str]) -> str:
        restored = text
        for token in sorted(mapping, key=len, reverse=True):
            restored = restored.replace(token, mapping[token])
        return restored

    def mask_messages(self, messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str], list[Entity]]:
        masked_messages = copy.deepcopy(messages)
        mapping: dict[str, str] = {}
        all_entities: list[Entity] = []
        for message in masked_messages:
            content = message.get("content")
            if isinstance(content, str):
                masked, local_mapping, entities = self.mask_text(content)
                message["content"] = masked
                mapping.update(local_mapping)
                all_entities.extend(entities)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                        masked, local_mapping, entities = self.mask_text(part["text"])
                        part["text"] = masked
                        mapping.update(local_mapping)
                        all_entities.extend(entities)
        return masked_messages, mapping, all_entities

    def restore_payload(self, payload: Any, mapping: dict[str, str]) -> Any:
        if isinstance(payload, str):
            return self.restore_text(payload, mapping)
        if isinstance(payload, list):
            return [self.restore_payload(item, mapping) for item in payload]
        if isinstance(payload, dict):
            return {key: self.restore_payload(value, mapping) for key, value in payload.items()}
        return payload

    def inspect(self, text: str) -> dict[str, Any]:
        masked, _, entities = self.mask_text(text)
        return {
            "masked_text": masked,
            "entities": [
                {
                    "type": entity.entity_type,
                    "start": entity.start,
                    "end": entity.end,
                    "score": entity.score,
                }
                for entity in entities
            ],
            "presidio_enabled": self._presidio is not None,
        }

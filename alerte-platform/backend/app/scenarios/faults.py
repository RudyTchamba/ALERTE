"""Catalogue des modes de panne (15) : les 12 types de défaillance de la Spec + 3 pannes d'exercice."""
from __future__ import annotations

FAULT_MODES: list[dict[str, str]] = [
    {"code": "false_alarm", "origin": "spec", "label": "False alarm", "description": "An alert is issued although no hazard materialises."},
    {"code": "missed_event", "origin": "spec", "label": "Missed event", "description": "A real hazard is not detected or not warned."},
    {"code": "bad_input_data", "origin": "spec", "label": "Bad input data", "description": "The AI system works from wrong or corrupted data."},
    {"code": "wrong_area", "origin": "spec", "label": "Wrong area", "description": "The alert targets the wrong geographic area."},
    {"code": "language_error", "origin": "spec", "label": "Language error", "description": "The message is wrong or unreadable in the audience's language."},
    {"code": "exclusion", "origin": "spec", "label": "Exclusion", "description": "Some groups (disabled, remote, unconnected) are not reached."},
    {"code": "fabricated_content", "origin": "spec", "label": "Fabricated content", "description": "The system invents facts, sources or numbers."},
    {"code": "spoofing", "origin": "spec", "label": "Spoofing", "description": "A fake sender or channel is used to push an alert."},
    {"code": "over_trust", "origin": "spec", "label": "Over-trust", "description": "The AI output is asserted with too much confidence or acted on unreviewed."},
    {"code": "privacy_breach", "origin": "spec", "label": "Privacy breach", "description": "Personal data is accessed or disclosed without basis."},
    {"code": "data_leaves_country", "origin": "spec", "label": "Data leaves the country", "description": "Data is processed or stored abroad."},
    {"code": "model_drift", "origin": "spec", "label": "Model drift", "description": "The model's quality degrades over time without detection."},
    {"code": "degraded_inputs", "origin": "exercise", "label": "Degraded inputs", "description": "Sensors or feeds are offline or degraded."},
    {"code": "silent_institution", "origin": "exercise", "label": "Silent institution", "description": "A seat does not respond."},
    {"code": "llm_outage", "origin": "exercise", "label": "LLM outage", "description": "The model provider fails for one round (agents fall back)."},
]
FAULT_CODES: frozenset[str] = frozenset(f["code"] for f in FAULT_MODES)
VALID_FAULT_MODES: frozenset[str] = FAULT_CODES | {"none"}
MIN_FAULT_MODES = 6

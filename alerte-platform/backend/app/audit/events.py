"""Catalogue des événements du ledger (contrat central entre moteur, SSE, gaps et rapports — doc 10 §10.2)."""
from __future__ import annotations


class EventType:
    SNAPSHOT = "SNAPSHOT"
    STATE = "STATE"
    INJECT = "INJECT"
    SEAT = "SEAT"
    RETRIEVAL = "RETRIEVAL"
    LLM_CALL = "LLM_CALL"
    TOOL_CALL = "TOOL_CALL"
    BOARD = "BOARD"
    DECISION = "DECISION"
    CITATION_CHECK = "CITATION_CHECK"
    GAP = "GAP"
    HUMAN = "HUMAN"
    FACILITATOR = "FACILITATOR"
    CORRECTION = "CORRECTION"
    ERROR = "ERROR"

    ALL = (SNAPSHOT, STATE, INJECT, SEAT, RETRIEVAL, LLM_CALL, TOOL_CALL, BOARD, DECISION, CITATION_CHECK,
           GAP, HUMAN, FACILITATOR, CORRECTION, ERROR)


class Visibility:
    PUBLIC = "public"   # tous les rôles, y compris observateur « public seulement »
    BOARD = "board"     # sièges, animateur, auditeur, observateur « tout »
    SEAT = "seat"       # ce siège (+ animateur/auditeur) — `seat_id` renseigné
    AUDIT = "audit"     # animateur et auditeur seulement

    ALL = (PUBLIC, BOARD, SEAT, AUDIT)


# Clés retirées de la projection stable du rejeu (non déterministes d'une exécution à l'autre)
NON_DETERMINISTIC_KEYS = frozenset({"ms", "latency_ms", "duration_ms", "real_time", "started_at", "finished_at",
                                    "created_at", "endpoint"})

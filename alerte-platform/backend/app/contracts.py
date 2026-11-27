"""Contrats communs entre modules (ports et objets de valeur).

Règle d'architecture : un module ne dépend que des modules autorisés (doc 05 §5.3). Ce fichier définit les
interfaces partagées pour que les modules se développent en parallèle sans se connaître :

* `SearchScope` / `Hit` / `SearchService` : recherche hybride à portée contrainte (knowledge → agents).
* `Embedder`, `VectorIndex`, `LexicalIndex` : ports du RAG hybride (fournisseurs interchangeables).
* `LLMProvider` : port du modèle de génération.
* `LedgerPort` : écriture d'événements d'audit (audit → simulation/agents/gaps).
* `GapHook` : point d'extension appelé à la fin d'un inject (simulation → gaps, sans import direct).
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

# Nombre maximal de tours par inject (source UNIQUE : simulation, agents, estimation de budget). Un message posté au tour r est
# livré au tour r+1 ; au dernier tour on ne peut donc plus poster (rien ne le traiterait) : le tour N sert à DÉCIDER.
MAX_ROUNDS = 3

# --------------------------------------------------------------------------- recherche


@dataclass(frozen=True)
class SearchScope:
    """Portée de lecture d'un acteur. Construite UNIQUEMENT par le backend (jamais depuis un paramètre d'outil)."""

    workspace_id: str
    kb_ids: frozenset[str]
    document_version_ids: frozenset[str]
    purpose: Literal["agent", "human_seat", "analyst", "ui_preview", "eval"] = "agent"
    seat_id: str | None = None

    @property
    def is_empty(self) -> bool:
        return not self.kb_ids or not self.document_version_ids

    def scope_hash(self) -> str:
        import hashlib

        payload = "|".join([self.workspace_id, ",".join(sorted(self.kb_ids)),
                            ",".join(sorted(self.document_version_ids))])
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class SearchFilters:
    """Ne peuvent que RESTREINDRE la portée."""

    languages: frozenset[str] | None = None
    doc_types: frozenset[str] | None = None
    article: str | None = None


@dataclass
class Hit:
    chunk_id: str
    document_version_id: str
    kb_id: str
    doc_code: str
    doc_title: str
    article: str | None
    page: int | None
    text: str
    score: float
    signals: dict[str, Any] = field(default_factory=dict)  # {"lexical": rank, "dense": rank, "degraded": bool}
    snippet: str = ""


class SearchService(Protocol):
    def search(self, scope: SearchScope, query: str, k: int = 5, *, filters: SearchFilters | None = None) -> list[Hit]: ...


# --------------------------------------------------------------------------- embeddings / index


@dataclass(frozen=True)
class EmbedderFingerprint:
    """Empreinte COMPLÈTE : des vecteurs de runtimes différents ne sont pas comparables."""

    model: str
    revision: str = ""
    runtime: str = ""
    quantization: str = ""
    normalized: bool = True
    dimension: int = 0

    def key(self) -> str:
        import hashlib

        raw = "|".join([self.model, self.revision, self.runtime, self.quantization, str(self.normalized), str(self.dimension)])
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@runtime_checkable
class Embedder(Protocol):
    fingerprint: EmbedderFingerprint

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


@dataclass
class VectorRecord:
    chunk_id: str
    kb_id: str
    document_version_id: str
    vector: list[float]


class VectorIndex(Protocol):
    """Index vectoriel (ChromaDB par défaut ; NumPy exact pour les tests et la garde de rappel)."""

    def upsert(self, records: Sequence[VectorRecord]) -> None: ...
    def delete(self, chunk_ids: Sequence[str]) -> None: ...
    def query(self, vector: Sequence[float], scope: SearchScope, k: int) -> list[tuple[str, float]]: ...
    def reset(self) -> None: ...


class LexicalIndex(Protocol):
    def query(self, text: str, scope: SearchScope, k: int) -> list[tuple[str, float]]: ...


# --------------------------------------------------------------------------- LLM


@dataclass
class LLMMessage:
    role: Literal["system", "user", "assistant", "tool"]
    content: str


@dataclass
class RawCompletion:
    text: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0
    ms: int = 0
    request_sha256: str = ""
    response_sha256: str = ""
    endpoint: str = ""  # endpoint effectif (preuve de non-sortie de données)


class LLMProvider(Protocol):
    name: str            # "openai_compat" | "scripted" | "cassette"
    ai_involved: bool    # False pour `scripted` (jamais présenté comme un résultat d'agents IA)

    def complete(self, messages: Sequence[LLMMessage], *, schema: dict[str, Any] | None = None,
                 temperature: float = 0.0, max_tokens: int | None = None) -> RawCompletion: ...


# --------------------------------------------------------------------------- audit


class LedgerPort(Protocol):
    def append(self, session: Any, exercise_id: str, type: str, actor: str, payload: dict[str, Any], *,
               seat_id: str | None = None, sim_time: str | None = None, visibility: str = "audit") -> int: ...


# hook simulation → gaps : (session, exercise_id, inject_ref, closing: bool) -> None
GapHook = Callable[[Any, str, str, bool], None]


# --------------------------------------------------------------------------- runtime d'agents (agents → simulation)


@dataclass
class PostedMessage:
    to: str                       # code de siège destinataire
    msg_type: str                 # INFO|REQUEST|DECISION|OBJECTION|GAP_FLAG
    body: str
    in_reply_to: str | None = None
    reply_status: str | None = None   # accepted|refused|not_our_role


@dataclass
class ToolEvent:
    """Événement produit par le runtime ; la simulation l'écrit au ledger dans SA transaction (un seul écrivain)."""

    type: str                     # LLM_CALL|TOOL_CALL|RETRIEVAL|CITATION_CHECK|DECISION|ERROR
    payload: dict[str, Any]
    visibility: str = "audit"     # public|board|seat|audit


@dataclass
class SeatContext:
    """Tout ce dont le runtime a besoin pour une activation. Le `scope` est construit par la simulation."""

    exercise_id: str
    workspace_id: str
    seat_id: str
    seat_code: str
    institution: dict[str, Any]          # {id, code, name, kind}
    agent: dict[str, Any]                # snapshot de l'agent (mission, instructions, tools, limits, model profile…)
    scope: SearchScope
    inject: dict[str, Any]               # inject courant (snapshot)
    round: int
    inbox: list[dict[str, Any]]          # nouveaux éléments de la boîte privée
    board: list[dict[str, Any]]          # messages du tableau visibles du siège
    own_decisions: list[dict[str, Any]]  # décisions précédentes de CE siège
    mandates: list[dict[str, Any]]       # mandats validés de l'institution actifs dans l'exercice (avec sources)
    seat_codes: list[str]                # destinataires valides pour `post`
    step_key: str                        # clé d'idempotence de l'étape (inject:round:seat)
    # annuaire des AUTRES sièges activables : {code, name, kind, mission, mandates:["kind:action_code"]} (informations publiques de rôle,
    # jamais d'instructions privées ni de contenu de boîte) ; vide => le prompt retombe sur la seule liste de codes
    seat_directory: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ActivationResult:
    decision: dict[str, Any] | None = None       # payload DECISION (voir CONTRACTS.md)
    messages: list[PostedMessage] = field(default_factory=list)
    events: list[ToolEvent] = field(default_factory=list)
    llm_calls: int = 0
    status: str = "ok"                           # ok|fallback|not_recorded|budget_exhausted
    author: str = "agent"                        # agent|fallback


class AgentRuntimePort(Protocol):
    def activate(self, ctx: SeatContext) -> ActivationResult: ...

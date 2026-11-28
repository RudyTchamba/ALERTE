"""Enveloppe d'action plate, validation Pydantic en union discriminée côté serveur (doc 08 §8.3)."""
from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, field_validator, model_validator

from .providers import extract_json_text

MSG_TYPES = ("INFO", "REQUEST", "DECISION", "OBJECTION", "GAP_FLAG")
MAX_RATIONALE = 280


def _trunc(v: Any) -> Any:
    if isinstance(v, str) and len(v) > MAX_RATIONALE:
        return v[:MAX_RATIONALE - 1].rstrip() + "…"
    return v


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    rationale: str = Field(min_length=1)

    @field_validator("rationale", mode="before")
    @classmethod
    def _r(cls, v: Any) -> Any:
        return _trunc(v)


class LegalBasisItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    chunk_id: str = Field(min_length=1)
    article: str | None = None
    quote: str = Field(min_length=1)

    @field_validator("article", mode="before")
    @classmethod
    def _a(cls, v: Any) -> Any:
        return None if v is None else str(v)


class GapFlag(BaseModel):
    model_config = ConfigDict(extra="ignore")
    hint: str | None = None
    text: str = Field(min_length=1, max_length=500)


class Decision(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    action: str = Field(min_length=1, max_length=500)
    action_code: str | None = None
    outcome: Literal["act", "decline", "refer", "no_legal_basis_found"]
    legal_basis: list[LegalBasisItem] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]
    options_considered: list[str] = Field(default_factory=list)
    gap_flags: list[GapFlag] = Field(default_factory=list)
    evidence_tag: Literal["documented", "inferred", "assumed"]

    @model_validator(mode="after")
    def _basis(self) -> Decision:
        if self.outcome != "no_legal_basis_found" and not self.legal_basis:
            raise ValueError("legal_basis is required unless outcome is no_legal_basis_found. If no retrieved passage supports your decision, "
                             "set outcome to no_legal_basis_found and legal_basis to []: do not cite an unrelated passage")
        return self


class SearchAction(_Base):
    action: Literal["search_kb"]
    query: str = Field(min_length=1, max_length=300)


class AskLegalAction(_Base):
    action: Literal["ask_legal"]
    question: str = Field(min_length=1, max_length=500)


class PostAction(_Base):
    action: Literal["post"]
    to: str = Field(min_length=1, max_length=64)
    msg_type: Literal["INFO", "REQUEST", "DECISION", "OBJECTION", "GAP_FLAG"]
    message: str = Field(min_length=1, max_length=1500)
    in_reply_to: str | None = None
    reply_status: Literal["accepted", "refused", "not_our_role"] | None = None


class DecideAction(_Base):
    action: Literal["decide"]
    decision: Decision


Envelope = Annotated[SearchAction | AskLegalAction | PostAction | DecideAction, Field(discriminator="action")]
_ADAPTER: TypeAdapter[Any] = TypeAdapter(Envelope)


def envelope_schema(allowed: list[str]) -> dict[str, Any]:
    """Schéma JSON PLAT (sans oneOf) transmis au fournisseur ; la validation réelle reste côté serveur."""
    dec = {"type": "object", "properties": {
        "action": {"type": "string"}, "action_code": {"type": ["string", "null"]},
        "outcome": {"type": "string", "enum": ["act", "decline", "refer", "no_legal_basis_found"]},
        "legal_basis": {"type": "array", "items": {"type": "object", "properties": {
            "chunk_id": {"type": "string"}, "article": {"type": ["string", "null"]}, "quote": {"type": "string"}},
            "required": ["chunk_id", "article", "quote"]}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "options_considered": {"type": "array", "items": {"type": "string"}},
        "gap_flags": {"type": "array", "items": {"type": "object", "properties": {
            "hint": {"type": ["string", "null"]}, "text": {"type": "string"}}}},
        "evidence_tag": {"type": "string", "enum": ["documented", "inferred", "assumed"]}},
        "required": ["action", "outcome", "legal_basis", "confidence", "evidence_tag"]}
    return {"title": "AlerteActionEnvelope", "type": "object", "properties": {
        "action": {"type": "string", "enum": list(allowed)},
        "rationale": {"type": "string", "maxLength": MAX_RATIONALE},
        "query": {"type": "string"}, "question": {"type": "string"},
        "to": {"type": "string"}, "msg_type": {"type": "string", "enum": list(MSG_TYPES)},
        "message": {"type": "string"}, "in_reply_to": {"type": ["string", "null"]},
        "reply_status": {"type": ["string", "null"], "enum": ["accepted", "refused", "not_our_role", None]},
        "decision": dec}, "required": ["action", "rationale"]}


def format_errors(exc: ValidationError) -> str:
    parts = []
    for e in exc.errors()[:6]:
        loc = ".".join(str(x) for x in e["loc"] if x != "function-after[_basis(), Decision]")
        parts.append(f"{loc or 'envelope'}: {e['msg']}")
    return "; ".join(parts)


_NESTED = ("args", "arguments", "parameters", "params", "input")
_QUERY_ALIASES = ("q", "search", "search_query", "search_text", "keywords", "text", "question")
_QUESTION_ALIASES = ("query", "q", "text", "prompt")


def _first_text(data: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for k in keys:
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, list) and v and isinstance(v[0], str) and v[0].strip():
            return v[0].strip()
    return None


def normalize_envelope(data: dict[str, Any]) -> dict[str, Any]:
    """Tolère les variantes de NOM de champ les plus courantes d'un petit modèle (la requête sous « question », « q », « queries »,
    ou imbriquée dans « args ») : l'intention est claire, la rejeter coûte un appel au modèle. Ne devine jamais une VALEUR : si aucun
    texte n'est trouvé, la validation habituelle refuse l'action."""
    data = dict(data)
    for k in _NESTED:
        if isinstance(data.get(k), dict):
            for kk, v in data[k].items():
                data.setdefault(kk, v)
    act = data.get("action")
    if act == "search_kb" and not str(data.get("query") or "").strip():
        q = _first_text(data, _QUERY_ALIASES + ("queries",))
        if q:
            data["query"] = q[:300]
    elif act == "ask_legal" and not str(data.get("question") or "").strip():
        q = _first_text(data, _QUESTION_ALIASES)
        if q:
            data["question"] = q[:500]
    return data


def parse_envelope(text: str) -> tuple[SearchAction | AskLegalAction | PostAction | DecideAction | None, str | None]:
    """(action validée, None) ou (None, message d'erreur à renvoyer au modèle)."""
    raw = extract_json_text(text or "")
    if raw is None:
        return None, "the reply is not valid JSON; answer with a single JSON object"
    try:
        data = json.loads(raw)
    except ValueError:
        return None, "the reply is not valid JSON"
    if not isinstance(data, dict):
        return None, "the reply must be a JSON object"
    if "action" not in data:
        return None, "action: field required (one of search_kb, ask_legal, post, decide)"
    try:
        return _ADAPTER.validate_python(normalize_envelope(data)), None
    except ValidationError as exc:
        return None, format_errors(exc)


# ----- conseiller juridique (§8.6)

class LegalClaim(BaseModel):
    model_config = ConfigDict(extra="ignore")
    claim: str = Field(min_length=1)
    cites: list[LegalBasisItem] = Field(default_factory=list)


class LegalGap(BaseModel):
    model_config = ConfigDict(extra="ignore")
    point: str = Field(min_length=1)
    searched_queries: list[str] = Field(default_factory=list)


class LegalPrecedent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    jurisdiction: str
    instrument: str
    summary: str
    cites: list[LegalBasisItem] = Field(default_factory=list)


class LegalAnswer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    what_the_texts_say: list[LegalClaim]
    what_they_do_not_say: list[LegalGap]
    what_others_do: list[LegalPrecedent]
    what_to_check: list[str]


LEGAL_SCHEMA: dict[str, Any] = {"title": "AlerteLegalAnswer", "type": "object", "properties": {
    "what_the_texts_say": {"type": "array"}, "what_they_do_not_say": {"type": "array"},
    "what_others_do": {"type": "array"}, "what_to_check": {"type": "array"}},
    "required": ["what_the_texts_say", "what_they_do_not_say", "what_others_do", "what_to_check"]}


def parse_legal(text: str) -> tuple[LegalAnswer | None, str | None]:
    raw = extract_json_text(text or "")
    if raw is None:
        return None, "the reply is not valid JSON"
    try:
        return LegalAnswer.model_validate_json(raw), None
    except ValidationError as exc:
        return None, format_errors(exc)

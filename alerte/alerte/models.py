"""Data models shared by every block (see design doc, section 2.3)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------
# Knowledge
# --------------------------------------------------------------------------

class Reliability(str, Enum):
    official = "official"      # official full text
    summary = "summary"        # reliable summary (law firm, IFRC, news) or team paraphrase
    fictional = "fictional"    # scenario material written by the team
    not_found = "not_found"    # listed but not obtained


class DocumentMeta(BaseModel):
    doc_id: str
    title: str
    country: str = "INT"                 # CM, AE, EU, PH, US, JP, MU, AU, INT ...
    doc_type: str = "report"             # law, decree, strategy, plan, report, standard, news, guidance, fictional
    language: str = "en"
    reliability: Reliability = Reliability.summary
    url: str = ""
    file: str = ""                       # path relative to data/docs
    collection: str = "GL"               # CM, AE, GL, ITU, SCN
    institutions: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    status: str = "current"              # current | replaced
    replaced_by: str = ""
    accessed: str = ""
    notes: str = ""


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    text: str
    article: str = ""
    country: str = "INT"
    doc_type: str = "report"
    language: str = "en"
    reliability: str = "summary"
    collection: str = "GL"
    institutions: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    url: str = ""
    status: str = "current"
    extraction: str = ""          # how the text was obtained: text-layer, OCR (with confidence), human-corrected...
    needs_review: bool = False    # the source file has pages a human should proofread


class SearchHit(BaseModel):
    chunk: Chunk
    score: float


# --------------------------------------------------------------------------
# Mandate map (who may or must do what)
# --------------------------------------------------------------------------

class ActionDef(BaseModel):
    code: str
    label: str
    label_fr: str = ""
    category: str = "coordination"   # coordination, alerting, liability, inclusion, ai_oversight, security, cross_border, data, health
    keywords: list[str] = Field(default_factory=list)
    conflicts_with: list[str] = Field(default_factory=list)
    gap_type: str = ""               # optional override of the gap type raised when this action is uncovered


class MandateLine(BaseModel):
    line_id: str
    country: str
    institution: str
    kind: str                         # power | duty | lead
    action: str                       # ActionDef.code
    description: str
    source_doc: str = ""              # doc_id
    article: str = ""
    procedure: str = ""               # empty = no procedure found
    depends_on: str = ""              # e.g. "APDP:operational?" free text
    dependency_ready: str = "yes"     # yes | no | unknown
    evidence: str = "documented"      # documented | inferred | assumed
    assumed_by: str = ""


# --------------------------------------------------------------------------
# Scenario
# --------------------------------------------------------------------------

class RoleCard(BaseModel):
    code: str
    name: str
    institution: str = ""
    mission: str = ""
    kb_countries: list[str] = Field(default_factory=list)
    kb_institutions: list[str] = Field(default_factory=list)
    contacts: list[str] = Field(default_factory=list)
    language: str = "en"
    kind: str = "institution"         # institution | ai_system | coordinator | adviser
    model_card: str = ""              # for the AI system under test
    perspective: str = ""             # how this institution sees the crisis: what it fears, what it can and cannot do
    priorities: list[str] = Field(default_factory=list)
    voice: str = ""                   # how it writes to colleagues


class Event(BaseModel):
    id: int
    sim_time: str
    to: list[str]
    sender: str = "SCENARIO"
    text: dict[str, str] | str
    act: int = 1
    required_actions: list[str] = Field(default_factory=list)
    expected_gaps: list[str] = Field(default_factory=list)
    failure_mode: str = ""
    severity: int = 2
    public: bool = False
    realism_source: list[str] = Field(default_factory=list)

    def text_in(self, lang: str) -> str:
        if isinstance(self.text, str):
            return self.text
        return self.text.get(lang) or self.text.get("en") or next(iter(self.text.values()), "")


class Scenario(BaseModel):
    id: str
    title: str
    country: str
    language: str = "en"
    fictional_notice: str = "Fictional exercise. Not a real alert."
    summary: str = ""
    ai_system: str = "HYDRO"
    roles_file: str
    events: list[Event]
    twin_of: str = ""
    profile: str = "extended"         # core (hackathon submission: 2 acts, 6 agents) | extended (3 acts)
    gap_rules: list[str] = Field(default_factory=list)   # empty = all rules active

    @field_validator("events")
    @classmethod
    def _sorted(cls, v: list[Event]) -> list[Event]:
        ids = [e.id for e in v]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate event ids")
        return sorted(v, key=lambda e: e.id)


# --------------------------------------------------------------------------
# Drill records
# --------------------------------------------------------------------------

class MessageType(str, Enum):
    INFO = "INFO"
    REQUEST = "REQUEST"
    DECISION = "DECISION"
    OBJECTION = "OBJECTION"
    GAP_FLAG = "GAP_FLAG"
    ANSWER = "ANSWER"


class Citation(BaseModel):
    doc_id: str
    chunk_id: str = ""
    article: str = ""
    quote: str = ""
    verified: Optional[bool] = None
    check_note: str = ""


class Decision(BaseModel):
    seat: str
    event_id: int
    sim_time: str
    situation: str = ""
    known: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    decision: str
    action: str = ""                   # ActionDef.code the decision is about, if any
    legal_basis: list[Citation] = Field(default_factory=list)
    no_legal_basis: bool = False
    confidence: str = "medium"         # low | medium | high
    gap_flags: list[str] = Field(default_factory=list)
    reasoning_summary: str = ""
    author: str = "rules"              # rules = rule engine, no AI | ai = AI model | fallback = AI failed, rules used | human | scripted
    statement: str = ""                # what the seat says to the others on the board, in its own words (AI mode)
    outside_role: bool = False

    @field_validator("confidence")
    @classmethod
    def _conf(cls, v: str) -> str:
        v = (v or "medium").lower().strip()
        return v if v in {"low", "medium", "high"} else "medium"


class Message(BaseModel):
    msg_id: str
    event_id: int
    round: int = 0
    type: MessageType
    sender: str
    recipient: str = "ALL"
    text: str
    action: str = ""
    in_reply_to: str = ""
    status: str = ""                   # for REQUEST answers: accepted | refused | not_our_role; for reactions: agree | object | clarify
    author: str = ""                   # who wrote the text: rules | ai | fallback | human | scripted | system


class Precedent(BaseModel):
    jurisdiction: str
    instrument: str
    article: str = ""
    what_it_does: str
    fit_note: str = ""
    doc_id: str = ""
    url: str = ""
    binding: bool = True


class Gap(BaseModel):
    gap_id: str
    type: str                          # G1..G10
    title: str
    description: str
    action: str = ""
    institutions: list[str] = Field(default_factory=list)
    event_ids: list[int] = Field(default_factory=list)
    first_sim_time: str = ""
    severity: int = 2                  # 1..3
    confidence: str = "suspected"      # confirmed_by_text | suspected
    status: str = "suspected"          # suspected | confirmed | disputed | rejected
    texts_checked: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)   # rule:G1, agent:no_basis, board:unanswered ...
    precedents: list[Precedent] = Field(default_factory=list)
    review_note: str = ""


class DimensionScore(BaseModel):
    dimension_id: int
    name: str
    score: float
    evidence: list[str] = Field(default_factory=list)


class LegalAnswer(BaseModel):
    question: str
    national: str
    missing: str
    elsewhere: list[Precedent] = Field(default_factory=list)
    recommendation: str
    citations: list[Citation] = Field(default_factory=list)
    disclaimer: str = "For exercise purposes only; confirm with a qualified lawyer."


def as_dict(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [as_dict(o) for o in obj]
    if isinstance(obj, dict):
        return {k: as_dict(v) for k, v in obj.items()}
    return obj

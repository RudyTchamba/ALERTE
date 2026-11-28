"""Garde-fous observés lors du premier run multi-agents avec un modèle réel (14B) : niveau de preuve non mérité, citation « none »,
demande reçue sans réponse, demandes en double, nom de champ de requête non standard."""
from __future__ import annotations

import pytest

from app.agents import envelope as env
from app.agents.citations import check_citations
from app.contracts import SearchScope
from tests.agents.conftest import DV, KB, SEARCH, WS, QueueProvider, decide, make_ctx

REQ = {"item_id": "I1", "kind": "board", "msg_id": "MSG1", "from": "DPC", "to": "MET", "msg_type": "REQUEST",
       "body": "Please confirm the forecast.", "round": 2}
REPLY = {"action": "post", "rationale": "answering", "to": "DPC", "msg_type": "INFO", "message": "We will check the forecast.",
         "in_reply_to": "MSG1", "reply_status": "accepted"}


def guard_events(res):  # noqa: ANN001, ANN201
    return [e.payload for e in res.events if e.type == "TOOL_CALL" and e.payload["tool"] == "evidence_guard"]


# ---------------------------------------------------------------- niveau de preuve
def test_documented_without_verified_citation_is_lowered_to_assumed(make_runtime):  # noqa: ANN001
    res = make_runtime(QueueProvider([decide(outcome="no_legal_basis_found", basis=[], evidence_tag="documented")])).activate(make_ctx())
    assert res.decision["evidence_tag"] == "assumed"
    g = guard_events(res)
    assert len(g) == 1 and g[0]["args"] == {"evidence_tag": {"from": "documented", "to": "assumed"}, "reason": "no_verified_citation"}


def test_documented_act_without_validated_mandate_is_lowered_to_inferred(make_runtime):  # noqa: ANN001
    res = make_runtime(QueueProvider([SEARCH, decide()])).activate(make_ctx(mandates=[]))
    assert res.decision["status"] == "recorded" and res.decision["evidence_tag"] == "inferred"
    assert guard_events(res)[0]["args"]["reason"] == "no_validated_mandate_for_seat"


def test_documented_is_kept_when_citation_verified_and_mandate_exists(make_runtime):  # noqa: ANN001
    res = make_runtime(QueueProvider([SEARCH, decide()])).activate(make_ctx())
    assert res.decision["evidence_tag"] == "documented" and not guard_events(res)


def test_inferred_and_assumed_are_never_touched(make_runtime):  # noqa: ANN001
    res = make_runtime(QueueProvider([SEARCH, decide(evidence_tag="inferred")])).activate(make_ctx(mandates=[]))
    assert res.decision["evidence_tag"] == "inferred" and not guard_events(res)


# ---------------------------------------------------------------- citation « none »
@pytest.mark.parametrize("art", ["none", "None", "null", "N/A", "-", "", None])
def test_article_none_string_means_no_article(knowledge, art):  # noqa: ANN001
    scope = SearchScope(WS, frozenset({KB}), frozenset({DV}), purpose="agent", seat_id="S1")
    quote = "Texte sans article numéroté mais suffisamment long"
    (r,) = check_citations(knowledge, None, [{"chunk_id": "C2", "article": art, "quote": quote}], scope=scope, retrieval_set={"C2"})
    assert r.passed, r.reason


def test_wrong_article_is_still_refused(knowledge):  # noqa: ANN001
    scope = SearchScope(WS, frozenset({KB}), frozenset({DV}), purpose="agent", seat_id="S1")
    quote = "peut ordonner l'évacuation des populations exposées"
    for art in ("none", "99", None):  # C1 est l'article 33 : « aucun article » n'est pas l'article 33
        (r,) = check_citations(knowledge, None, [{"chunk_id": "C1", "article": art, "quote": quote}], scope=scope, retrieval_set={"C1"})
        assert not r.passed and r.reason == "article_mismatch"


# ---------------------------------------------------------------- noms de champs tolérés
@pytest.mark.parametrize("payload", [
    {"action": "search_kb", "rationale": "x", "question": "seuils d'alerte"},
    {"action": "search_kb", "rationale": "x", "queries": ["seuils d'alerte", "autre"]},
    {"action": "search_kb", "rationale": "x", "q": "seuils d'alerte"},
    {"action": "search_kb", "rationale": "x", "args": {"query": "seuils d'alerte"}},
])
def test_search_query_aliases_are_accepted(payload):  # noqa: ANN001
    act, err = env.parse_envelope(__import__("json").dumps(payload))
    assert err is None and act.action == "search_kb" and act.query == "seuils d'alerte"


def test_search_without_any_text_is_still_rejected():  # noqa: ANN001
    act, err = env.parse_envelope('{"action": "search_kb", "rationale": "x", "queries": [], "question": ""}')
    assert act is None and "query" in err


# ---------------------------------------------------------------- réponse aux demandes reçues
def test_pending_request_reserves_first_step_for_a_reply(make_runtime):  # noqa: ANN001
    prov = QueueProvider([REPLY, SEARCH, decide()])
    res = make_runtime(prov).activate(make_ctx(seat_code="MET", round=2, inbox=[REQ], seat_codes=["DPC", "OPS"],
                                               step_key="inject:3:round:2:seat:MET"))
    assert prov.schemas[0]["properties"]["action"]["enum"] == ["post"]  # 1er pas : répondre
    assert "search_kb" in prov.schemas[1]["properties"]["action"]["enum"]
    assert "MSG1" in prov.calls[0][-1].content or "MSG1" in " ".join(m.content for m in prov.calls[0])
    assert [(m.to, m.in_reply_to, m.reply_status) for m in res.messages] == [("DPC", "MSG1", "accepted")]
    assert res.decision is not None and res.status == "ok"


def test_already_answered_request_is_not_forced_again(make_runtime):  # noqa: ANN001
    board = [{"msg_id": "R1", "from": "MET", "to": "DPC", "msg_type": "INFO", "in_reply_to": "MSG1", "reply_status": "accepted", "round": 2}]
    prov = QueueProvider([SEARCH, decide()])
    make_runtime(prov).activate(make_ctx(seat_code="MET", round=2, inbox=[REQ], board=board, seat_codes=["DPC", "OPS"]))
    assert "search_kb" in prov.schemas[0]["properties"]["action"]["enum"]


def test_model_that_ignores_the_reply_step_is_not_locked_in_or_replaced_by_a_fallback(make_runtime):  # noqa: ANN001
    prov = QueueProvider([SEARCH, SEARCH, decide()], repeat_last=True)  # répond par une recherche alors que seul « post » est permis
    res = make_runtime(prov).activate(make_ctx(seat_code="MET", round=2, inbox=[REQ], seat_codes=["DPC", "OPS"]))
    assert res.author == "agent" and res.decision is not None and res.decision["outcome"] == "act"
    assert res.messages == []  # aucun message fabriqué par le serveur


def test_no_reply_is_forced_in_the_last_round(make_runtime):  # noqa: ANN001
    prov = QueueProvider([SEARCH, decide()])
    make_runtime(prov).activate(make_ctx(seat_code="MET", round=3, inbox=[REQ], seat_codes=["DPC", "OPS"]))
    assert "post" not in prov.schemas[0]["properties"]["action"]["enum"]


def test_second_request_to_same_seat_is_refused(make_runtime):  # noqa: ANN001
    r1 = {"action": "post", "rationale": "ask", "to": "MET", "msg_type": "REQUEST", "message": "Confirm validity of the alert."}
    r2 = {**r1, "message": "Validate the quality of the forecast."}
    res = make_runtime(QueueProvider([r1, r2, decide(outcome="no_legal_basis_found", basis=[])])).activate(make_ctx())
    assert [m.to for m in res.messages] == ["MET"]
    tc = [e.payload for e in res.events if e.type == "TOOL_CALL" and e.payload["tool"] == "post"]
    assert [t["ok"] for t in tc] == [True, False] and tc[1]["error"] == "duplicate_request"


# ---------------------------------------------------------------- citation « chiffres »
def test_numeric_table_row_is_not_a_legal_quotation(knowledge):  # noqa: ANN001
    knowledge.chunks["TAB"] = {"chunk_id": "TAB", "text": "Régions 80,3 16,6 3,1 100,0 75,2 12,4 8,8", "article": None,
                               "document_version_id": DV, "kb_id": KB, "validity": "in_force"}
    scope = SearchScope(WS, frozenset({KB}), frozenset({DV}), purpose="agent", seat_id="S1")
    (r,) = check_citations(knowledge, None, [{"chunk_id": "TAB", "article": None, "quote": "80,3 16,6 3,1 100,0 75,2"}],
                           scope=scope, retrieval_set={"TAB"})
    assert not r.passed and r.reason == "quote_not_prose"


def test_empty_legal_basis_error_tells_the_model_what_to_do():
    act, err = env.parse_envelope('{"action": "decide", "rationale": "x", "decision": {"action": "refer it", "outcome": "refer", '
                                  '"legal_basis": [], "confidence": "low", "evidence_tag": "assumed"}}')
    assert act is None and "no_legal_basis_found" in err and "unrelated" in err

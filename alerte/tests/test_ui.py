"""Interface tests: every screen renders without error, the arena draws the right arrows, the diagram builds."""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from alerte.sim.engine import Drill
from alerte.ui.arena import arena_html, render_arena
from alerte.ui.architecture import architecture_svg
from alerte.ui.data_access import role_dicts


@pytest.fixture(scope="module")
def finished():
    d = Drill("ae-core", brain="offline")
    return d.run()


def test_arena_draws_messages_and_flags(finished):
    d = Drill("ae-core", brain="offline")
    d.step()
    d.step()
    ev = d.scenario.events[1]
    svg = render_arena(role_dicts(d.scenario), [m.model_dump(mode="json") for m in d.messages if m.event_id == 2],
                       [x.model_dump(mode="json") for x in d.decisions if x.event_id == 2], ev.to, {"sender": ev.sender, "sim_time": ev.sim_time})
    assert svg.startswith("<svg") and "HYDRO" in svg and "MET" in svg and "Coordination board" in svg
    assert "ar-inject" in svg                      # event delivered to its recipients
    assert "<script" not in svg.lower()           # no active content
    html = arena_html(svg, "caption")
    assert "<style>" in html and "prefers-reduced-motion" in html


def test_arena_shows_legal_consultation():
    d = Drill("cm-core", brain="offline")
    for _ in range(3):
        d.step()
    msgs = [m.model_dump(mode="json") for m in d.messages]
    assert any(m["sender"] == "LEGAL" and m["type"] == "ANSWER" for m in msgs), "a seat should consult the Legal Adviser"
    ev = d.scenario.events[2]
    svg = render_arena(role_dicts(d.scenario), [m for m in msgs if m["event_id"] == 3], [], ev.to)
    assert "ar-legal" in svg


def test_architecture_diagram():
    svg = architecture_svg()
    for token in ("SRC", "MLFO", "SINK", "Sandbox".upper(), "Y.3172", "LLM gateway", "hash-chained"):
        assert token in svg
    assert svg.count("<svg") == 1 and svg.rstrip().endswith("</svg>")


def test_live_page_start_step_finish():
    def app():
        from alerte.ui.pages import live
        live.page()
    at = AppTest.from_function(app, default_timeout=60).run()
    assert not at.exception
    at.button[0].click().run()                     # start the drill
    assert not at.exception and at.session_state["drill"] is not None
    nxt = next(b for b in at.button if "Next" in b.label or "Suivant" in b.label)
    nxt.click().run()
    assert not at.exception and at.session_state["drill"].index == 1


@pytest.mark.parametrize("module", ["decisions", "gaps", "replay", "adviser", "readiness", "knowledge", "about"])
def test_other_pages_render(finished, module):
    at = AppTest.from_string(f"from alerte.ui.pages import {module} as m\nm.page()", default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]


def test_arena_draws_objections_and_agreement():
    roles = {"MET": {"name": "NCM", "institution": "NCM", "kind": "institution"}, "DPC": {"name": "NCEMA", "institution": "NCEMA", "kind": "institution"},
             "OPS": {"name": "Op", "institution": "Op", "kind": "institution"}}
    msgs = [{"type": "OBJECTION", "sender": "OPS", "recipient": "DPC", "status": "object", "text": "no legal basis", "action": ""},
            {"type": "INFO", "sender": "MET", "recipient": "ALL", "status": "agree", "text": "fine", "action": ""}]
    svg = render_arena(roles, msgs, [], [])
    assert "objects" in svg and "agrees" in svg


def test_live_page_says_plainly_when_no_ai_is_running():
    def app():
        from alerte.ui.pages import live
        live.page()
    at = AppTest.from_function(app, default_timeout=60).run()
    at.selectbox[1].select("offline").run()
    texts = " ".join(w.value for w in list(at.warning) + list(at.error) + list(at.info))
    assert "RULE ENGINE MODE" in texts and "no AI model" in texts
    at.button[0].click().run()
    assert any("RULE ENGINE MODE" in w.value for w in at.warning)

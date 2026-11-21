"""GapEngine (`ctx.services["gap_engine"]`) : snapshot figé + ledger (LECTURE) + registre -> candidats -> recherche négative
-> scoring -> persistance idempotente. N'écrit JAMAIS le ledger (seule la simulation écrit les événements d'exercice) ;
ne lit aucune table d'un autre module à part `exercise_snapshot.payload` (contrat CONTRACTS.md)."""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..contracts import SearchScope
from ..core.canonical_json import canonical_sha256
from ..core.errors import Conflict, NotFound
from .commitment import compute_commitment, rules_sha256, snapshot_hash
from .detection import Ev, GapCandidate, Registry, demands_from_snapshot, detect
from .models import Gap
from .negative_search import NegativeResult, run_negative_search
from .scoring import finalize

log = logging.getLogger("alerte.gaps")


class GapEngine:
    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx

    # ------------------------------------------------------------------ hooks (contrat simulation -> gaps)
    def on_inject_closed(self, session: Session, exercise_id: str, inject_ref: str) -> list[dict[str, Any]]:
        """Détection incrémentale, au mieux (la détection finale recalcule tout) : une erreur ne casse pas l'exercice."""
        try:
            with session.begin_nested():
                return self.run(session, exercise_id, final=False, up_to_inject=inject_ref)["gaps"]
        except Exception:
            log.exception("détection incrémentale échouée (exercice %s, inject %s)", exercise_id, inject_ref)
            return []

    def on_exercise_finished(self, session: Session, exercise_id: str) -> list[dict[str, Any]]:
        return self.run(session, exercise_id, final=True)["gaps"]

    def detect(self, session: Session, exercise_id: str) -> list[dict[str, Any]]:
        return self.run(session, exercise_id, final=True)["gaps"]

    def compute_commitment(self, snapshot: dict[str, Any]) -> str:
        return compute_commitment(snapshot)

    # ------------------------------------------------------------------ entrées
    def load_snapshot(self, session: Session, exercise_id: str) -> tuple[dict[str, Any], str | None]:
        loader = self.ctx.services.get("snapshot_loader")
        if loader is not None:
            return loader(session, exercise_id)
        try:
            row = session.execute(text("SELECT payload, payload_sha256 FROM exercise_snapshot WHERE exercise_id = :e"),
                                  {"e": exercise_id}).first()
        except Exception as exc:
            raise NotFound("snapshot d'exercice introuvable") from exc
        if row is None:
            raise NotFound("snapshot d'exercice introuvable")
        payload = json.loads(row[0]) if isinstance(row[0], (str, bytes)) else row[0]
        return payload, row[1]

    def read_events(self, session: Session, exercise_id: str) -> list[dict[str, Any]]:
        ledger = self.ctx.services.get("ledger")
        if ledger is None:
            return []
        out, after = [], 0
        while True:
            batch = ledger.read(session, exercise_id, after_seq=after, limit=500)
            if not batch:
                return out
            out += [{"seq": e.seq, "type": e.type, "actor": e.actor, "seat_id": e.seat_id, "sim_time": e.sim_time,
                     "visibility": e.visibility, "payload": e.payload} for e in batch]
            after = batch[-1].seq

    def check_integrity(self, snapshot: dict[str, Any], stored_sha: str | None, events: list[dict[str, Any]],
                        registry: dict[str, str] | None = None) -> dict[str, Any]:
        """Snapshot : l'empreinte du SNAPSHOT du ledger (et la colonne `payload_sha256`) doivent correspondre, sinon refus net.
        Engagement : `commitment_sha256` déclaré vs recalculé ; `match` / `mismatch` / `absent` (jamais bloquant)."""
        snap_ev = next((e["payload"] for e in reversed(events) if e["type"] == "SNAPSHOT"), {})
        if stored_sha and stored_sha != canonical_sha256(snapshot):
            raise Conflict("le snapshot a été modifié après le lancement (payload_sha256 incohérent)",
                           code="gap.snapshot_integrity_failed")
        declared_snap = snap_ev.get("snapshot_sha256")
        if declared_snap and declared_snap != snapshot_hash(snapshot):
            raise Conflict("le snapshot a été modifié après le lancement (snapshot_sha256 incohérent)",
                           code="gap.snapshot_integrity_failed")
        declared = snapshot.get("commitment_sha256") or (snapshot.get("exercise") or {}).get("commitment_sha256") \
            or snap_ev.get("commitment_sha256")
        recomputed = compute_commitment(snapshot, registry)
        status = "absent" if not declared else ("match" if declared == recomputed else "mismatch")
        return {"snapshot": "verified" if declared_snap else "unverifiable", "commitment": status,
                "declared": declared, "recomputed": recomputed, "rules_sha256": rules_sha256()}

    def registry_states(self, session: Session, snapshot: dict[str, Any]) -> tuple[dict[str, str], str]:
        if snapshot.get("registry_states"):
            return dict(snapshot["registry_states"]), "snapshot"
        svc = self.ctx.services.get("mandates")
        if svc is None:
            return {}, "unavailable"
        ws = snapshot["workspace_id"]
        return {i["id"]: svc.registry_state(session, ws, i["id"]) for i in snapshot.get("institutions", [])}, "live"

    # ------------------------------------------------------------------ pipeline
    def run(self, session: Session, exercise_id: str, *, final: bool = True, up_to_inject: str | None = None,
            persist: bool = True) -> dict[str, Any]:
        snapshot, stored_sha = self.load_snapshot(session, exercise_id)
        events = self.read_events(session, exercise_id)
        states, states_src = self.registry_states(session, snapshot)
        integrity = self.check_integrity(snapshot, stored_sha, events, states)
        mandates = snapshot.get("mandates", [])
        registry = Registry.build(mandates, states)
        demands = demands_from_snapshot(snapshot)
        if up_to_inject:
            seq = next((d.seq for d in demands if d.inject_ref == up_to_inject), None)
            if seq is not None:
                demands = [d for d in demands if d.seq <= seq]
        cands = detect(snapshot, registry, demands, events)
        env = self._negative_env(session, snapshot)
        self._enrich(session, exercise_id, snapshot, cands, events, env)
        warnings = []
        integrity["registry_states"] = states_src
        if states_src != "snapshot" and integrity["commitment"] != "match":
            warnings.append(f"registry_states_{states_src}")  # états relus en direct et NON vérifiables par l'engagement
        if integrity["commitment"] == "mismatch":
            warnings.append("commitment_mismatch")
        result: dict[str, Any] = {"integrity": integrity, "warnings": warnings, "gaps": [], "created": 0, "updated": 0,
                                  "unchanged": 0, "stale": 0}
        if persist:
            from .persistence import persist_candidates
            persist_candidates(session, snapshot, exercise_id, cands, env["neg_rows"], integrity, final, result)
        else:
            result["gaps"] = [{"code": c.code, "action_code": c.action_code, "fingerprint": c.fingerprint,
                               "evidence_basis": c.evidence_basis, "confidence": c.confidence, "severity": c.severity,
                               "cause": c.cause, "origin": c.origin} for c in cands]
        return result

    # ------------------------------------------------------------------ recherche négative
    def _negative_env(self, session: Session, snapshot: dict[str, Any]) -> dict[str, Any]:
        know = self.ctx.services.get("knowledge")
        search = self.ctx.services.get("search")
        ws = snapshot["workspace_id"]
        kb_ids, docs, langs = [], set(), []
        for kb in snapshot.get("kb", []):
            meta: dict[str, Any] = {}
            if know is not None and hasattr(know, "kb_overview"):
                try:
                    meta = know.kb_overview(session, ws, kb["kb_id"]) or {}
                except Exception:
                    meta = {}
            if meta.get("kind") in ("global_practices", "prior_reports"):
                continue  # des bonnes pratiques étrangères ne prouvent pas une compétence nationale
            kb_ids.append(kb["kb_id"])
            docs |= set(kb.get("document_version_ids", []))
            for lg in meta.get("languages") or []:
                if lg not in langs:
                    langs.append(lg)
        if not langs:
            langs = [((snapshot.get("scenario") or {}).get("language") or "fr")[:2]]
        cov: dict[str, Any] = {"ratio": None, "missing": []}
        if know is not None and hasattr(know, "coverage") and kb_ids:
            try:
                c = know.coverage(session, ws, kb_ids)
                cov = {"ratio": c.get("ratio"), "missing": c.get("missing", [])}
            except Exception:
                log.exception("coverage indisponible")
        cfg = ((snapshot.get("exercise") or {}).get("settings") or {}).get("gap_detection") or {}
        scope = SearchScope(workspace_id=ws, kb_ids=frozenset(kb_ids), document_version_ids=frozenset(docs), purpose="analyst")
        return {"search": search, "scope": scope, "kb_ids": kb_ids, "docs": docs, "langs": langs, "coverage": cov,
                "cfg": cfg, "cache": {}, "neg_rows": {}}

    def _enrich(self, session: Session, exercise_id: str, snapshot: dict[str, Any], cands: list[GapCandidate],
                events: list[dict[str, Any]], env: dict[str, Any]) -> None:
        lang = ((snapshot.get("scenario") or {}).get("language") or "fr")[:2]
        lang = lang if lang in ("fr", "en") else "en"
        for c in cands:
            if not (c.needs_negative_search or c.absence):
                continue
            c.corpus_documents, c.coverage = len(env["docs"]), env["coverage"]["ratio"]
            if not c.needs_negative_search:
                finalize(c)
                continue
            if env["search"] is None:
                c.neg_status = "unavailable"
                finalize(c)
                continue
            res = env["cache"].get(c.action_code)
            if res is None:
                label = next((a["label"] for a in snapshot.get("actions", []) if a["code"] == c.action_code), c.action_code or "")
                syn = (env["cfg"].get("synonyms") or {}).get(c.action_code or "", {})
                try:
                    res = run_negative_search(env["search"], env["scope"], action_code=c.action_code, label=label,
                                              languages=env["langs"], corpus_documents=len(env["docs"]),
                                              coverage=env["coverage"]["ratio"], coverage_missing=env["coverage"]["missing"],
                                              synonyms=syn, cfg=env["cfg"].get("negative_search"))
                except Exception:
                    log.exception("recherche négative échouée")
                    res = False
                env["cache"][c.action_code] = res
            if res is False:
                c.neg_status = "unavailable"
                finalize(c)
                continue
            c.neg_status, c.strong_hit = "ran", res.verdict == "strong_hit"
            env["neg_rows"][res.query_key] = res
            c.add_evidence(Ev("negative_search", "counter" if c.strong_hit else "supports",
                              {"query_key": res.query_key, "verdict": res.verdict, "corpus_documents": res.corpus_documents,
                               "coverage": res.coverage}, res.statement(lang)))
            for h in res.counter_hits:
                c.add_evidence(Ev("chunk", "counter", {k: h[k] for k in ("chunk_id", "document_version_id", "kb_id", "score",
                                                                         "article", "doc_code")}, h["snippet"]))
            for h in [t for t in res.top_hits if t not in res.counter_hits][:2]:
                c.add_evidence(Ev("chunk", "context", {k: h[k] for k in ("chunk_id", "document_version_id", "kb_id", "score",
                                                                         "article", "doc_code")}, h["snippet"]))
            c.description = f"{c.description} {res.statement(lang)}"
            if c.strong_hit:
                c.artifact = self._is_artifact(c, res, snapshot, events)
                if c.artifact:
                    c.note("document pertinent présent dans la portée du siège mais non récupéré (artefact de retrieval)")
            finalize(c)

    @staticmethod
    def _is_artifact(c: GapCandidate, res: NegativeResult, snapshot: dict[str, Any], events: list[dict[str, Any]]) -> bool:
        """Le document pertinent était dans la portée d'un siège acteur mais n'a jamais été récupéré (RETRIEVAL du ledger)."""
        agent_side_absence = any(s["signal"] == "MISSING_BASIS" for s in c.signals) or any(
            e["type"] == "DECISION" and e["payload"].get("action_code") == c.action_code
            and e["payload"].get("outcome") == "no_legal_basis_found" for e in events)
        if not agent_side_absence:
            return False
        seats = {s["code"]: s for s in snapshot.get("seats", [])}
        acting = {e["payload"].get("seat_code") for e in events if e["type"] == "DECISION"
                  and e["payload"].get("action_code") == c.action_code}
        acting |= {code for code, s in seats.items() if s.get("institution_id") in c.institutions}
        kb_docs = {k["kb_id"]: set(k.get("document_version_ids", [])) for k in snapshot.get("kb", [])}
        for code in acting:
            seat = seats.get(code)
            if not seat or not seat.get("agent"):
                continue
            granted = snapshot.get("grants", {}).get(seat["agent"]["id"], [])
            retrieved = [e for e in events if e["type"] == "RETRIEVAL" and e["seat_id"] == seat.get("seat_id")]
            if not retrieved:
                continue  # aucun retrieval consigné : on ne peut pas conclure à un échec de retrieval
            seen = {r["chunk_id"] for e in retrieved for r in e["payload"].get("results", [])}
            for h in res.counter_hits:
                if h["kb_id"] in granted and h["document_version_id"] in kb_docs.get(h["kb_id"], set()) and h["chunk_id"] not in seen:
                    return True
        return False


def existing_workspace_gap_ids(session: Session, workspace_id: str, exercise_id: str) -> list[str]:
    return list(session.scalars(select(Gap.id).where(Gap.workspace_id == workspace_id, Gap.exercise_id == exercise_id)))

import json

import pytest

from alerte.cli import main
from alerte.knowledge.store import get_store


def test_cli_commands(capsys):
    assert main(["scenarios"]) == 0
    assert "cm01" in capsys.readouterr().out
    assert main(["search", "operators relay public warnings", "-k", "3"]) == 0
    assert "GL-S01" in capsys.readouterr().out
    assert main(["run", "ae01"]) == 0
    out = capsys.readouterr().out
    assert "chain verified" in out
    run_id = out.split("Run ")[1].split()[0]
    assert main(["verify", run_id]) == 0


def test_sft_export(tmp_path, mock_llm):
    """Training data comes only from AI-written or human decisions, never from the rule engine's templates."""
    from alerte.sft import build_dataset
    from alerte.sim.engine import Drill
    rules_run = Drill("cm01").run().run_dir
    none = build_dataset(tmp_path / "none.jsonl", [rules_run])
    assert none.get("drill", 0) == 0
    run = Drill("cm01", brain="llm").run().run_dir
    out = tmp_path / "sft.jsonl"
    counts = build_dataset(out, [run])
    assert counts["total"] > 40 and counts.get("drill", 0) > 0
    first = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert [m["role"] for m in first["messages"]] == ["system", "user", "assistant"]


def test_hash_vectors_hybrid_search(tmp_path):
    """The vector path (meaning-based search) with deterministic test vectors."""
    from alerte.knowledge.ingest import build_index
    from alerte.knowledge.store import KnowledgeStore
    build_index(include_itu=False, embed_provider="hash", index_dir=tmp_path / "idx")
    s = KnowledgeStore.load(tmp_path / "idx")
    assert s.vectors is not None and s.vectors.shape[0] == len(s.chunks)
    hits = s.search("mobile operators must relay public warnings", 3, countries=["EU"])
    assert hits[0].chunk.doc_id == "GL-S01"


def test_chroma_export(tmp_path):
    pytest.importorskip("chromadb")
    from alerte.knowledge.chroma_export import export_to_chroma
    n = export_to_chroma(get_store(), tmp_path / "chroma", "alerte_kb", embed_provider="hash")
    assert n == len([c for c in get_store().chunks if c.collection != "ITUREF"])
    import chromadb
    from chromadb.config import Settings
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"), settings=Settings(anonymized_telemetry=False))
    col = client.get_collection("alerte_kb")
    meta = col.get(limit=1, include=["metadatas"])["metadatas"][0]
    for key in ("source_file", "source_type", "country", "chunk_index", "total_chunks", "ingested_at", "doc_id", "article"):
        assert key in meta

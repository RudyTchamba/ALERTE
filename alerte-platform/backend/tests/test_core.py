from __future__ import annotations

import io
import threading
import time

import pytest

from app.core.blobs import BlobStore
from app.core.canonical_json import canonical_bytes, canonical_sha256, sha256_hex
from app.core.db import make_engine, make_sessionmaker, session_scope
from app.core.ids import is_ulid, new_id
from app.core.jobs import Job, JobRunner, JobStatus
from app.core.security import generate_token, hash_token, safe_equal


def test_canonical_json_is_order_independent_and_compact():
    a = {"b": 1, "a": {"y": [1, 2], "x": "é"}}
    b = {"a": {"x": "é", "y": [1, 2]}, "b": 1}
    assert canonical_bytes(a) == canonical_bytes(b) == '{"a":{"x":"é","y":[1,2]},"b":1}'.encode()
    assert canonical_sha256(a) == sha256_hex(canonical_bytes(b))


def test_canonical_json_rejects_nan_and_non_string_keys():
    with pytest.raises(ValueError):
        canonical_bytes({"x": float("nan")})
    with pytest.raises(TypeError):
        canonical_bytes({1: "x"})


def test_ids_are_unique_ordered_ulids():
    ids = [new_id() for _ in range(2000)]
    assert len(set(ids)) == 2000
    assert ids == sorted(ids)
    assert all(is_ulid(i) for i in ids)


def test_tokens_are_hashed_and_comparable():
    plain, h = generate_token("own")
    assert plain.startswith("own_") and len(plain) > 40
    assert h == hash_token(plain) and h != plain
    assert safe_equal(h, hash_token(plain)) and not safe_equal(h, hash_token(plain + "x"))


def test_blobstore_roundtrip_dedup_and_limits(tmp_path):
    store = BlobStore(tmp_path / "blobs")
    sha = store.put_bytes(b"bonjour")
    assert sha == sha256_hex(b"bonjour") and store.exists(sha) and store.verify(sha)
    assert store.put_bytes(b"bonjour") == sha  # dédoublonnage
    sha2, size = store.put_stream(io.BytesIO(b"x" * 5000), max_bytes=10_000)
    assert size == 5000 and store.size(sha2) == 5000
    with pytest.raises(ValueError):
        store.put_stream(io.BytesIO(b"x" * 5000), max_bytes=100)
    with pytest.raises(ValueError):
        store.path_for("../../etc/passwd")  # aucun chemin libre : uniquement des empreintes
    (store.path_for(sha)).write_bytes(b"corrompu")
    assert not store.verify(sha)


def _runner(tmp_path):
    from app.core.db import Base
    eng = make_engine(f"sqlite:///{(tmp_path / 'j.sqlite').as_posix()}")
    Base.metadata.create_all(eng, tables=[Job.__table__])
    return eng, make_sessionmaker(eng)


def _wait(factory, job_id, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        with session_scope(factory) as s:
            j = s.get(Job, job_id)
            if j.status in JobStatus.TERMINAL:
                return j.status, j.progress, j.result, j.error
        time.sleep(0.05)
    raise AssertionError("job non terminé")


def test_job_runner_progress_result_and_failure(tmp_path):
    eng, factory = _runner(tmp_path)
    runner = JobRunner(factory, workers=2)

    def ok(ctx):
        ctx.update(0.5, "mi-parcours")
        return {"n": 3}

    def boom(ctx):
        raise RuntimeError("échec voulu")

    j1 = runner.submit("test.ok", ok)
    j2 = runner.submit("test.fail", boom)
    s1 = _wait(factory, j1)
    s2 = _wait(factory, j2)
    assert s1[0] == JobStatus.DONE and s1[1] == 1.0 and s1[2] == {"n": 3}
    assert s2[0] == JobStatus.FAILED and "échec voulu" in s2[3]
    runner.shutdown(wait=True)


def test_jobs_left_running_are_marked_interrupted_on_startup(tmp_path):
    eng, factory = _runner(tmp_path)
    with session_scope(factory) as s:
        s.add(Job(id=new_id(), kind="x", status=JobStatus.RUNNING))
        s.add(Job(id=new_id(), kind="y", status=JobStatus.QUEUED))
        s.add(Job(id=new_id(), kind="z", status=JobStatus.DONE))
    runner = JobRunner(factory)
    assert runner.mark_interrupted_on_startup() == 2
    runner.shutdown()


def test_ids_thread_safe():
    out, lock = [], threading.Lock()

    def work():
        local = [new_id() for _ in range(500)]
        with lock:
            out.extend(local)

    ts = [threading.Thread(target=work) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(set(out)) == 4000

"""Tâches longues : table `job` + pool de threads du processus (architecture V1 : un seul processus).

Un job a un identifiant, un statut, une progression observable (SSE) et une erreur éventuelle. Au démarrage,
les jobs restés `queued`/`running` sont marqués `interrupted` (la reprise est une relance explicite).
"""
from __future__ import annotations

import datetime as dt
import logging
import threading
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from sqlalchemy import JSON, DateTime, Float, String, Text, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from .db import Base, session_scope, utcnow
from .ids import new_id

log = logging.getLogger("alerte.jobs")


class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    TERMINAL = {DONE, FAILED, INTERRUPTED}


class Job(Base):
    __tablename__ = "job"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=new_id)
    workspace_id: Mapped[str | None] = mapped_column(String(26), index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16), default=JobStatus.QUEUED, index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobContext:
    """Passé à la fonction du job : met à jour la progression et fournit des sessions courtes."""

    def __init__(self, job_id: str, factory: sessionmaker[Session], payload: dict[str, Any] | None) -> None:
        self.job_id = job_id
        self.payload = payload or {}
        self._factory = factory

    def session(self):  # noqa: ANN201 - context manager
        return session_scope(self._factory)

    def update(self, progress: float | None = None, message: str | None = None) -> None:
        values: dict[str, Any] = {}
        if progress is not None:
            values["progress"] = max(0.0, min(1.0, float(progress)))
        if message is not None:
            values["message"] = message[:500]
        if values:
            with session_scope(self._factory) as s:
                s.execute(update(Job).where(Job.id == self.job_id).values(**values))


JobFn = Callable[[JobContext], dict[str, Any] | None]


class JobRunner:
    def __init__(self, factory: sessionmaker[Session], workers: int = 2) -> None:
        self._factory = factory
        self._pool = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="alerte-job")
        self._lock = threading.Lock()

    def mark_interrupted_on_startup(self) -> int:
        with session_scope(self._factory) as s:
            res = s.execute(
                update(Job).where(Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
                .values(status=JobStatus.INTERRUPTED, error="interrompu par un arrêt du serveur", finished_at=utcnow())
            )
            return res.rowcount or 0

    def submit(self, kind: str, fn: JobFn, *, workspace_id: str | None = None,
               payload: dict[str, Any] | None = None) -> str:
        job_id = new_id()
        with session_scope(self._factory) as s:
            s.add(Job(id=job_id, workspace_id=workspace_id, kind=kind, payload=payload, status=JobStatus.QUEUED))
        self._pool.submit(self._run, job_id, fn, payload)
        return job_id

    def _run(self, job_id: str, fn: JobFn, payload: dict[str, Any] | None) -> None:
        with session_scope(self._factory) as s:
            s.execute(update(Job).where(Job.id == job_id).values(status=JobStatus.RUNNING, started_at=utcnow()))
        ctx = JobContext(job_id, self._factory, payload)
        try:
            result = fn(ctx)
            with session_scope(self._factory) as s:
                s.execute(update(Job).where(Job.id == job_id).values(
                    status=JobStatus.DONE, progress=1.0, result=result, finished_at=utcnow()))
        except Exception as exc:  # noqa: BLE001 - un job ne doit jamais tuer le pool
            log.error("job en échec", extra={"job_id": job_id})
            with session_scope(self._factory) as s:
                s.execute(update(Job).where(Job.id == job_id).values(
                    status=JobStatus.FAILED, error=f"{exc}\n{traceback.format_exc(limit=8)}"[:4000], finished_at=utcnow()))

    def get(self, job_id: str) -> dict[str, Any] | None:
        with session_scope(self._factory) as s:
            job = s.scalar(select(Job).where(Job.id == job_id))
            return None if job is None else job_to_dict(job)

    def shutdown(self, wait: bool = False) -> None:
        self._pool.shutdown(wait=wait, cancel_futures=True)


def job_to_dict(job: Job) -> dict[str, Any]:
    return {
        "id": job.id, "workspace_id": job.workspace_id, "kind": job.kind, "status": job.status,
        "progress": job.progress, "message": job.message, "result": job.result, "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }

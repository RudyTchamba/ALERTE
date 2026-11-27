"""Fournisseurs de modèles (port `contracts.LLMProvider`) : openai_compat, scripted, cassette (doc 08 §8.7).

* Les prompts/réponses sont hachés ici (SHA-256 du JSON canonique de la requête / texte brut de la réponse) ;
  le runtime stocke les mêmes octets dans `ctx.blobs` : les empreintes coïncident.
* `endpoint_ref` d'un profil est le NOM d'une variable de configuration, jamais une URL saisie par l'utilisateur.
"""
from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from ..contracts import LLMMessage, RawCompletion
from ..core.canonical_json import canonical_bytes, sha256_hex
from ..core.config import Settings


class ProviderError(Exception):
    """Base des erreurs fournisseur."""


class ProviderUnavailable(ProviderError):
    """Fournisseur indisponible (réseau, timeout, 5xx, configuration manquante) → repli déterministe du runtime."""


class CassetteError(ProviderError):
    """Cassette introuvable, réponse absente ou prompt divergent : échec explicite (jamais de repli silencieux)."""


def request_bytes(messages: Sequence[LLMMessage], schema: dict[str, Any] | None) -> bytes:
    return canonical_bytes({"messages": [{"role": m.role, "content": m.content} for m in messages], "schema": schema})


def request_sha256(messages: Sequence[LLMMessage], schema: dict[str, Any] | None) -> str:
    return sha256_hex(request_bytes(messages, schema))


def sanitize_endpoint(url: str) -> str:
    """Sans identifiants ni requête : sert de preuve de destination des données."""
    p = urlsplit(url)
    host = p.hostname or ""
    if p.port:
        host = f"{host}:{p.port}"
    return urlunsplit((p.scheme, host, p.path, "", ""))


def extract_json_text(text: str) -> str | None:
    """Premier objet JSON équilibré du texte (tolère clôtures ``` et texte autour)."""
    text = text.strip()
    if text.startswith("{"):
        try:
            json.loads(text)
            return text
        except ValueError:
            pass
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    cand = text[start:i + 1]
                    try:
                        json.loads(cand)
                        return cand
                    except ValueError:
                        break
        start = text.find("{", start + 1)
    return None


# --------------------------------------------------------------------------- openai_compat

_STRATEGIES = ("json_schema", "ollama_format", "json_object", "plain")
# Paramètres de requête supplémentaires autorisés dans `profil.extra.request_body` (liste blanche : jamais de champ arbitraire). Servent surtout à
# désactiver la « réflexion » des modèles qui la pratiquent par défaut, ex. {"chat_template_kwargs": {"enable_thinking": false}} (vLLM).
# Le support dépend du serveur ET du modèle : un paramètre inconnu est ignoré ou refusé (HTTP 400) selon le serveur ; voir docs/runbooks.
ALLOWED_REQUEST_BODY = {"chat_template_kwargs": dict, "reasoning_effort": str}


def validate_request_body(body: Any) -> dict[str, Any]:
    """Valide `extra.request_body` ; lève ValueError (message explicite) si un champ n'est pas autorisé ou mal typé."""
    if body in (None, {}):
        return {}
    if not isinstance(body, dict):
        raise ValueError("request_body doit être un objet JSON")
    bad = sorted(set(body) - set(ALLOWED_REQUEST_BODY))
    if bad:
        raise ValueError(f"champ(s) non autorisé(s) dans request_body : {', '.join(bad)} (autorisés : {', '.join(ALLOWED_REQUEST_BODY)})")
    for k, v in body.items():
        if not isinstance(v, ALLOWED_REQUEST_BODY[k]):
            raise ValueError(f"request_body.{k} : type attendu {ALLOWED_REQUEST_BODY[k].__name__}")
    return dict(body)
_strategy_cache: dict[str, str] = {}


class OpenAICompatProvider:
    name = "openai_compat"
    ai_involved = True
    uses_step_key = False

    def __init__(self, base_url: str, model: str, *, api_key: str | None = None, timeout_s: float = 120.0,
                 extra_body: dict[str, Any] | None = None) -> None:
        if urlsplit(base_url).scheme not in ("http", "https"):
            raise ProviderUnavailable("endpoint invalide (schéma http/https attendu)")
        try:
            self.extra_body = validate_request_body(extra_body)
        except ValueError as exc:
            raise ProviderUnavailable(f"profil de modèle invalide : {exc}") from exc
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_s = timeout_s

    @property
    def url(self) -> str:
        return self.base_url + ("/chat/completions" if self.base_url.endswith("/v1") else "/v1/chat/completions")

    @property
    def endpoint(self) -> str:
        return sanitize_endpoint(self.url)

    def _payload(self, strategy: str, messages: Sequence[LLMMessage], schema: dict[str, Any] | None,
                 temperature: float, max_tokens: int | None) -> dict[str, Any]:
        body: dict[str, Any] = {"model": self.model, "temperature": temperature, "stream": False,
                                "messages": [{"role": m.role, "content": m.content} for m in messages]}
        if max_tokens:
            body["max_tokens"] = max_tokens
        body.update(self.extra_body)
        if schema is not None:
            if strategy == "json_schema":
                body["response_format"] = {"type": "json_schema", "json_schema": {
                    "name": str(schema.get("title", "response")), "schema": schema, "strict": False}}
            elif strategy == "ollama_format":
                body["format"] = schema
            elif strategy == "json_object":
                body["response_format"] = {"type": "json_object"}
        return body

    def complete(self, messages: Sequence[LLMMessage], *, schema: dict[str, Any] | None = None,
                 temperature: float = 0.0, max_tokens: int | None = None) -> RawCompletion:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        strategies = _STRATEGIES if schema is not None else ("plain",)
        cached = _strategy_cache.get(self.base_url)
        if cached in strategies:
            strategies = strategies[strategies.index(cached):]
        last = "aucune réponse"
        t0 = time.monotonic()
        for strat in strategies:
            try:
                resp = httpx.post(self.url, json=self._payload(strat, messages, schema, temperature, max_tokens),
                                  headers=headers, timeout=httpx.Timeout(self.timeout_s))
            except httpx.TimeoutException as exc:
                raise ProviderUnavailable(f"délai dépassé ({self.timeout_s}s)") from exc
            except httpx.HTTPError as exc:
                raise ProviderUnavailable(f"erreur réseau : {type(exc).__name__}") from exc
            if resp.status_code >= 500:
                raise ProviderUnavailable(f"HTTP {resp.status_code} du fournisseur")
            if resp.status_code in (401, 403):
                raise ProviderUnavailable(f"HTTP {resp.status_code} : accès refusé")
            if resp.status_code >= 400:  # format non supporté → stratégie suivante
                last = f"HTTP {resp.status_code} avec la stratégie {strat}"
                continue
            try:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage") or {}
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise ProviderUnavailable("réponse du fournisseur illisible") from exc
            if not isinstance(text, str) or not text.strip():
                raise ProviderUnavailable("réponse vide du fournisseur")
            _strategy_cache[self.base_url] = strat
            return RawCompletion(
                text=text, model=str(data.get("model") or self.model), provider=self.name,
                tokens_in=int(usage.get("prompt_tokens") or 0), tokens_out=int(usage.get("completion_tokens") or 0),
                ms=int((time.monotonic() - t0) * 1000), request_sha256=request_sha256(messages, schema),
                response_sha256=sha256_hex(text), endpoint=self.endpoint)
        raise ProviderUnavailable(f"aucun format de sortie accepté : {last}")


# --------------------------------------------------------------------------- scripted

_DOC_RE = re.compile(r'<retrieved_document untrusted="true" chunk_id="([^"]+)"[^>]*>\n?(.*?)\n?</retrieved_document>', re.S)
_ALLOWED_RE = re.compile(r"^Allowed actions now: (.*)$", re.M)


class ScriptedProvider:
    """Règles déterministes, SANS IA : recherche puis décision citant le meilleur chunk récupéré."""

    name = "scripted"
    ai_involved = False
    uses_step_key = False
    LABEL = "[scripted/no-AI] "

    def complete(self, messages: Sequence[LLMMessage], *, schema: dict[str, Any] | None = None,
                 temperature: float = 0.0, max_tokens: int | None = None) -> RawCompletion:
        t0 = time.monotonic()
        system = next((m.content for m in messages if m.role == "system"), "")
        title = (schema or {}).get("title")
        if title == "AlerteLegalAnswer":
            out = self._legal(system)
        elif title == "AlerteActionEnvelope":
            out = self._action(system)
        else:
            out = {"ok": True, "scripted": True}
        text = json.dumps(out, ensure_ascii=False, sort_keys=True)
        return RawCompletion(text=text, model="scripted-rules-v1", provider=self.name,
                             tokens_in=len(system) // 4, tokens_out=len(text) // 4,
                             ms=int((time.monotonic() - t0) * 1000), request_sha256=request_sha256(messages, schema),
                             response_sha256=sha256_hex(text), endpoint="local:scripted")

    @staticmethod
    def _quote(text: str) -> str:
        flat = " ".join(text.split())
        return flat[:140].rsplit(" ", 1)[0] if len(flat) > 140 else flat

    def _action(self, system: str) -> dict[str, Any]:
        m = _ALLOWED_RE.search(system)
        allowed = [a.strip() for a in m.group(1).split(",")] if m else ["decide"]
        docs = _DOC_RE.findall(system)
        if not docs and "search_kb" in allowed:
            tm = re.search(r"^Inject title: (.*)$", system, re.M)
            return {"action": "search_kb", "rationale": self.LABEL + "search the knowledge base for the inject topic",
                    "query": (tm.group(1) if tm else "mandate")[:200]}
        if not docs:
            return {"action": "decide", "rationale": self.LABEL + "no legal basis found in retrieved documents",
                    "decision": {"action": "No documented basis to act", "action_code": None,
                                 "outcome": "no_legal_basis_found", "legal_basis": [], "confidence": "low",
                                 "options_considered": [], "gap_flags": [], "evidence_tag": "assumed"}}
        cid, text = docs[0]
        am = re.search(rf'chunk_id="{re.escape(cid)}"[^>]*article="([^"]*)"', system)
        article = am.group(1) if am and am.group(1) not in ("", "none") else None
        return {"action": "decide", "rationale": self.LABEL + "act on the best retrieved provision",
                "decision": {"action": "Act within the documented mandate", "action_code": None, "outcome": "act",
                             "legal_basis": [{"chunk_id": cid, "article": article, "quote": self._quote(text)}],
                             "confidence": "medium", "options_considered": [], "gap_flags": [],
                             "evidence_tag": "documented"}}

    def _legal(self, system: str) -> dict[str, Any]:
        docs = _DOC_RE.findall(system)
        claims, cites = [], []
        for cid, text in docs[:2]:
            am = re.search(rf'chunk_id="{re.escape(cid)}"[^>]*article="([^"]*)"', system)
            art = am.group(1) if am and am.group(1) not in ("", "none") else None
            cites.append({"chunk_id": cid, "article": art, "quote": self._quote(text)})
        if cites:
            claims.append({"claim": self.LABEL + "the retrieved text states the quoted provision", "cites": cites[:1]})
        return {"what_the_texts_say": claims, "what_they_do_not_say": [], "what_others_do": [],
                "what_to_check": ["Confirm applicability with a qualified lawyer"]}


# --------------------------------------------------------------------------- cassette

@dataclass
class CassetteProvider:
    """Rejoue des réponses enregistrées, appariées par (step_key, request_sha256). Divergence → CassetteError."""

    entries: dict[tuple[str, str], dict[str, Any]]
    blobs: Any = None
    name: str = "cassette"
    ai_involved: bool = True
    uses_step_key: bool = True
    used: set = field(default_factory=set)

    @classmethod
    def from_file(cls, path: Path, blobs: Any = None) -> CassetteProvider:
        if not path.is_file():
            raise CassetteError(f"cassette introuvable : {path.name}")
        entries: dict[tuple[str, str], dict[str, Any]] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                e = json.loads(line)
                entries[(e["step_key"], e["request_sha256"])] = e
        return cls(entries, blobs)

    @classmethod
    def from_llm_calls(cls, payloads: Sequence[Mapping[str, Any]], blobs: Any) -> CassetteProvider:
        """Construit une cassette depuis les `LLM_CALL` d'un exercice enregistré (réponses lues dans les blobs)."""
        entries = {}
        for p in payloads:
            entries[(p["step_key"], p["request_blob_sha256"])] = {
                "step_key": p["step_key"], "request_sha256": p["request_blob_sha256"],
                "response_sha256": p["response_blob_sha256"], "model": p.get("model", ""),
                "tokens_in": p.get("tokens_in", 0), "tokens_out": p.get("tokens_out", 0)}
        return cls(entries, blobs)

    def complete(self, messages: Sequence[LLMMessage], *, schema: dict[str, Any] | None = None,
                 temperature: float = 0.0, max_tokens: int | None = None, step_key: str = "") -> RawCompletion:
        req = request_sha256(messages, schema)
        entry = self.entries.get((step_key, req))
        if entry is None:
            same_step = [k for k in self.entries if k[0] == step_key]
            if same_step:
                raise CassetteError(f"cassette divergente à l'étape {step_key} : le prompt a changé "
                                    f"(attendu {same_step[0][1][:12]}…, reçu {req[:12]}…)")
            raise CassetteError(f"aucune réponse enregistrée pour l'étape {step_key}")
        text = entry.get("response_text")
        if text is None:
            if self.blobs is None or not entry.get("response_sha256"):
                raise CassetteError(f"réponse introuvable pour l'étape {step_key}")
            text = self.blobs.read_bytes(entry["response_sha256"]).decode("utf-8")
        self.used.add((step_key, req))
        return RawCompletion(text=text, model=str(entry.get("model") or "cassette"), provider=self.name,
                             tokens_in=int(entry.get("tokens_in", 0)), tokens_out=int(entry.get("tokens_out", 0)),
                             ms=0, request_sha256=req, response_sha256=sha256_hex(text), endpoint="local:cassette")


class RecordingProvider:
    """Enveloppe un fournisseur et enregistre ses échanges au format cassette (JSONL)."""

    uses_step_key = True

    def __init__(self, inner: Any) -> None:
        self.inner, self.name, self.ai_involved = inner, inner.name, inner.ai_involved
        self.entries: list[dict[str, Any]] = []

    def complete(self, messages: Sequence[LLMMessage], *, schema: dict[str, Any] | None = None,
                 temperature: float = 0.0, max_tokens: int | None = None, step_key: str = "") -> RawCompletion:
        raw = self.inner.complete(messages, schema=schema, temperature=temperature, max_tokens=max_tokens)
        self.entries.append({"step_key": step_key, "request_sha256": request_sha256(messages, schema),
                             "response_text": raw.text, "model": raw.model,
                             "tokens_in": raw.tokens_in, "tokens_out": raw.tokens_out})
        return raw

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(e, ensure_ascii=False, sort_keys=True) for e in self.entries) + "\n",
                        encoding="utf-8")


# --------------------------------------------------------------------------- fabrique

_NAME_OK = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


@dataclass
class ProfileSpec:
    provider: str
    model: str | None = None
    endpoint_ref: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = 1024
    timeout_s: float | None = None
    extra: dict[str, Any] | None = None

    @classmethod
    def coerce(cls, p: Any) -> ProfileSpec:
        if isinstance(p, ProfileSpec):
            return p
        get = (lambda k, d=None: p.get(k, d)) if isinstance(p, Mapping) else (lambda k, d=None: getattr(p, k, d))
        return cls(provider=get("provider"), model=get("model"), endpoint_ref=get("endpoint_ref"),
                   temperature=get("temperature", 0.0) or 0.0, max_tokens=get("max_tokens"),
                   timeout_s=get("timeout_s"), extra=get("extra"))


def _env_file_value(name: str) -> str | None:
    """Valeur d'une variable déclarée dans le fichier `.env` du backend (relu s'il change) : permet aux profils de
    modèle de désigner un serveur supplémentaire (ex. ALERTE_LLM_AWS_BASE_URL) sans redémarrer l'application."""
    from pathlib import Path

    from dotenv import dotenv_values
    path = Path(".env")
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    if _ENV_CACHE.get("mtime") != mtime:
        _ENV_CACHE.update(mtime=mtime, values=dotenv_values(path))
    v = (_ENV_CACHE.get("values") or {}).get(name)
    return v.strip() if isinstance(v, str) and v.strip() else None


_ENV_CACHE: dict[str, Any] = {}


def resolve_config(name: str, settings: Settings) -> str | None:
    """Résout un NOM de configuration : variable d'environnement, champ `Settings` (ALERTE_X → x), puis `.env`."""
    val = os.environ.get(name)
    if val:
        return val
    if name.upper().startswith("ALERTE_"):
        v = getattr(settings, name[len("ALERTE_"):].lower(), None)
        if v:
            return str(v)
        return _env_file_value(name)
    return None


def provider_for(profile: Any, settings: Settings, *, blobs: Any = None) -> Any:
    """Fabrique le fournisseur d'un profil (dict, ORM ou ProfileSpec)."""
    spec = ProfileSpec.coerce(profile)
    if spec.provider == "scripted":
        return ScriptedProvider()
    if spec.provider == "cassette":
        name = (spec.extra or {}).get("cassette")
        if not isinstance(name, str) or not _NAME_OK.match(name):
            raise CassetteError("profil cassette : nom de cassette absent ou invalide (extra.cassette)")
        return CassetteProvider.from_file(settings.resolved_data_dir / "cassettes" / f"{name}.jsonl", blobs)
    if spec.provider == "openai_compat":
        ref = spec.endpoint_ref or "ALERTE_LLM_BASE_URL"
        base = resolve_config(ref, settings)
        if not base:
            raise ProviderUnavailable(f"endpoint non configuré : définir la variable {ref}")
        key_ref = (spec.extra or {}).get("api_key_ref")
        if key_ref and not str(key_ref).upper().startswith("ALERTE_"):
            # la clé d'API part vers le serveur configuré : un profil ne peut donc désigner qu'une variable d'ALERTE (jamais AWS_*, etc.)
            raise ProviderUnavailable("api_key_ref doit désigner une variable ALERTE_* (jamais une variable arbitraire)")
        api_key = resolve_config(key_ref, settings) if key_ref else settings.llm_api_key
        model = spec.model or settings.llm_model
        if not model:
            raise ProviderUnavailable("modèle non configuré (profil ou ALERTE_LLM_MODEL)")
        return OpenAICompatProvider(base, model, api_key=api_key, timeout_s=spec.timeout_s or settings.llm_timeout_s,
                                    extra_body=(spec.extra or {}).get("request_body"))
    raise ProviderUnavailable(f"fournisseur inconnu : {spec.provider}")

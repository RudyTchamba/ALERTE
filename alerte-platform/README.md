# ALERTE Platform

Plateforme **générique** de simulation d'exercices de crise multi-agents : des agents (ou des humains) jouent les institutions réelles d'un pays, bornées par leurs mandats et leurs sources documentaires ; les **lacunes institutionnelles** émergent des documents, du registre de mandats, des événements du scénario, des interactions et de règles explicites, puis sont validées par des humains et publiées en rapports.

* **Backend** : FastAPI (Python 3.12) · SQLAlchemy 2 + SQLite (WAL) · ChromaDB + FTS5 (RAG hybride) · ledger SHA-256 chaîné.
* **Frontend** : React + TypeScript + Vite.
* **Indépendant de la machine et du Sandbox** : les serveurs de modèles et d'embeddings sont configurables (`ALERTE_LLM_BASE_URL`, `ALERTE_EMBED_BASE_URL`).
* **Multiplateforme** : Linux, Windows, macOS ; Docker/Podman optionnels.

Démarrage : [docs/runbooks/install.md](docs/runbooks/install.md) · Architecture : [docs/architecture/README.md](docs/architecture/README.md) · Contrats entre modules : [backend/CONTRACTS.md](backend/CONTRACTS.md).

```bash
python scripts/setup.py && python scripts/doctor.py && python scripts/dev.py
```

> Les fonctionnalités IA ne sont considérées comme opérationnelles qu'après un test avec un **vrai modèle et de vrais embeddings** (`pytest -m model`). Les fournisseurs `scripted`/`cassette` sont des outils de test, jamais une preuve.

> **Annexe — Recherche : licences logicielles, modèles, SBOM.**
> Matériau de recherche brut produit le 2026-11-21 par un sous-agent (modèle Haiku 5.5), relu en partie par l'architecte. Les marqueurs « non vérifié » / `[NV]` / `[V]` / `[P]` / `[S]` / `[LU]` / `[SUPPOSÉ]` sont ceux du sous-agent. Pièce justificative, pas une spécification.

---

# 15 - Licences, SBOM et modèles (ALERTE)

Date de recherche : 2026-11-21. Document de travail, **ne constitue pas un avis juridique**.

Légende des statuts :
- **[V]** vérifié sur une source officielle lue (page dépôt, carte de modèle Hugging Face, API Hugging Face, page légale), ou sur un résultat de recherche citant la source officielle.
- **[P]** issu de connaissances générales, non relu dans cette session. À confirmer avant décision.
- **[NV]** non vérifié (source inaccessible ou information incertaine).

---

## 1. Inventaire des licences logicielles

### 1.1 Tableau des logiciels

| Composant | Licence SPDX | Statut | Risque (pour publication MIT/Apache-2.0) | Remplaçant / action |
|---|---|---|---|---|
| **PyMuPDF** | AGPL-3.0 (licence commerciale séparée proposée par l'éditeur) | [V] (COPYING lu) | **Élevé** : obligations AGPL réseau et de liaison ; incompatible avec une distribution sous MIT/Apache-2.0 sans licence commerciale | **Ne pas utiliser.** Remplacer par pypdfium2 (rendu) + pdfplumber/pdfminer.six/pypdf (texte) |
| **Docker Desktop** | Conditionnelle : Docker Subscription Service Agreement | [V] (FAQ Docker, résultats de recherche) | **Moyen à élevé** : usage gratuit seulement si &lt; 250 employés ET &lt; 10 M$ de CA ; sinon abonnement payant par utilisateur | Docker Engine (Apache-2.0) + Compose (Apache-2.0), ou Podman (Apache-2.0) |
| **psycopg (3)** | LGPL-3.0 | [P] | **Faible à moyen** : LGPL, acceptable comme dépendance non modifiée ; à documenter (possibilité de relier) | Conserver si accepté ; alternative : asyncpg (Apache-2.0) |
| FastAPI | MIT | [P] | Faible | - |
| Starlette | BSD-3-Clause | [P] | Faible | - |
| Uvicorn | BSD-3-Clause | [P] | Faible | - |
| Pydantic | MIT | [P] | Faible | - |
| SQLAlchemy | MIT | [P] | Faible | - |
| Alembic | MIT | [P] | Faible | - |
| asyncpg | Apache-2.0 | [P] | Faible | - |
| httpx | BSD-3-Clause | [P] | Faible | - |
| NetworkX | BSD-3-Clause | [P] | Faible | - |
| NumPy | BSD-3-Clause | [P] | Faible | - |
| pdfplumber | MIT | [P] | Faible | - |
| pdfminer.six | MIT | [P] | Faible | - |
| pypdf | BSD-3-Clause | [P] | Faible | - |
| pypdfium2 | Apache-2.0 OR BSD-3-Clause | [P] | Faible | Remplaçant recommandé de PyMuPDF |
| docling | MIT | [P] | Faible à moyen (dépendances de modèles à vérifier séparément) | Vérifier la licence des modèles qu'il télécharge |
| WeasyPrint | BSD-3-Clause | [P] | Faible | - |
| ReportLab | BSD (open source) ; offre commerciale distincte pour certaines extensions | [P] | Faible à moyen (vérifier les modules utilisés) | - |
| openpyxl | MIT | [P] | Faible | - |
| python-docx | MIT | [P] | Faible | - |
| pytesseract | Apache-2.0 | [P] | Faible | - |
| Tesseract OCR | Apache-2.0 | [P] | Faible | - |
| tessdata (tessdata_fast / tessdata_best) | Apache-2.0 | [P] | Faible ; vérifier le fichier LICENSE du dépôt tessdata | - |
| cryptography | Apache-2.0 OR BSD-3-Clause | [P] | Faible | - |
| canonicaljson | Apache-2.0 | [P] | Faible | - |
| rfc8785 (JCS) | [NV] | [NV] | [NV] | Vérifier la licence du paquet PyPI avant usage |
| Procrastinate | MIT | [P] | Faible | - |
| pgqueuer | MIT | [P] | Faible | - |
| ChromaDB | Apache-2.0 | [P] | Faible | - |
| Qdrant | Apache-2.0 | [P] | Faible | - |
| Milvus | Apache-2.0 | [P] | Faible | - |
| pgvector | PostgreSQL License | [P] | Faible | - |
| FAISS | MIT | [P] | Faible | - |
| LanceDB | Apache-2.0 | [P] | Faible | - |
| sqlite-vec | MIT OU Apache-2.0 | [P] | Faible | - |
| React | MIT | [P] | Faible | - |
| Vite | MIT | [P] | Faible | - |
| TypeScript | Apache-2.0 | [P] | Faible | - |
| React Router | MIT | [P] | Faible | - |
| TanStack Query / Table | MIT | [P] | Faible | - |
| Tailwind CSS | MIT | [P] | Faible | - |
| Radix UI | MIT | [P] | Faible | - |
| shadcn/ui | MIT (code copié dans le dépôt) | [P] | Faible ; c'est une copie de code : conserver l'attribution | - |
| lucide-react | ISC | [P] | Faible | - |
| Recharts | MIT | [P] | Faible | - |
| react-i18next | MIT | [P] | Faible | - |
| openapi-typescript | MIT | [P] | Faible | - |
| Vitest | MIT | [P] | Faible | - |
| Playwright | Apache-2.0 | [P] | Faible | - |
| Docker Engine | Apache-2.0 | [P] | Faible | - |
| Podman | Apache-2.0 | [P] | Faible | - |
| PostgreSQL | PostgreSQL License (permissive, type MIT/BSD) | [P] | Faible | - |
| SQLite | Domaine public | [P] | Nul | - |
| Ollama | MIT | [P] | Faible | - |
| vLLM | Apache-2.0 | [P] | Faible | - |
| llama.cpp | MIT | [P] | Faible | - |
| Hugging Face TEI | Apache-2.0 | [P] | Faible | - |

**Composants à signaler (aucun ne doit être introduit sans décision explicite) :** PyMuPDF (AGPL-3.0), Docker Desktop (conditionnelle), psycopg (LGPL-3.0, à documenter). Ne sont pas retenus dans la liste : Elastic License, Redis RSAL/SSPL, MongoDB SSPL, BSL : à éviter si ajoutés plus tard (vérifier les versions récentes de Redis, qui ont changé de politique de licence [NV]).

**Compatibilité avec publication MIT/Apache-2.0 :** les composants MIT, Apache-2.0, BSD, ISC, PostgreSQL et domaine public sont compatibles. LGPL (psycopg) est compatible en tant que dépendance non modifiée, avec obligations de documentation. AGPL (PyMuPDF) n'est pas compatible avec une publication permissive si le code est lié ou distribué : **avis juridique requis** avant toute exception.

### 1.2 Dépendances transitives

Les licences transitives ne sont pas listées ici : elles doivent être extraites automatiquement (voir section 3).

---

## 2. Modèles et poids

### 2.1 Distinction code / poids / conditions d'usage

Pour un modèle Hugging Face, trois niveaux peuvent avoir des licences différentes : le **code d'inférence** (souvent Apache-2.0 ou MIT), les **poids** (licence du modèle, souvent identique au code mais non garantie), et les **conditions d'usage** (Acceptable Use Policy, clauses de seuil, attribution). Chaque carte doit être lue.

### 2.2 Tableau des modèles

| Modèle | Licence affichée (carte HF) | Statut | Conditions notables | Compatibilité « open source privilégié » | Langues (FR/EN/AR) |
|---|---|---|---|---|---|
| Qwen2.5-0.5B-Instruct | [NV] | [NV] | - | - | - |
| Qwen2.5-1.5B-Instruct | [NV] | [NV] | - | - | - |
| Qwen2.5-3B-Instruct | **qwen-research** | [V] | Licence de recherche : non permissive pour un usage commercial | **Non** (sauf accord) | Multilingue 29+ langues (carte) [V] |
| Qwen2.5-7B-Instruct | **apache-2.0** | [V] | Standard Apache-2.0 | **Oui** | 29+ langues dont FR, EN, AR [V] |
| Qwen2.5-14B-Instruct | **apache-2.0** | [V] | Standard | **Oui** | 29+ langues [V] |
| Qwen2.5-32B-Instruct | **apache-2.0** | [V] | Standard | **Oui** | 29+ langues [V] |
| Qwen2.5-72B-Instruct | **qwen** (Qwen license) | [V] | Licence propre, non Apache ; clause de seuil d'utilisateurs (100 M) [P] | **Non** | 29+ langues [V] |
| Qwen3-{…} (Apache-2.0 attendu pour la famille) | [NV] (API HF non lue) | [NV] | À vérifier carte par carte | [NV] | 119 langues annoncées [P] |
| Llama 3.x (ex. Llama 3.1 8B Instruct) | **Llama 3.1 Community License** (licence propriétaire personnalisée, non OSI) | [V] | Seuil 700 M d'utilisateurs actifs mensuels (licence Meta requise au-delà) ; attribution « Built with Llama » ; dérivés nommés « Llama… » ; Acceptable Use Policy | **Non** | Multilingue (liste officielle à vérifier) [NV] |
| Mistral 7B | [NV] | [NV] | - | - | - |
| Mistral Nemo 12B Instruct (mistralai/Mistral-Nemo-Instruct-2407) | **apache-2.0** | [V] (recherche, carte officielle citée) | Un miroir tiers (llmware, « mistral-research ») diffère : utiliser le dépôt officiel | **Oui** | Multilingue (FR, AR : [P]) |
| Mistral Small | [NV] | [NV] | - | - | - |
| Gemma (ex. gemma-2-9b-it) | **Gemma Terms of Use** (licence propriétaire) | [V] (résumé de la page officielle, page partiellement lue) | Politique d'usage interdit incorporée ; redistribution avec copie des conditions et clauses reprises en aval ; Gemma 4 régi par une licence distincte | **Non** (conditions personnalisées) | [NV] |
| Phi-3 / Phi-4 | MIT [P] | [NV] | - | Oui [P] | Surtout EN [P] |
| DeepSeek (modèles distillés / V-series) | MIT pour le code ; licence modèle à vérifier [NV] | [NV] | - | [NV] | - |
| BGE-M3 (BAAI/bge-m3) | **mit** | [V] | - | **Oui** | 100+ langues (XLM-RoBERTa), FR, EN, AR inclus [V] |
| bge-reranker-v2-m3 (BAAI) | **apache-2.0** | [V] (API HF) | - | **Oui** | Multilingue [V] |
| multilingual-e5-small / base / large (intfloat) | **mit** (large vérifié) | [V] pour large ; small et base [P] | Notes sur les langues peu dotées | **Oui** | ~94-100 langues (XLM-R) [V] |
| jina-embeddings-v3 | **cc-by-nc-4.0** | [V] (API HF) | **Non commercial** : incompatible avec usage commercial / publication permissive | **Non** | Multilingue [P] |
| nomic-embed-text-v1.5 / v2 | Apache-2.0 attendu | [NV] (API HF non lue) | Vérifier la carte ; v1.5 surtout anglais [P] | [NV] | Surtout EN [P] |
| Qwen3-Embedding | Apache-2.0 attendu [P] | [NV] | À vérifier | [NV] | Multilingue [P] |

### 2.3 Recommandations (sous réserve de vérification des cartes et des tests)

**Génération (sorties structurées JSON Schema sous vLLM/Ollama) :**
1. **Qwen2.5-7B-Instruct** (Apache-2.0 [V]) : option GPU de classe L4/A10. Support multilingue annoncé (FR, AR).
2. **Qwen2.5-14B-Instruct** (Apache-2.0 [V]) : option A10/A100, meilleure qualité.
3. **Qwen2.5-32B-Instruct** (Apache-2.0 [V]) : option 30B+, nécessite un GPU plus large (A100 80 Go ou équivalent, à confirmer).
- Alternative Apache-2.0 : **Mistral Nemo 12B** [V].
- À **éviter** pour publication permissive : Qwen2.5-72B (Qwen license), Qwen2.5-3B (qwen-research), Llama 3.x (licence communautaire), Gemma (conditions propriétaires).

**Embeddings :** **BGE-M3** (MIT [V]), multilingue 100+ langues, adapté FR/AR/EN. Alternative : multilingual-e5-large (MIT [V]).

**Reranker :** **bge-reranker-v2-m3** (Apache-2.0 [V]).

**Ce qui n'est pas vérifiable sans exécution :** qualité réelle en arabe et en français juridique, fiabilité du JSON Schema (taux d'échec, rapport de validation), latence et VRAM réelles sur A10/L4/A100, comportement des modèles après quantification (poids GGUF/AWQ : **la licence de la version quantifiée peut différer ou être dérivée, à vérifier**).

**Note sur les poids dérivés :** les versions quantifiées (GGUF, AWQ, GPTQ) publiées par des tiers héritent en général de la licence d'origine, mais leurs cartes peuvent ajouter des conditions. Télécharger depuis le dépôt officiel de l'éditeur.

---

## 3. Outillage SBOM et inventaire de licences [P]

| Outil | Rôle | Licence [P] |
|---|---|---|
| cyclonedx-py (Python) | Génération SBOM CycloneDX | Apache-2.0 |
| @cyclonedx/cyclonedx-npm (Node) | Génération SBOM CycloneDX | Apache-2.0 |
| SPDX tools (spdx-tools) | Génération/validation SBOM SPDX | Apache-2.0 |
| Syft | Génération SBOM (images, dépôts) | Apache-2.0 |
| Grype | Scan de vulnérabilités à partir d'un SBOM | Apache-2.0 |
| pip-licenses | Inventaire des licences Python | MIT |
| license-checker (npm) | Inventaire des licences npm | BSD-3-Clause |
| licensee | Détection de licences | MIT |
| pip-audit | Audit de vulnérabilités Python | Apache-2.0 |
| npm audit | Audit npm (intégré) | - |
| OSV-Scanner | Audit OSV | Apache-2.0 |
| ORT (OSS Review Toolkit) | Revue de conformité, politique de licences | Apache-2.0 |
| REUSE (FSFE) | En-têtes SPDX par fichier, conformité | Outil : GPL-3.0-or-later ; spécification : CC0 [P] |

**Formats SBOM [P] :** CycloneDX 1.6 (standard ECMA-424) et SPDX 2.3 (ou SPDX 3.0 pour le support de l'écosystème). Recommandation : **CycloneDX 1.6** pour les dépendances et les modèles, **SPDX** si l'équipe ou un acheteur l'exige ; les deux sont convertibles.

**Procédure proposée (à valider) :**
1. Générer le SBOM Python (`cyclonedx-py`) et npm (`@cyclonedx/cyclonedx-npm`) à chaque build, en incluant les transitives.
2. Produire un inventaire de licences (`pip-licenses`, `license-checker`) et le comparer à une liste d'autorisation (MIT, Apache-2.0, BSD-2/3, ISC, PostgreSQL, domaine public, LGPL-3.0 documenté).
3. Bloquer en CI toute licence hors liste (AGPL, GPL, SSPL, BSL, RSAL, « NOASSERTION », « other »).
4. Scanner les vulnérabilités (pip-audit, npm audit, OSV-Scanner, Grype).
5. Pour les images Docker : Syft pour le SBOM, Grype pour le scan.
6. Publier les SBOM en artefacts de build (CycloneDX JSON).

**Intégration GitHub Actions [P] :**
- `actions/dependency-review-action` (officielle GitHub) : bloque les PR qui introduisent une licence interdite ou une vulnérabilité.
- `anchore/sbom-action` (Syft) : génération SBOM en CI, avec upload.
- Les transitives sont couvertes par le lockfile (`uv.lock`/`poetry.lock`/`package-lock.json`) : les SBOM doivent être générés à partir du lockfile, pas des dépendances directes seulement.

**Documentation des licences des modèles et données :** créer deux fichiers dans le dépôt :
- `MODEL_LICENSES.md` : pour chaque modèle, identifiant HF, version (commit), licence du code, licence des poids, conditions d'usage, date de vérification, URL de la carte.
- `DATA_LICENSES.md` : pour chaque corpus ou document importé, `license_spdx` (ou `LicenseRef-...` si non SPDX), `redistribution` (oui/non/à confirmer), source officielle, date d'accès, et mention « avis juridique requis ».

---

## 4. Données et documents importés

**Méthode (aucune supposition juridique) :**
- Pour chaque document importé : enregistrer la source officielle (URL), la date d'accès, le **`license_spdx`** si une licence ouverte est explicitement publiée (ex. Etalab-2.0, CC-BY-4.0, CC0), sinon un **`LicenseRef-`** décrivant la condition telle qu'affichée par la source.
- Ajouter un champ **`redistribution`** : `oui` (licence ouverte explicite), `non` (interdiction explicite), `à confirmer` (silence ou conditions ambiguës). Ne pas redistribuer les documents marqués `non` ou `à confirmer` sans avis.
- Les textes officiels (lois, décrets) ont souvent des conditions de réutilisation propres à chaque État : **ne pas affirmer** une licence pour les textes du Cameroun, des Émirats arabes unis ou d'autres pays sans source officielle lue.
- Les documents de l'UIT présents dans le dépôt (`T-AI4G-AI4GOOD-2025-6-PDF-E.pdf`, `T-REC-Y.3172-201906-I!!PDF-E.pdf`) : vérifier la politique de réutilisation de l'UIT avant toute redistribution. **[NV]**
- Les données de test ou d'exemple générées : indiquer leur licence explicitement (ex. CC0 si créées par l'équipe).

**Avis juridique requis** pour : toute redistribution de textes officiels, toute conclusion sur la réutilisation de documents d'un État, et toute décision sur l'usage d'un modèle dont la licence restreint l'usage commercial.

---

## 5. Points non vérifiés

- Licences exactes de Qwen2.5-0.5B, 1.5B, Qwen3 (tous formats), Mistral 7B, Mistral Small, Phi-3/4, DeepSeek, nomic-embed (v1.5/v2), Qwen3-Embedding : **[NV]** (API ou page non lue).
- Licence du **paquet** rfc8785 sur PyPI : **[NV]**.
- Licence des tessdata et des langues arabes : **[P]**, à lire dans le dépôt officiel.
- Licences de toutes les autres bibliothèques : **[P]** (connaissances générales, non relues).
- Tarifs actuels de Docker : contradictoires selon les sources ; **[NV]**.
- Politique actuelle de licence de Redis (RSAL/SSPL/AGPL depuis les versions récentes) : **[NV]**.
- Qualité, langues réelles, JSON Schema, VRAM : **non vérifiables sans exécution**.
- Licence des textes UIT : **[NV]**.
- Lecture partielle de la page Gemma (résultat de recherche, non intégral).

**Avis juridique requis** pour : PyMuPDF (AGPL), psycopg (LGPL) si modifié, Llama et Gemma (licences propriétaires), Qwen2.5-72B et 3B, Docker Desktop (conditions commerciales), jina-embeddings-v3 (non commercial), et tout document de données.

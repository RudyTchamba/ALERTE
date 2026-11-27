# Évaluation de la recherche documentaire (mesurée)

Outils : `backend/scripts/kb_eval.py`, questions `knowledge_bases/evaluation/questions.jsonl` (50 questions : 25 passages × français/anglais), résultats `knowledge_bases/evaluation/results_lexical.json`. Date : 2026-11-24.

## Méthode
* **Aucun gold saisi à la main** : une question porte un document attendu, éventuellement un article, et une **phrase de preuve** (`evidence_quote`) lue dans les textes. `kb_eval.py` résout les chunks « gold » dans le corpus **construit** (chunks du document dont le texte contient la phrase, et l'article attendu). Si l'étiquette d'article a été mal lue par l'OCR, il évalue le **passage** (phrase retrouvée) et l'indique (`gold_resolution = quote_only`). Une question dont la preuve n'est pas retrouvée dans le texte extrait est **`not_evaluable`** (problème de couverture ou d'extraction), jamais comptée comme réussite ni comme échec.
* Mesures : **Recall@5** (un chunk gold dans les 5 premiers), **MRR**, recall du **document** dans les 5 premiers ; séparées **même langue** (question et document dans la même langue) / **langue croisée** (FR→EN, EN→FR).
* Les questions couvrent Cameroun (30 évaluées), Émirats (8), Références globales (10). **Aucune question ITU** (corpus de 2 documents).

## Résultats — recherche **lexicale seule** (FTS5), pondération d'autorité neutre
Mode : `search_degraded_lexical_only = true`. Embeddings : **0 / 1 342 chunks CM**, 0 pour AE, GL, ITU au moment de la mesure (calcul en cours : voir `build-report.md`).

| Sous-ensemble | n | Recall@5 | MRR | Recall document@5 |
|---|---|---|---|---|
| **Toutes les questions évaluables** | 48 | **0,667** | 0,524 | 0,729 |
| Même langue | 24 | **1,000** | 0,829 | 1,000 |
| **Langue croisée** | 24 | **0,333** | 0,219 | 0,458 |
| Cameroun / Émirats / Global | 30 / 8 / 10 | 0,667 / 0,625 / 0,700 | 0,586 / 0,463 / 0,387 | — |

Non évaluables : **Q019, Q020** (CM-01 art. 32) : l'OCR du scan de la loi 2024/017 a perdu des mots de cet article ; le texte de preuve n'existe pas dans le corpus extrait (défaut d'extraction réel, à relire).

**Lecture** : en même langue, la recherche lexicale atteint 1,000 (n = 24). **En langue croisée elle échoue (0,333)** : sans vecteurs, une question anglaise ne retrouve pas un texte français et inversement. **Le critère T1 (Recall@5 ≥ 0,80 sur ≥ 40 questions évaluables) n'est PAS atteint dans l'ensemble** (0,667) ; il l'est en même langue. La mesure en mode **hybride** (BGE-M3) **n'a pas pu être faite** : les embeddings ne sont pas terminés (voir ci-dessous). Aucune amélioration due aux vecteurs n'est revendiquée.

## Ce que la mesure a révélé (et qui a été corrigé)
| Constat mesuré | Cause | Correction (testée) |
|---|---|---|
| Un texte « unofficial » (loi 86/016 art. 3, 1ʳᵉ réponse lexicale) disparaissait des résultats | la pondération d'autorité (officiel 1,0 … unofficial 0,7) est **multipliée** aux scores RRF dont l'écart entre le 1ᵉʳ et le 8ᵉ rang n'est que de ~10 % : l'autorité l'emporte sur la pertinence ; même un facteur 0,96 suffisait | amplitude réglable `ALERTE_AUTHORITY_SPREAD`, **défaut 0 (neutre)**. Avant (spread = 1) : Recall@5 0,708, même langue 0,958 ; après (0) : 0,729, même langue **1,000** sur la même base (mesures du 2026-11-24, avant le dernier ajout d'étiquettes « Article (n) » des décrets émiratis) |
| Après calcul de seulement quelques vecteurs, tous les résultats venaient du 1ᵉʳ document vectorisé | le signal dense était utilisé dès le premier vecteur : les seuls documents vectorisés reçoivent un rang sémantique | **un index vectoriel incomplet n'est plus utilisé** : recherche lexicale, étiquetée « dégradée » jusqu'à ce que tout le périmètre ait ses vecteurs |
| Articles 52 et 53 de la loi 2024/017 absents des chunks | (1) l'OCR lit « 53 » → « §3 » ; (2) le découpeur **supprimait** le texte entre un titre de section et le prochain article reconnu | texte conservé dans un chunk sans numéro ; garde « texte non couvert par les chunks » ; détection de « suite des articles interrompue » ⇒ document `needs_review` |
| 2 articles sur 218 seulement reconnus dans les décrets des Émirats | format « Article (3) » non reconnu | motif étendu ; Knowledge Records AE : 2 → 218 |
| Page de titre d'un scan portant un cachet traitée comme texte | couche texte du cachet > 80 caractères | règle « page image + peu de texte ⇒ OCR » |

## Limites
* 48 questions rédigées à partir de passages lus par l'auteur du pipeline : **petit échantillon, non indépendant**, qui ne remplace pas un jeu établi par des juristes. Les intervalles de confiance sont larges (n = 24 par sous-ensemble).
* Les questions testent la recherche d'un passage connu ; elles ne mesurent pas la **validité des citations** des agents ni la qualité des réponses (mesures prévues mais **non exécutées** ici : *Citation validity*, *Metadata completeness* au-delà du taux de champs renseignés, *Duplicate rate* = 0 doublon exact et 0 quasi-doublon d'après l'inventaire).
* Aucune question en arabe (aucun document arabe dans le corpus) ; l'OCR arabe est installé mais non exercé.
* **Hybride non mesuré.** Pour le mesurer : terminer l'embedding de la base (`python -m app.cli knowledge embed --country CM`), puis `scripts/kb_eval.py --api http://localhost:8000 --label hybrid` (le port par défaut du script, 8020, est ancien) ; le résultat s'ajoutera à `results_hybrid.json`.

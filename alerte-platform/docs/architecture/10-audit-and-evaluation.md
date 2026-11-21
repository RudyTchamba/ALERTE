# 10 — Audit, traçabilité et évaluation

> Pratiques : BP-13, 34, 35. Critère officiel C4 : « transparency of agent reasoning through logs, chain-of-thought traces, and source attribution ». Décision : ADR 003 (ledger = journal et flux SSE).

## 10.1 Principe : auditer des actes vérifiables, pas un raisonnement privé

| Ce qu'ALERTE enregistre | Ce qu'ALERTE n'exige pas |
|---|---|
| Entrées exactes de chaque appel de modèle (contexte, requêtes, chunks récupérés **avec scores**) | La divulgation du « raisonnement interne » du modèle (non fidèle, non vérifiable) |
| Sortie brute du modèle, sa validation, ses rejets et relances | — |
| Actions (outils) et leurs résultats ; décisions structurées avec **sources vérifiées** | — |
| **`rationale` public** : justification ≤ 280 caractères *produite comme champ de l'action* (déclarée, donc contrôlable et conservée) | — |

C'est la réponse au critère « chain-of-thought traces » : une **trace de décision** complète et rejouable, plus fiable qu'un récit de raisonnement. À expliquer en une diapositive pour le jury.

## 10.2 Catalogue d'événements (contrat central — figé en premier, cf. doc 14)

Champs communs : `seq`, `exercise_id`, `type`, `actor` (`system | coord | facilitator | seat:<code> | human:<nom> | legal`), `seat_id?`, `sim_time`, `real_time` (UTC), `visibility`, `payload` (JSON), `prev_hash`, `hash`.

| Type | Quand | Payload (clés principales) | Visibilité |
|---|---|---|---|
| `SNAPSHOT` | Au lancement | `snapshot_sha256`, `kb_versions`, `ai_mode` (`ai \| scripted \| cassette`), `readiness` | audit |
| `STATE` | Changement d'état | `from`, `to`, `reason` | public |
| `INJECT` | Libération d'un événement | `inject_id`, `title`, `body`, `recipients[]`, `tags`, `fault_mode`, `surprise` | public (ou seat si ciblé) |
| `SEAT` | Affectation/bascule | `seat`, `from`, `to`, `human_name?`, `reason` | board |
| `RETRIEVAL` | Recherche d'un siège | `query`, `scope_hash`, `hits[{chunk_id, score, rank}]`, `signals` | seat |
| `LLM_CALL` | Appel de modèle | `provider`, `model`, `params`, `prompt_sha256`, `response_sha256`, `tokens_in/out`, `ms`, `step_key`, `valid`, `retry` — **prompt et réponse complets dans `blob`** | audit |
| `TOOL_CALL` | Action de l'agent | `tool`, `args`, `rationale`, `result_ref`, `ok`, `error?` | seat |
| `BOARD` | Message sur le tableau | `msg_id`, `from`, `to`, `type`, `body`, `in_reply_to`, `reply_status` | board |
| `DECISION` | Décision enregistrée | décision complète (`outcome`, `legal_basis[]`, `confidence`, `options`, `gap_flags`, `rationale`, `status`) | public (selon exercice) |
| `CITATION_CHECK` | Contrôle de citation | `decision_id\|answer_id`, par citation `{chunk_id, pass, reason}` | audit |
| `GAP` | Candidat ou signal | `origin` (`rule \| coordinator \| agent_hypothesis`), `gap_id?`, `signal`, `code`, `evidence_refs[]` | public pour les constats, audit pour les signaux |
| `HUMAN` | Action d'un humain | `task_id`, `kind` (`task_opened \| submitted \| expired`), `by` | seat/audit |
| `FACILITATOR` | Commande de l'animateur | `command`, `args` | audit |
| `CORRECTION` | Correction | `corrects_seq`, `reason`, `replacement?` — **l'entrée corrigée reste** | audit |
| `ERROR` | Échec | `component`, `message`, `next_action` (ex. « fallback decide », « pause ») | audit |

Chaque événement porte des **données de provenance** (version du moteur, `step_key`, référence au modèle). Les prompts/réponses étant volumineux, ils vont dans `blob` (adressés par SHA-256) ; le ledger conserve leur empreinte (la chaîne couvre donc leur contenu).

## 10.3 Chaîne de hachage

```
canon(e)  = RFC8785_JCS({ exercise_id, seq, type, actor, seat_id, sim_time, real_time, visibility, payload })
hash(e)   = SHA256( prev_hash || 0x0A || canon(e) )                # chaînage, séparation de domaine
genesis   = SHA256( "ALERTE-LEDGER-v1:" || exercise_id || ":" || snapshot_sha256 )   # prev_hash de seq=1
```

* `seq` strictement croissant, **sans trou** ; écriture sous `BEGIN IMMEDIATE` dans la **même transaction** que l'action métier (BP-10/13).
* **Triggers SQLite** `BEFORE UPDATE/DELETE` sur `ledger_event` (refus) — défense contre les erreurs applicatives, pas contre un administrateur.

### Empreinte de rejeu (`replay_digest`) — distincte de la tête de chaîne

La **tête de chaîne** couvre *tout* (dont `real_time`, durées `ms`, identifiants ULID propres à l'exécution) : elle sert à détecter l'altération, pas à comparer deux exécutions. Pour la reproductibilité (rejeu cassette, golden test) on calcule une **projection stable** de chaque événement : `(seq, type, actor_code, seat_code, sim_time, visibility, payload_stable)` où `payload_stable` retire `ms`, `real_time`, les latences, et remplace chaque identifiant d'entité (ULID) par son **ordinal d'apparition** dans l'exercice ; les contenus (prompts, réponses, décisions, citations) sont conservés. `replay_digest = SHA256` chaîné sur ces projections. **Deux exécutions du même snapshot avec la même cassette doivent produire le même `replay_digest`** ; l'`exercise_id` n'intervient pas. La tête de chaîne, elle, diffère à chaque exécution (attendu).

### Vérification (`GET /exercises/{id}/ledger/verify`)

1. Recalcule `hash` de chaque événement dans l'ordre ; compare à `hash` stocké et vérifie `prev_hash` ; 2. vérifie l'absence de trou de `seq` ; 3. recalcule les empreintes des `blob` référencés ; 4. compare la **tête** (dernier `seq`, `hash`) aux **ancres** : table `ledger_anchor` + fichier d'ancre `data/anchors/<exercise>.jsonl` (ajout seul, écrit à la fin de chaque tour ; **sur le même volume que la base : ce n'est pas une ancre externe**) + tête incluse dans chaque rapport ; 5. résultat : `{ok, checked, first_bad_seq?, anchor_mismatch?, truncated_after_anchor?}` → **« intact »** ou **« première entrée altérée n° N »**.

### Détection de modification et de troncature

| Attaque | Détectée par |
|---|---|
| Modification d'un événement | Hash recalculé ≠ stocké, ou chaîne rompue à `seq` N |
| Suppression d'un événement au milieu | Trou de `seq` / `prev_hash` incohérent |
| **Suppression de fin** | Ancre : `seq_ancre > seq_max` ou hash de l'ancre absent → « tronqué après l'ancre » (P0 : ancre en base + fichier sur le même volume + tête dans chaque rapport exporté ; P1 : tête **signée Ed25519** exportée **hors serveur**, clé hors base) |
| Réécriture complète de la chaîne | **Non détectable** si l'attaquant maîtrise base, fichiers d'ancre et clé — limite assumée |

**Formulation honnête (à publier dans la page Audit et le rapport)** : « *Toute modification ou suppression de fin est détectable à partir de la dernière tête exportée ou publiée. Un administrateur qui contrôle à la fois la base, les fichiers d'ancre et la clé de signature peut réécrire le journal ; pour s'en prémunir, exporter la tête signée hors du serveur.* » On ne dit pas « infalsifiable ».

## 10.4 Rejeu et trace de décision

| Fonction | Détail |
|---|---|
| Rejeu de lecture | `GET /exercises/{id}/replay?until_seq=N` : état reconstruit (boîtes, tableau, décisions, lacunes) sans modèle ; curseur temporel ; « voir ce que chaque siège savait » |
| Ré-exécution cassette | Cf. doc 08 §8.14 ; compare le `replay_digest` (test de reproductibilité) |
| **Trace de décision** (page Audit → une décision) | Parcours : *contexte fourni* (boîte, tableau) → *requêtes et chunks (scores)* → *sortie brute du modèle* → *validation Pydantic* → *citations : pass/fail avec raison* → *relance éventuelle* → *décision enregistrée* → *lacunes liées* ; lien vers chaque chunk (page/article/extrait). Pas de chaîne de pensée privée |
| Journal d'erreurs | Repli, relances, budget, pannes (démonstration de robustesse) |
| Export | Ledger en JSONL (avec empreintes) pour vérification **hors** ALERTE (script `verify_ledger.py` indépendant, **à fournir** dans le dépôt) |

## 10.5 Évaluation : métriques T1–T6 (Spec L883-894) et protocoles

| Cible | Protocole mesuré | Seuil | Données | Où | Prio |
|---|---|---|---|---|---|
| **T1 Retrieval** | Jeu de ≥ 40 questions à réponse connue ; le bon document **et** le bon article dans le top 5 | ≥ 80 % (32/40) | `eval_question` (KB) ; répartition suggérée 20/10/10 (national / EAU / mondial) | `evaluation.t1` ; calcule aussi MRR, nDCG, recall@10 | P1 |
| **T2 Citations** | `pass` / total des `CITATION_CHECK` de l'exercice | ≥ 95 % | ledger | automatique | P0 |
| **T3 Lacunes prévues** | Part des `eval_fixture` du scénario retrouvées par le détecteur (par `fingerprint`) | ≥ 80 % | fixtures **cachées** (scellées) | `evaluation.t3` — seul module qui lit les fixtures | P1 |
| **T4 Non inventées** | Part des lacunes `confirmed` ou `partially_real` après revue humaine (`reality_label`) | ≥ 85 % | `gap_review` | calculé depuis les revues (aucun travail en plus) | P1 |
| **T5 Stabilité** | 3 exercices clonés (même snapshot, vrai modèle) ; part des `fingerprint` trouvés dans ≥ 2/3 | ≥ 80 % | 3 exercices (`parent_exercise_id`) | `evaluation.t5` | P1 |
| **T6 Temps et appels** | Durée mur (premier INJECT → dernier événement) et nombre d'événements `LLM_CALL` | < 20 min et < 200 appels | ledger | automatique | P0 |
| Vérif. indépendante | Gaps IFRC (CM-12) touchant le scénario, retrouvés par ALERTE | sans seuil | liste externe | `evaluation.benchmark` | P2 |
| Mesures du Simple | Compréhension du rapport par un non-spécialiste ; couverture IFRC « most » | non bloquantes | revue | hors code | — |

Règles : une métrique non calculable → `status=not_computed` + raison ; jamais 0 (I6) ; chaque mesure est rattachée à un exercice et à une version de KB (reproductible).

Mesures complémentaires RAG (BP-24) : `recall@5/10`, `MRR`, `nDCG@10`, **citation precision** (déterministe), *groundedness* et *completeness* par juge LLM (P1, accord humain mesuré sur 50 réponses), **fuite entre KB = 0** (test bloquant).

## 10.6 Page Audit & Evaluation (UI)

* **Audit** : chronologie filtrable par type/siège ; « Vérifier le journal » ; export JSONL ; ouverture de la **trace de décision** ; état des ancres ; bandeau « SANS IA » le cas échéant ; rejeu avec curseur.
* **Evaluation** : tableau T1–T6 (seuil, valeur, statut, d'où vient le chiffre), lancement des mesures, comparaison entre exercices ; scorecard (doc 09 §9.11).

# Matrice des tests fonctionnels et extrêmes — ALERTE

> Exercice fictif, pas une alerte réelle. **Priorité** : P0 = indispensable à la démonstration ; P1 = important ; P2 = confort/extrême. **Statut réel** (ce qui a été vérifié sur le code actuel) : **UI** cliqué dans l'interface · **API** exécuté par la route de l'interface · **TEST** couvert par un test automatisé · **DOC** déduit, non exécuté · **ABS** non implémenté (le « résultat attendu » décrit alors ce que la **spec** voudrait et ce qui se passe réellement est noté). Le mode utilisé est « Scénarisé (SANS IA) » sauf mention. Procédures détaillées : `guide-test-complet-interface.md` (étapes citées « Ét. N »).

## WS — Espace de travail et accès
| ID | P | Prérequis | Action | Résultat attendu | Risque testé | Statut |
|---|---|---|---|---|---|---|
| WS-01 | P0 | backend démarré, base vide | /access → créer « ALERTE — Demonstration » | jeton propriétaire affiché une fois, Accueil lisible | compréhension du Workspace | API (+UI Accueil) |
| WS-02 | P0 | un espace existe | /access → créer un autre sans jeton | refus « Un espace existe déjà… » (`workspace.bootstrap_disabled`) | création sauvage d'espaces | API |
| WS-03 | P1 | jeton propriétaire | créer un 2ᵉ espace avec le jeton | création OK ; isolation totale | cohabitation | API |
| WS-04 | P0 | 2 espaces | lire exercice/KB/gap/ledger de l'espace 1 avec le jeton de l'espace 2 | **404** partout ; listes vides | fuite inter-espaces | API |
| WS-05 | P1 | — | coller un jeton invalide | « Ce jeton est invalide, expiré ou révoqué » | message d'erreur | UI (libellés) |
| WS-06 | P1 | jeton propriétaire | Jetons d'accès → créer facilitator/observer/auditor ; révoquer | jeton affiché une fois ; révocation immédiate | gestion des rôles | API |
| WS-07 | P2 | — | perdre le jeton propriétaire | non récupérable ; repartir avec un autre `ALERTE_DATA_DIR` | continuité | DOC |
| WS-08 | P1 | — | description d'espace | **pas de champ** description | exigence du brief | ABS |

## GEO — Pays et institutions
| GEO-01 | P0 | WS-01 | créer le pays Cameroun (CM, fr/en) | ligne dans le tableau | base du parcours | API |
| GEO-02 | P1 | — | ISO sur 3 lettres | « Exactement 2 lettres » | validation | UI (libellé) |
| GEO-03 | P0 | GEO-01 | créer les 11 institutions (codes du scénario) | 11 lignes ; filtre pays | codes exacts | API |
| GEO-04 | P1 | GEO-03 | recréer le code `MET` | refus `institution.duplicate` | unicité par espace | API |
| GEO-05 | P1 | institution utilisée | **Supprimer** | refus ; proposer **Archiver** | intégrité référentielle | TEST |
| GEO-06 | P2 | pays sans institution | l'ouvrir | liste d'institutions vide, état vide explicatif | état vide | UI |
| GEO-07 | P2 | — | contacts d'une institution | pas de champ contacts | brief | ABS |

## KB — Bases de connaissances (voir aussi le diagnostic KB)
| KB-01 | P0 | archive CM | Importer une archive → **Valider l'archive** | rapport « valide » (17 docs, 1 665 chunks) ; rien créé avant confirmation | dry-run | API |
| KB-02 | P0 | KB-01 | **Confirmer l'import** (code `CM`) | KB créée, non publiée | import | API |
| KB-03 | P0 | KB-02 | Publier `v1` ; republier sans changement | v1 ; 2ᵉ refus « aucun changement » | versions immuables | API |
| KB-04 | P0 | KB vide | Nouvelle base → Documents → téléverser un PDF scanné | ingestion SSE ≈ 3 min, `needs_review`, pages/articles, qualité 0,88 | extraction/OCR | API |
| KB-05 | P1 | KB-04 | téléverser le **même** fichier | refus `kb.document.duplicate` (SHA-256) | doublon | TEST |
| KB-06 | P1 | doc | Validité = `replaced` | exclu des recherches courantes | obsolète | TEST |
| KB-07 | P0 | KB-02 | Test de recherche « état d'urgence » | CM-09 Art. 6 en tête | retrieval | API |
| KB-08 | P1 | KB-02 | recherche FR sur doc EN / sans résultat / sans article | résultats ou « Aucun résultat » ; mode dégradé affiché | multilingue, vide | API |
| KB-09 | P0 | droits `unknown` | Export → **Publication ouverte** | refus 422 `kb.export.restricted_documents` + liste | droits | API |
| KB-10 | P1 | KB-02 | Export **Sélection** (tous sauf CM-01) puis import | 16 docs / 1 592 chunks ; nouvelle KB | portabilité | API |
| KB-11 | P1 | archive piégée | importer un zip avec `../evil.txt` | rejet `kb.import.integrity_failed` | sécurité import | TEST |
| KB-12 | P1 | doc sans date/licence | Onglet Qualité | « doc_date » manquant listé | métadonnées | API |
| KB-13 | P1 | serveur d'embeddings absent | Calculer les embeddings | message « non configuré » ; recherche « dégradée » | dégradation honnête | API |
| KB-14 | P1 | doc avec « ignore tes règles » | ingérer | alerte d'injection ; jamais exécuté comme ordre | prompt injection | TEST |
| KB-15 | P2 | Ollama + bge-m3 | `pytest -m model tests/knowledge` | dense actif, non dégradé | embeddings réels | TEST (réussi) |
| KB-16 | P1 | — | signature de l'archive | non fournie | intégrité forte | ABS |

## MD — Mandats
| MD-01 | P0 | GEO-03 | Importer un CSV (essai à blanc puis réel) | 14 « proposés », sans source | import | API |
| MD-02 | P1 | `ONR`/`COORD` absents | import | erreurs « institution inconnue » listées ; 12 créés | import partiel | API |
| MD-03 | P0 | MD-01 | **Valider** sans source | 422 « aucune source ne résout vers un chunk réel » | pas de mandat sans source | API |
| MD-04 | P0 | KB CM | rattacher CM-04 Art. 7 à CM-L10 puis **Valider** | « validé », actif | validation | API |
| MD-05 | P1 | MD-01 | **Rejeter** sans motif / avec motif | refus / « rejeté » | motif obligatoire | API |
| MD-06 | P1 | MD-04 | corriger la description | modifiée (API) ; **pas de bouton UI** | correction | API / ABS en UI |
| MD-07 | P1 | MD-04 | historique d'une ligne | création, mise à jour, validation (API) ; non affiché en UI | traçabilité | API / ABS en UI |
| MD-08 | P0 | 9 institutions | registre → `reviewed complete` | avertissement `registry.not_reviewed` disparaît ; lacunes « documentées » possibles | absence ≠ non revu | API |
| MD-09 | P1 | 2 pouvoirs | valider 2 `power` sur la même action | G2 « chevauchement » attendu | double compétence | DOC (non provoqué) |
| MD-10 | P1 | aucun mandat | exercice | G1 pour chaque action exigée | personne n'a le pouvoir | API (22 G1) |
| MD-11 | P2 | — | extraction de mandats par LLM | non fournie | spec F-02 | ABS |
| MD-12 | P1 | document source retiré + republié | exercice | le mandat devient **inactif** ; G1 revient | ablation | API |

## AG / AC — Agents, modèles, permissions
| AG-01 | P0 | GEO-03 | créer `AG-MET` (4 outils, limites 4/3/2) | ligne + Aperçu du prompt sans secret | création | API |
| AG-02 | P1 | AG-01 | code en double | `agent.duplicate` | unicité | API |
| AG-03 | P1 | — | outil inconnu / limite invalide | 422 | validation | TEST |
| AG-04 | P1 | — | rôle « Système d'IA testé » | sorties **scénarisées** (JSON de l'inject), jamais un modèle | HydroSense | TEST |
| AG-05 | P1 | serveur LLM | profil `ollama-local` + **Tester la connexion** | « joignable » ; sinon « injoignable » | fournisseur | TEST/DOC |
| AG-06 | P1 | profil avec URL | saisir une URL à la place du nom de variable | refus `endpoint_not_a_name` | secrets | TEST |
| AG-07 | P1 | exercice `scripted` + agent avec profil réel | lancer | aucun appel modèle (`ai_mode` prime) | confusion SANS IA / IA | TEST |
| AG-08 | P1 | exercice « Modèle réel » sans URL | lancer | ERROR `llm_provider`, **repli** | indisponibilité | API |
| AC-01 | P0 | agents + KB publiées | cocher AG-MET × CM | toast « peut désormais lire » ; persistant | permissions | API |
| AC-02 | P0 | AC-01 | décocher puis lancer ; Audit RETRIEVAL de MET | aucun résultat hors bases accordées | périmètre | TEST (canaris) |
| AC-03 | P0 | agent sans base | Marquer prêt | blocage `agent.no_kb_grant` | agent sans KB | API |
| AC-04 | P1 | — | accorder une KB d'un autre espace | 404 | isolation | API |

## SC — Scénarios
| SC-01 | P0 | GEO-03 | Importer le YAML Rising Waters (fr) | 15 injects, 41 destinataires, 0 avertissement | scénario central | API |
| SC-02 | P1 | institution manquante | importer | erreur/avertissement destinataire | prérequis | TEST |
| SC-03 | P1 | — | YAML invalide | `scenario.import_invalid` | robustesse | TEST |
| SC-04 | P1 | — | inject sans destinataire | lint `inject.no_recipient` (bloquant) | cohérence | TEST |
| SC-05 | P1 | — | destinataire inexistant | `inject.unknown_recipient` | cohérence | TEST |
| SC-06 | P1 | — | demande inconnue | `inject.unknown_action` (bloquant) | catalogue | TEST |
| SC-07 | P1 | — | inject à toutes les institutions | avertissement `inject.all_recipients` | inégalité d'information | TEST |
| SC-08 | P1 | — | moins de 6 modes de panne | avertissement « au moins 6 recommandés » | couverture des pannes | API |
| SC-09 | P2 | — | mauvais ordre chronologique | **aucune vérification** (temps = libellé) | cohérence temporelle | ABS |
| SC-10 | P2 | — | événements contradictoires | permis (voulu par le scénario) ; aucune détection | réalisme | ABS |
| SC-11 | P2 | — | branches conditionnelles | non implémentées | spec v2 | ABS |
| SC-12 | P1 | scénario | Monter/Descendre un inject, Exporter en YAML | ordre mis à jour ; fichier | édition | API |

## RD — Préparation (Readiness)
| RD-01 | P0 | exercice sans siège | page de l'exercice | `seats.none` + « destinataire sans siège : CTD » (codes lisibles) | sièges | UI |
| RD-02 | P0 | 9 sièges, budget par défaut | readiness | **2 blocages budget** (≈ 304–328 appels > 1,5 × 199) | budget | UI/API |
| RD-03 | P0 | RD-02 | recréer avec budget 330 | 0 blocage, 18 avertissements (mandats/registre) | budget | API |
| RD-04 | P1 | siège Humain sans nom | readiness | `seat.human_unnamed` | humain nommé | TEST |
| RD-05 | P1 | siège sans agent | readiness | `seat.no_controller` | contrôleur | TEST |
| RD-06 | P1 | KB non publiée | readiness | `kb.not_ready` | publication | TEST |
| RD-07 | P1 | agent sans KB | readiness | `agent.no_kb_grant` | permissions | TEST |
| RD-08 | P1 | agent sans modèle, mode Modèle réel | readiness | `agent.no_model_profile` | modèle | TEST |
| RD-09 | P1 | fournisseur indisponible | readiness | `provider.test_failed` | disponibilité | TEST |
| RD-10 | P1 | aucun mandat validé | readiness | avertissement `institution.no_mandates` | mandats | API |
| RD-11 | P1 | registre non revu | readiness | avertissement `registry.not_reviewed` | honnêteté des lacunes | API |
| RD-12 | P0 | blocage présent | **Marquer prêt** | refus (409 `exercise.readiness_blocked`) | pas de contournement | API |
| RD-13 | P2 | — | délai de réponse humaine dans l'UI | non exposé | config | ABS en UI |

## SIM — Simulation et contrôles
| SIM-01 | P0 | exercice prêt | Lancer (auto) | terminé en ≈ 16 s ; 284 entrées ; 38/38 citations ; budget 76/330 | autopilot | API |
| SIM-02 | P0 | rythme manuel | Lancer puis **Pas** ×2 | 0 → 1 → 2 événements | pas à pas | API |
| SIM-03 | P0 | en cours | **Pause** / **Reprendre** | *en pause* → *en cours* | contrôle | API |
| SIM-04 | P1 | en cours | rythme *auto avec délai* / *auto* | délai entre événements | cadence | API |
| SIM-05 | P0 | en cours | **Surprise** (OPS, DPC) | événement ad hoc consigné ; +1 inject | imprévu | API |
| SIM-06 | P1 | en cours | changer l'attribution d'un siège | événement `SEAT` + raison | reprise en main | API |
| SIM-07 | P1 | décision existante | correction | entrée `CORRECTION` (API) ; **pas de bouton UI** | erreur d'animateur | API / ABS en UI |
| SIM-08 | P0 | en cours | **Arrêter** | état *arrêté*, détection finale | arrêt propre | API |
| SIM-09 | P1 | coupure brutale | redémarrer le backend | jobs `interrupted` signalés ; exercice reprenable | résilience | TEST |
| SIM-10 | P1 | budget très bas | lancer | pause « budget épuisé » ; Reprendre avec budget étendu | coût | TEST |
| SIM-11 | P1 | 2 exercices simultanés | lancer ensemble | contention SQLite possible : détection incrémentale peut échouer (journalisé), détection finale OK | concurrence | API (observé) |
| SIM-12 | P2 | exercice terminé | modifier son snapshot | impossible : nouvel exercice requis | immutabilité | TEST |
| SIM-13 | P1 | scénario | une institution ne reçoit que ses événements | MET : 1, 2, 6, 8, 11, 15… | distribution | API |

## HS / OB — Siège humain et observateur
| HS-01 | P0 | siège Humain nommé | **invitation** (lien) | `/play#t=pla_…` valable 24 h | accès joueur | API |
| HS-02 | P0 | HS-01 | fiche de rôle | mission, outils, limites, bases, mandats, autres sièges | rôle | API |
| HS-03 | P0 | HS-01 | rechercher | résultats limités à vos bases | permissions | API |
| HS-04 | P1 | HS-01 | interroger le conseiller | réponse 4 parties ; `[scripted/no-AI]` ; décompté | conseiller | API |
| HS-05 | P1 | HS-01 | poster un message à DPC | « préparé » ; envoyé à la clôture | coordination | API |
| HS-06 | P0 | HS-01 | décision avec citation fausse | refus `decision.citation_failed` (`quote_not_in_chunk`) | pas de loi inventée | API |
| HS-07 | P0 | HS-01 | issue « Aucune base légale trouvée » | enregistrée, comptée comme signal | honnêteté | TEST |
| HS-08 | P0 | joueur silencieux | attendre `human_deadline_s` | `HUMAN expired` → `SEAT human→agent deadline_expired` | reprise | API |
| HS-09 | P0 | joueur | lire la boîte d'un autre siège | **403** | confidentialité | API |
| HS-10 | P0 | joueur | commande d'animateur | **403** | rôles | API |
| HS-11 | P1 | lien | ouvrir un lien expiré | « Ce lien est invalide ou a expiré » | expiration | UI (libellé) |
| OB-01 | P0 | jeton observer | `/watch#t=…` | vue publique lecture seule | observation | API |
| OB-02 | P0 | OB-01 | commande / post / création | **403** « rôle insuffisant » | lecture seule | API |
| OB-03 | P0 | OB-01 | boîte privée, tableau | **403** « boîtes privées non visibles » | confidentialité | API |
| OB-04 | P2 | — | choisir tout / public | non implémenté | spec UC-04 | ABS |

## CO — Coordination
| CO-01 | P1 | siège humain | `REQUEST` à DPC | affiché avec type et heure | échanges | API |
| CO-02 | P1 | — | réponse acceptée / refusée / « pas notre rôle » | statut enregistré | réponses | TEST |
| CO-03 | P1 | demande sans réponse | clôture du tour | signal `NO_RESPONSE`/`ORPHAN_REQUEST` | demande orpheline | TEST |
| CO-04 | P1 | — | plus de 2 tours | rejet « tour maximal dépassé » | échanges bornés | TEST |
| CO-05 | P1 | 2 décisions opposées | clôture | `CONFLICTING_DECISIONS` | contradiction | TEST |
| CO-06 | P1 | exercice SANS IA | ouvrir le tableau | **vide** (les agents scénarisés ne postent pas) | limite du mode | API |
| CO-07 | P2 | vrai modèle | échanges réels | à valider | qualité | non fait |

## GAP — Lacunes
| GAP-01 | P0 | exercice terminé | ouvrir /gaps (Exercice = EX-001) | 42 lacunes (22 G1, 8 G6, 7 G7, 2 G8, 2 G10, 1 G9) | détection | UI |
| GAP-02 | P0 | GAP-01 | fiche d'une lacune | chaîne de preuves numérotée ; recherche négative ; couverture | preuves | UI |
| GAP-03 | P0 | registre non revu | exercice | lacunes « déduites », pas « documentées » | absence ≠ non revu | API |
| GAP-04 | P0 | registre revu complet | exercice | lacunes « documentées » | intégrité | API |
| GAP-05 | P0 | GAP-02 | **Contester** sans motif | refus « Un motif est requis… » | revue | TEST |
| GAP-06 | P0 | GAP-02 | **Confirmer** puis **Rejeter** avec motif | statuts mis à jour ; historique conservé | validation humaine | API |
| GAP-07 | P1 | — | rouvrir une lacune | action « Rouvrir » | cycle de vie | DOC |
| GAP-08 | P1 | — | ajouter une action d'amélioration | listée séparément des constats | séparation | TEST |
| GAP-09 | P1 | références vides | fiche | « Aucune référence associée » ; sources insuffisantes | références | UI |
| GAP-10 | P1 | — | filtrer par pays/domaine/confiance | non disponibles | brief | ABS |
| GAP-11 | P1 | G2, G5 | provoquer chevauchement / conflit | non provoqués dans la démo | règles P0 | DOC |
| GAP-12 | P1 | décision sans base | exercice avec signal | `UNSUPPORTED_DECISION`/G1 | décision non étayée | TEST |
| GAP-13 | P1 | citation inexistante | citation fausse | refusée avant enregistrement | pas de loi inventée | API |
| GAP-14 | P1 | même lacune répétée | 2 exercices | fusion par empreinte ; comparaison | doublons | API |
| GAP-15 | P1 | recherche lexicale | négative | passages sans rapport affichés comme contexte | limite connue | UI (observé) |

## CF — Contrefactuel (voir Ét. 20)
| CF-01 | P0 | CM-L15 proposé, registres complets | retirer CM-01, publier v2, exercice 1 | G1 « autoriser le transfert… » documentée | lacune sans texte | API |
| CF-02 | P0 | CF-01 | téléverser le PDF réel, valider CM-L15 sur son art. 32, publier v3, exercice 2 | G1 résolue ; G3 + G4 nouvelles | lacune non préprogrammée | API |
| CF-03 | P0 | CF-02 | retirer, publier v4, exercice 3 | G1 réapparaît | réversibilité | API |
| CF-04 | P1 | CF-01..03 | comparer 1↔2, 2↔3 | résolues/nouvelles conformes | comparaison | API |
| CF-05 | P0 | exercice lancé | modifier la KB/mandats ensuite | l'exercice déjà lancé **ne change pas** (snapshot) | immutabilité | TEST |
| CF-06 | P1 | base copiée | mandat lié à l'ancienne base | reste inactif (ids de versions différents) | subtilité | API |

## RP / EV / AU — Rapports, évaluation, audit
| RP-01 | P0 | exercice terminé | Générer | rapport v1 brouillon, bandeau SANS IA | rapport | API |
| RP-02 | P0 | RP-01 | télécharger MD/JSON/CSV/XLSX/PDF | 5 × HTTP 200 | formats | API |
| RP-03 | P0 | lacune sans référence | XLSX | **corrigé** (avant : 500) | régression | TEST |
| RP-04 | P0 | RP-01 | Publier puis modifier | refus `report.immutable` | immutabilité | API |
| RP-05 | P1 | RP-04 | v2 puis comparer v1↔v2 | version liée ; diff | versions | API (UI : comparer) |
| RP-06 | P1 | — | importer un rapport antérieur | séparé des constats | rapports importés | TEST |
| RP-07 | P2 | Pango absent | PDF | erreur claire | dépendance | DOC |
| EV-01 | P0 | exercice terminé | T2 / T6 | 38/38 ; 15,2 s ; note SANS IA | métriques | API |
| EV-02 | P0 | pas de questions | T1 | « non calculée » (jamais 0) | honnêteté | API |
| EV-03 | P0 | — | scorecard | 13 dimensions « non évaluée » | honnêteté | API |
| EV-04 | P1 | — | évaluation LLM | **501** | non fournie | ABS |
| EV-05 | P1 | 40 questions valides | T1 recall@5 | calculé avec intervalle | retrieval | TEST (jeu à créer) |
| AU-01 | P0 | exercice terminé | Vérifier le ledger | intact (284) | intégrité | API |
| AU-02 | P0 | copie isolée | `ledger_tamper_demo.py` | copie `ok:false` n° 10 ; original `ok:true` | altération | API |
| AU-03 | P0 | — | lire/exporter le ledger | compteur d'appels modèle inchangé (76) | rejeu sans modèle | API |
| AU-04 | P1 | — | Exporter en JSONL | NDJSON ≈ 256 Ko | export | API |
| AU-05 | P1 | — | filtrer la chronologie | par type/siège/texte | lecture | UI (libellés) |
| AU-06 | P1 | — | Trace de décision | recherches, appels, contrôles de citation | transparence | TEST |

## AI — Défaillances des agents et du modèle
| AI-01 | P1 | — | sortie JSON invalide | 1 nouvelle tentative puis « non enregistrée » | robustesse | TEST (+ run réel qwen 1,5 B : observé) |
| AI-02 | P1 | — | `llm_outage` (Surprise) | ERROR + décision de repli | panne modèle | API |
| AI-03 | P1 | — | `silent_institution` | **sans effet** (étiquette seulement) | pannes décoratives | API (observé) |
| AI-04 | P1 | — | modèle trop lent | délai (`ALERTE_LLM_TIMEOUT_S`) puis repli | lenteur | TEST |
| AI-05 | P1 | — | agent hors rôle / dépasse son mandat | « agit hors de son rôle » (signal) | périmètre | TEST |
| AI-06 | P1 | — | agent lit une KB non accordée | impossible (périmètre serveur) ; `SCOPE_VIOLATION` consigné | sécurité | TEST |
| AI-07 | P0 | vrai modèle | run réel qwen2.5:1.5b | recherche réelle OK ; décision sans base légale **rejetée/non vérifiée** (garde-fous) | IA réelle | API (observé) |
| AI-08 | P0 | modèle 7–14 B | `pytest -m model tests/agents` | taux d'échec de schéma < 5 % | qualité | **non fait** |

## UAE — Jumeau
| UAE-01 | P1 | Ét. 1–15 | pack AE : pays, 10 institutions, KB AE, 17 mandats, scénario EN | exercice terminé (33 s) | jumeau | API |
| UAE-02 | P1 | UAE-01 | vérifier la séparation | agents AE : KB AE+GL ; agents CM : CM+GL ; institutions distinctes | confusion de données | API |
| UAE-03 | P1 | UAE-01 | Comparer CM↔AE | 42 nouvelles/42 résolues (empreintes différentes) | comparaison | API (partiel) |
| UAE-04 | P2 | — | scénario EN seulement | pas de FR | langues | DOC |

## STRESS — Scénario composé (Ét. 25.2)
| ST-01 | P1 | CF + AI-02 + HS-08 + surprise spoofing + budget serré | exercice composé | reste lisible, cohérent, sécurisé, auditable, honnête | cumul d'incidents | API (éléments séparés vérifiés ; combiné non exécuté) |
| ST-02 | P2 | — | JSON invalide + citation fausse + hallucination | non reproductibles en SANS IA | IA réelle | non fait |

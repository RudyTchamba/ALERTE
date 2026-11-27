# Dimensionnement des machines d'inférence

**But.** Choisir la machine (locale, d'un coéquipier ou AWS) qui héberge les modèles, **à partir de faits mesurés**, et non du seul nom d'un modèle.
**Statut.** Le cadre de calcul et l'outil de mesure sont prêts ; **aucun chiffre GPU n'a encore été mesuré** (aucun GPU sur la machine de développement, rapports des machines des coéquipiers pas encore reçus). Les cases « À MESURER » ne doivent pas être remplies à la main.

## 1. Ce que demande réellement ALERTE au serveur de génération (relevé dans le code)
| Fait | Valeur | Source |
|---|---|---|
| Requêtes simultanées par exercice en cours | **1** (un fil par exercice, sièges activés l'un après l'autre) | `backend/app/simulation/engine.py` (`_run_unit`, un `threading.Thread` par exercice) |
| Exercices simultanés | 2 au plus (`ALERTE_MAX_CONCURRENT_EXERCISES`) | `core/config.py` |
| ⇒ **Parallélisme à prévoir** | **1** (démonstration) à **2** requêtes simultanées | déduit |
| Taille d'un prompt d'agent | jusqu'à ≈ 4 000 jetons estimés (`TOKEN_BUDGET`), puis dégradé par paliers | `agents/prompt.py` |
| Sortie | `max_tokens` du profil, 1 024 par défaut ; une décision ≈ 200 à 400 jetons | `agents/providers.py`, [DÉDUIT] |
| ⇒ **Contexte minimal du serveur** | **8 192** jetons (4 000 + 1 024 + marge) ; Ollama est à 4 096 par défaut sous 24 Go de VRAM → à relever | https://docs.ollama.com/context-length |
| Appels par exercice (Rising Waters CM, 15 injects, 9 sièges) | estimation **haute** = destinataires × 3 tours × pas ; l'exercice réel en consomme moins | `readiness.py`, `scenarios/service.py` ; **la consommation réelle avec un vrai modèle n'a pas encore été mesurée** |

## 2. Mémoire d'un modèle (formule, pas mesure)
```
VRAM nécessaire ≈ poids du modèle quantifié + cache de contexte (KV) × (contexte) × (requêtes simultanées) + marge (plusieurs Go)
poids ≈ paramètres (en milliards) × octets par paramètre   (4 bits ≈ 0,5 à 0,6 ; 8 bits ≈ 1,0 ; 16 bits ≈ 2,0)
```
Le cache KV dépend de l'architecture du modèle (couches, têtes) : **il se mesure**, il ne se déduit pas du nom. Ollama : augmenter `OLLAMA_NUM_PARALLEL` multiplie la mémoire de contexte (« increasing the context size by the number of parallel requests », https://docs.ollama.com/faq).

## 3. Candidats et ce qui est établi
| Modèle | Poids téléchargés (quantification par défaut Ollama) | Licence | Mode « réflexion » | Source |
|---|---|---|---|---|
| Qwen2.5-14B-Instruct (référence prévue) | AWQ 4 bits ≈ 9-10 Go [DÉDUIT] ; le script AWS le destine à un GPU 24 Go (A10G) | Apache-2.0 | non | fiche HF ; `scripts/aws/setup_vllm.sh` |
| Qwen3.5-9B | `qwen3.5:9b` 6,6–7,6 Go | Apache-2.0 | **oui par défaut** | https://huggingface.co/Qwen/Qwen3.5-9B · https://ollama.com/library/qwen3.5 |
| Granite 4.2-8B | `granite4.2:8b` 5,3 Go | Apache-2.0 | **oui par défaut** | https://huggingface.co/ibm-granite/granite-4.2-8b · https://ollama.com/library/granite4.2 |
| Gemma 4 12B IT | `gemma4:12b` 7,7–8,0 Go | Apache-2.0 selon les métadonnées HF (**page de licence à vérifier**) | désactivée par défaut | https://huggingface.co/google/gemma-4-12B-it · https://ollama.com/library/gemma4 |

Ces informations viennent de la revue du 27/11/2026 (consultation des pages citées) ; **aucun de ces modèles n'a été exécuté dans ce projet**. Les « modèles à réflexion » exigent de pouvoir désactiver la réflexion (voir §6) et, pour certains, une version de vLLM plus récente que celle figée dans `setup_vllm.sh` (v0.8.5) — **à vérifier modèle par modèle**.

## 4. Configurations
| | Minimale | Recommandée |
|---|---|---|
| Usage | **test de câblage** (chaîne technique, pas de qualité) | démonstration avec de vrais résultats |
| Machine applicative | 2 cœurs, 4 Go RAM, 10 Go disque | idem (l'application est légère) |
| Génération | CPU, modèle ≤ 2 B (ex. `qwen2.5:1.5b-instruct`) | **GPU NVIDIA** dont la VRAM ≥ (poids du modèle retenu + KV + marge) : **à déterminer par la mesure du §5** |
| Embeddings | BGE-M3 (≈ 1,2 Go) sur CPU : suffisant pour des requêtes ; la construction d'une base est lente sur CPU | idem, ou même GPU |
| Contexte serveur | 8 192 | 8 192 (16 384 si VRAM ≥ 40 Go, comme `setup_vllm.sh`) |
| Résultat attendu | ≈ 15 à 33 s par appel mesurés sur la machine de développement (4 cœurs, sans GPU, 1,5 B) — **quelques minutes à plusieurs heures par exercice** | à mesurer |
**Ne pas** présenter la configuration minimale comme une validation de la qualité des agents.

## 5. Mesurer sur chaque candidat (outil fourni)
Sur la machine qui héberge le modèle **inactive** (aucun autre calcul), avec le contexte à 8 192 :
```bash
python scripts/llm_bench.py --url http://localhost:11434/v1 --model <nom exact> --calls 5 --prompt-tokens 3500 --max-tokens 300 --out bench-<machine>-<modèle>.json
python scripts/llm_bench.py --url http://localhost:11434/v1 --model <nom exact> --calls 6 --parallel 2 --out bench-par2-<machine>-<modèle>.json   # 2 exercices simultanés
```
Le script affiche médiane et maximum par appel, jetons d'entrée/sortie rapportés par le serveur, et **avertit si le prompt a été tronqué**. Il ne mesure pas la qualité.
Chaque ligne du tableau ci-dessous se remplit avec ces sorties, la sonde matérielle et `nvidia-smi` (VRAM utilisée pendant la mesure).

| Machine | Modèle (nom exact, quantification) | VRAM utilisée | Médiane par appel | Appels/min (1 flux) | Appels/min (2 flux) | Prompt tronqué ? | Date |
|---|---|---|---|---|---|---|---|
| Dev (4 cœurs, sans GPU) | qwen2.5:1.5b-instruct | — | 14,9 s (3 mesures le 26/11, machine au repos) ; 32,7 s à froid | — | — | non vérifié | 2026-11-26 |
| Linux (coéquipier) | À MESURER | | | | | | |
| Windows (coéquipier) | À MESURER | | | | | | |
| AWS (instance à choisir) | À MESURER | | | | | | |

## 6. Règle de décision
1. Recevoir les rapports de la [sonde matérielle](../runbooks/sonde-materielle.md) des machines.
2. Pour chaque machine **dotée d'un GPU**, installer le modèle de référence (Qwen2.5-14B), mesurer (§5).
3. Calculer la durée d'un exercice complet : `appels × médiane`. Un exercice de 150 à 450 appels ne tient pas dans les 7 minutes de démonstration en direct : **prévoir** soit un scénario réduit joué en direct, soit le **rejeu** d'un exercice réel déjà enregistré (présenté comme rejeu, jamais comme une nouvelle génération).
4. Choisir la machine ; **seulement alors** chiffrer une instance AWS (prix relevé sur la page officielle de la région, quota GPU obtenu).
5. Ne comparer d'autres modèles que si ce premier run de référence est fiable.

## 7. Modèles à réflexion : désactiver, si le serveur le permet
Profil de modèle → `extra.request_body` (liste blanche : `chat_template_kwargs`, `reasoning_effort`), par ex. `{"chat_template_kwargs": {"enable_thinking": false}}`.
**Support par serveur (vérifié ou non) :** vLLM — la page officielle `serving/online_serving` n'a pas permis de confirmer `chat_template_kwargs` ; Opus l'a relevé dans les fiches de modèles ; **à tester** sur votre serveur (un paramètre inconnu est ignoré ou refusé en HTTP 400 selon le serveur). Ollama (point d'accès compatible OpenAI) — **non vérifié**. Sans effet pour Qwen2.5 (pas de mode réflexion).

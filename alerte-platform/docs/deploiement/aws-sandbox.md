# Déploiement sur le Sandbox AWS — procédure pour le coéquipier qui détient les accès

**Statut.** Cette procédure est **préparée depuis le dépôt** ; elle n'a été vérifiée contre **aucune** ressource AWS (aucun accès depuis la machine de rédaction). L'état réel du compte (machine créée ? code déployé ? quota GPU ? crédits utilisables ?) est **inconnu** tant que la partie 1 n'a pas été exécutée et ses résultats communiqués.

**Règles.** Ne rien créer, démarrer, arrêter ni modifier sans l'autorisation explicite du responsable du projet. Les commandes de la partie 1 sont de **simple lecture** (aucune dépense). Les parties suivantes **créent des ressources payantes** : elles ne se lancent qu'après décision.

## 1. État du compte — lecture seule (à exécuter et à renvoyer)
Avec l'AWS CLI configurée (authentification à deux facteurs comprise), dans la région du sandbox :
```bash
aws sts get-caller-identity                                  # compte et identité (n'envoyez que les 4 derniers chiffres du compte)
aws configure list | grep -i region                          # région active
aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId,InstanceType,State.Name,Tags[?Key==`Name`]|[0].Value]' --output table
aws ec2 describe-volumes --query 'Volumes[].[VolumeId,Size,State]' --output table
aws service-quotas list-service-quotas --service-code ec2 --query "Quotas[?contains(QuotaName,'G and VT')].[QuotaName,Value]" --output table   # quota instances GPU
aws ecr describe-repositories ; aws s3 ls                    # autres ressources éventuelles
```
Sur la **machine déjà créée** (si elle existe), en SSH : `python3 scripts/hardware_probe.py --label aws-<type> --out ~/alerte-rapports` (voir [sonde-materielle.md](../runbooks/sonde-materielle.md)), puis répondre, **sans rien démarrer d'autre** : l'application est-elle installée ? démarrée ? un serveur de modèle répond-il ? Une base est-elle présente ?

Niveaux à documenter séparément (chacun : OUI / NON / INCONNU) : infrastructure créée · machine démarrée · code transféré · application installée · application démarrée · modèles accessibles · base documentaire disponible · application réellement fonctionnelle.

## 2. Décider du type d'instance — **après** le dimensionnement
Ne choisissez pas d'instance avant d'avoir : (a) le modèle retenu, (b) son poids quantifié et la VRAM nécessaire, (c) le quota GPU obtenu, (d) le prix **relevé sur la page officielle EC2** de la région. Voir [dimensionnement.md](dimensionnement.md). Ce guide ne recommande volontairement aucune instance.

## 3. Architectures possibles (à choisir ensemble)
| Option | Description | Quand |
|---|---|---|
| **A — tout sur une instance GPU** | application (Docker) + modèles sur la même instance | démonstration autonome, un seul point à garder allumé |
| **B — modèles sur AWS, application sur un portable** | tunnel SSH vers vLLM (`scripts/aws/setup_vllm.sh`, `scripts/llm_target.py`, [aws-gpu-model.md](../runbooks/aws-gpu-model.md)) | le portable garde les données ; AWS ne sert que d'inférence |
| **C — application sur une petite instance CPU, modèles sur une machine d'équipe** | deux machines, URL configurables | si la machine GPU est chez un coéquipier |

## 4. Mise en place (UNIQUEMENT après autorisation) — option B (déjà scriptée)
1. Quota « Running On-Demand G and VT instances » (partie 1) ; instance avec l'AMI « Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu) », disque ≥ 100 Go.
2. Sur l'instance, dans `tmux` : `MODEL=<modèle retenu> bash scripts/aws/setup_vllm.sh` (installe vLLM v0.8.5 en Docker, écoute **127.0.0.1 seulement**, génère une clé d'API dans `/etc/alerte-vllm.env`).
3. Sur le poste de l'application : `ssh -N -L 8001:127.0.0.1:8000 -i <clé.pem> ubuntu@<ip-instance>`, puis `python3 scripts/llm_target.py init-aws --url http://localhost:8001/v1 --model <nom servi> --key <clé>` et `python3 scripts/llm_target.py aws`. **Ce script modifie `backend/.env` (avec sauvegarde)** : le lancer est une décision du propriétaire du fichier.
4. Vérification : `curl -H "Authorization: Bearer <clé>" http://localhost:8001/v1/models` ; `python3 scripts/doctor.py` ; préparer un exercice « Modèle réel ».

## 5. Mise en place — option A (Docker sur l'instance) — NOT TESTED
```bash
git clone <URL du dépôt> && cd <dépôt>/alerte-platform && git checkout Rudy
VLLM_MODEL=<modèle> docker compose -f deploy/compose.models.yml --profile vllm up -d vllm        # modèles (GPU)
cp deploy/env.app.example deploy/.env.app                                                         # ALERTE_LLM_BASE_URL=http://host.docker.internal:8001/v1 ; ALERTE_EMBED_* : voir ci-dessous
docker compose -f deploy/compose.app.yml --env-file deploy/.env.app up -d --build
curl http://localhost:8000/api/v1/health
```
Les **embeddings** (BGE-M3) : vLLM ci-dessus ne les sert pas ; prévoir Ollama (`docker compose -f deploy/compose.models.yml up -d ollama` puis `ollama pull bge-m3`) et `ALERTE_EMBED_BASE_URL=http://host.docker.internal:11434/v1`. Accès à l'interface depuis votre poste : tunnel `ssh -L 8000:127.0.0.1:8000 …`.

## 6. Réseau et sécurité
| Port | Règle du groupe de sécurité |
|---|---|
| 22 (SSH) | votre IP seulement |
| 8000 (application) | **ne pas ouvrir** : tunnel SSH |
| 8001 / 11434 (modèles) | **ne pas ouvrir** : localhost / tunnel |
Aucune clé dans le dépôt ni dans les captures d'écran. Chiffrer ou limiter l'accès aux données de démonstration (textes publics, aucune donnée personnelle).

## 7. Contrôle des coûts
Une instance GPU facture tant qu'elle est **démarrée**. Arrêtez-la après chaque session (`aws ec2 stop-instances --instance-ids <id>`) et notez heure de démarrage/arrêt. Ne supposez pas que les 20 000 USD de crédits annoncés sont disponibles : vérifiez-les dans la console (Billing → Credits).

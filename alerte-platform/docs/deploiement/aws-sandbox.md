# Déploiement sur le Sandbox AWS — procédure exacte (une seule machine virtuelle)

> **Région imposée : Europe (Francfort), `eu-central-1`.** Dans la console, sélectionnez-la en haut à droite avant de chercher une instance (liste vide = souvent mauvaise région). La disponibilité de `g5.2xlarge` dans cette région n'est **pas vérifiée** : voir la partie 1.

**Ce document donne une recommandation précise. Ce qui y est établi et ce qui ne l'est pas est dit à chaque fois.**
Je n'ai accès à aucun compte AWS depuis la machine de rédaction : **les types d'instance, quotas, régions autorisées, prix et la sortie Internet du sandbox ne sont PAS vérifiés**. La partie 1 (lecture seule, sans coût) les vérifie avant toute création. Rien ici n'a été exécuté sur AWS : **statut global NOT TESTED**.

## 0. La machine recommandée (résumé)
| Paramètre | Valeur à saisir | Pourquoi |
|---|---|---|
| **Type d'instance** | **`g5.2xlarge`** (1 GPU NVIDIA A10G 24 Go, 8 vCPU, 32 Go de RAM — **à confirmer dans le sélecteur de la console**) | un GPU de 24 Go héberge Qwen2.5-14B quantifié (≈ 9-10 Go de poids) **et** BGE-M3 ; 8 vCPU et 32 Go de RAM permettent d'y faire tourner aussi l'application et la construction de la base sans saturer |
| Si indisponible ou quota refusé | `g5.xlarge` (4 vCPU, 16 Go ; **c'est le type actuel d'`AlerteVM`**) fonctionne mais **sans marge** (construction de la base et modèle en même temps déconseillés) ; sinon `g6.2xlarge` (GPU L4 24 Go) — **non évalué** | — |
| **Système (AMI)** | **Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 24.04)** (pilotes NVIDIA, Docker et NVIDIA Container Toolkit inclus). Si seule la 22.04 existe : voir §3 (Python 3.12 à ajouter) | l'application exige Python ≥ 3.11 (3.12 recommandé) ; Ubuntu 24.04 l'apporte |
| **Stockage racine** | **200 Go**, type **gp3** (3 000 IOPS, 125 Mo/s par défaut) | AMI ≈ 60 Go + image vLLM ≈ 10 Go + modèle ≈ 10 Go + base et vecteurs + marge ; 100 Go ne suffisent pas (déjà constaté dans `aws-gpu-model.md`) |
| **Modèle de génération** | `Qwen/Qwen2.5-14B-Instruct-AWQ` servi par vLLM, contexte **8 192** | c'est le modèle de référence prévu (`.env`) ; l'AWQ 4 bits tient sur 24 Go |
| **Embeddings** | `bge-m3` via Ollama (sur le même GPU) | modèle d'embeddings retenu du projet |
| **Réseau** | IP publique, **groupe de sécurité : SSH (22) depuis VOTRE IP seulement**, aucun autre port ouvert | l'application et les modèles ne sont joints que par **tunnel SSH** |
| **Résiliation** | **protection contre la résiliation activée** ; on **arrête** l'instance, on ne la **résilie** jamais | un arrêt ne facture que le disque |

**Partage du GPU (calcul indicatif, non mesuré)** : poids 14B AWQ ≈ 9,4 Go ; cache de contexte (48 couches × 8 têtes KV × 128 × 2 × 2 octets ≈ 0,19 Mo par jeton) × 8 192 jetons × 2 requêtes ≈ 3 Go. vLLM est donc limité à **75 % de la mémoire GPU** (`VLLM_GPU_UTILIZATION=0.75`, ≈ 17 Go) ; il reste ≈ 5 Go pour Ollama/BGE-M3 (≈ 1,2 Go de poids). Valeurs à confirmer avec `nvidia-smi` (§6).

**Ce qui n'est pas mesuré** : la vitesse réelle (secondes par appel). Elle se mesure à l'étape 7 avec `scripts/llm_bench.py` ; ne promettez pas de durée avant.

## 0 bis. Comptes d'accès et machine existante « AlerteVM » — à clarifier AVANT de créer quoi que ce soit
**Situation** : un coéquipier a créé une machine `AlerteVM` avec le compte protégé par SON authentification à deux facteurs (MFA) ; les autres membres ont reçu des comptes des organisateurs. **Je ne sais pas** si ces comptes sont dans le **même compte AWS** que `AlerteVM` ou dans d'**autres** comptes : cela dépend de la façon dont les organisateurs ont configuré l'accès, et rien dans le dépôt ne le dit. Le MFA d'un utilisateur ne bloque **pas** les autres utilisateurs : il ne protège que **sa** connexion.

**Test décisif (2 minutes, lecture seule)** — chaque personne, avec **son propre** accès :
| Qui | Commande ou écran | Ce qu'on note |
|---|---|---|
| vous | console AWS, menu du profil en haut à droite : **ID de compte** (12 chiffres) ; ou `aws sts get-caller-identity` | les **4 derniers chiffres** de l'ID de compte, et le type d'identité (`user/…`, `assumed-role/…`) |
| le coéquipier | idem avec le compte qui a créé `AlerteVM` | les 4 derniers chiffres |
| les deux | région affichée en haut à droite de la console | la **région** de `AlerteVM` |

| Résultat | Conclusion | Que faire |
|---|---|---|
| **Même ID de compte** | même compte AWS : `AlerteVM` existe pour vous aussi | ne **créez pas** de nouvelle machine ; passez à « Réutiliser AlerteVM » ci-dessous |
| **ID différents** | comptes séparés : vous **ne verrez pas** `AlerteVM`, et les crédits sont peut-être séparés | demandez aux organisateurs **quel compte porte les crédits** et lequel doit servir pour la finale ; ne dupliquez rien tant qu'ils n'ont pas répondu |
| Même ID mais `AlerteVM` invisible | mauvaise **région** (les instances sont propres à une région), ou **permissions** insuffisantes (`ec2:DescribeInstances` refusé) | changez de région dans la console ; sinon demandez aux organisateurs d'étendre vos droits EC2 |
| Votre connexion est une connexion « SSO / portail d'accès » avec liste de comptes | normal pour les accès d'équipe d'un sandbox | le portail liste les comptes et rôles auxquels vous avez droit : relevez les ID |

**Réutiliser `AlerteVM` (même compte)** — d'abord la **lire sans la modifier** (console → EC2 → Instances → `AlerteVM`, onglets Détails et Stockage) et noter : type d'instance, état, région, taille et type du disque, groupe de sécurité, paire de clés, système. Puis :
| Constat sur `AlerteVM` | Décision |
|---|---|
| type **GPU** (`g5.*` ou équivalent) avec ≥ 24 Go de mémoire GPU et disque ≥ 150 Go | l'adopter : **ne rien recréer**, passer aux §3 et suivants |
| type **sans GPU** (`t3`, `m5`, `c5`…) | elle peut héberger l'**application** mais **pas** un modèle de 14 B : soit on y ajoute plus tard un modèle distant (autre machine), soit son type est **changé** (arrêter l'instance, *Actions → Instance settings → Change instance type* ; possible seulement si le quota GPU le permet et que le disque est assez grand) — **à décider avec le coéquipier, jamais seul** (un arrêt coupe ce qui tourne dessus) |
| disque trop petit | l'agrandir (*Modifier le volume*, puis `growpart` / `resize2fs` sur l'instance) |
**Accès SSH à `AlerteVM`** : seul son créateur possède le fichier `.pem` de la paire de clés. Deux solutions sans rien refaire : (1) le coéquipier ajoute **votre clé publique** (`~/.ssh/id_ed25519.pub`) dans `~/.ssh/authorized_keys` de l'instance ; ou (2) *EC2 Instance Connect* depuis la console (bouton *Se connecter*) ou `aws ec2-instance-connect send-ssh-public-key --instance-id <id> --instance-os-user ubuntu --ssh-public-key file://~/.ssh/id_ed25519.pub --region <RÉGION>`, **si** vos permissions l'autorisent et si le port 22 est ouvert depuis votre IP. Ne partagez **jamais** le `.pem` par un canal de messagerie.

**Si `AlerteVM` n'est pas utilisable** (autre compte, mauvais type) : seulement alors, créez la machine du §2 — dans le compte **désigné par les organisateurs** — et notez-le ici pour ne pas refaire la même chose deux fois.

### Constat du 28/11/2026 (relevé dans la console par un membre de l'équipe, même compte AWS que le créateur de la machine)
| Élément | Valeur relevée |
|---|---|
| Machine existante | `AlerteVM`, région `eu-central-1` |
| Type | **`g5.xlarge`** (1 GPU A10G 24 Go, 4 vCPU, 16 Go de RAM — à confirmer dans la console) |
| État | **arrêtée** depuis le 23/11/2026 (arrêt manuel) ; pas d'IP publique tant qu'elle est arrêtée ; pas d'IP élastique |
| Système | Deep Learning Base OSS Nvidia Driver GPU AMI **Ubuntu 22.04** (Python 3.12 à ajouter : §3) |
| Paire de clés | `alerteK` (le fichier doit s'appeler `alerteK.pem`) |
| Protection contre la résiliation / l'arrêt | **désactivées** (à activer) ; aucun rôle IAM ; IMDSv2 « facultatif » |
| Disque | **150 Gio** (`/dev/sda1`), non chiffré, attaché : suffisant (150 Gio = minimum du runbook) |
| Groupe de sécurité | `launch-wizard-8` ; règle entrante **unique** : SSH (TCP 22) depuis **une seule adresse `/32`** (celle du créateur) ; sortant : tout autorisé (accès Internet pour télécharger modèle et paquets : OK côté groupe) |
| **À faire** | **ajouter votre propre IP** (SSH, port 22, source « Mon IP ») sans retirer la règle existante — sinon la connexion expire ; **jamais** `0.0.0.0/0` |
| Quota « Running On-Demand G and VT instances » en `eu-central-1` | **768 vCPU** appliqués (défaut AWS : 0 ; relevé par les organisateurs), utilisation 0 : `g5.2xlarge` (8 vCPU) est permis |
| **État relevé après démarrage (28/11)** | `g5.2xlarge` confirmé (8 CPU, 30 Go de RAM, A10G 23 Go) ; **vLLM déjà installé** par le créateur : conteneur `alerte-vllm` (image `v0.8.5`, `Qwen/Qwen2.5-14B-Instruct-AWQ`, contexte 8 192, **92 % du GPU**, clé d'API dans `/etc/alerte-vllm.env`, port hôte **8000** sur 127.0.0.1) ; modèle déjà en cache dans `/opt/hf-cache` (19 Go) ; disque 85/146 Go utilisés ; Internet OK ; Python 3.10 (3.12 absent) ; Docker 28 + Compose 2.38 ; ni Ollama ni code ALERTE |
| **Conséquence** | **ne pas réinstaller vLLM** : le relancer à **75 %** du GPU (même commande, `--gpu-memory-utilization 0.75`) pour laisser ≈ 5 Go à `bge-m3` ; l'application ALERTE utilise le port **8010** (le 8000 est pris par vLLM) ; `ALERTE_LLM_BASE_URL=http://127.0.0.1:8000/v1` et `ALERTE_LLM_API_KEY` lue depuis `/etc/alerte-vllm.env` sans jamais l'afficher |
| **Non relevé** | prix, crédits disponibles |

**Décision de machine** (ne rien recréer) :
* **Option A — garder `g5.xlarge`** : aucun changement ; 16 Go de RAM **sans marge** : construire la base (OCR + embeddings) **avant** de démarrer vLLM, jamais en même temps ; **non mesuré**.
* **Option B — passer en `g5.2xlarge`** (8 vCPU, 32 Go) : instance **arrêtée**, *Actions → Paramètres de l'instance → Modifier le type d'instance* ; réversible ; exige un quota « G and VT » ≥ 8 vCPU en `eu-central-1` ; **recommandée si le quota le permet**. Prix : à relever sur la page officielle EC2.
**Démarrer l'instance fait facturer** : accord du responsable du projet d'abord. Activer ensuite la protection contre la résiliation (*Actions → Paramètres de l'instance → Modifier la protection contre la résiliation*).

## 1. Avant de créer quoi que ce soit — vérifications en lecture seule (aucun coût)
Avec l'AWS CLI configurée (2FA comprise), dans la région **imposée par les organisateurs : Europe (Francfort), `eu-central-1`** (remplacez `<RÉGION>` ci-dessous par `eu-central-1` ; les quotas et les types d'instance sont propres à chaque région) :
```bash
aws sts get-caller-identity                                       # compte (n'envoyez que les 4 derniers chiffres)
aws ec2 describe-instance-type-offerings --location-type region \
    --filters Name=instance-type,Values=g5.2xlarge,g5.xlarge,g6.2xlarge --region <RÉGION> --output table       # types offerts dans la région
aws service-quotas list-service-quotas --service-code ec2 --region <RÉGION> \
    --query "Quotas[?contains(QuotaName,'G and VT')].[QuotaName,Value]" --output table                          # quota « On-Demand G and VT » (en vCPU)
aws ec2 describe-instances --region <RÉGION> --output table                                                     # machine déjà créée ?
```
**Conditions pour continuer** : (a) `g5.2xlarge` figure dans la liste ; (b) le quota « Running On-Demand G and VT instances » est **≥ 8** (vCPU ; 4 pour `g5.xlarge`) ; sinon *Service Quotas → Amazon EC2 → « Running On-Demand G and VT instances » → Demander une augmentation* (délai : de quelques heures à quelques jours, non garanti) ; (c) le **prix** est relevé sur la page officielle EC2 de la région (je n'en donne aucun) et les **crédits** sont visibles dans *Billing → Credits* (les « 20 000 USD » annoncés ne sont **pas** présumés disponibles) ; (d) **l'instance pourra sortir sur Internet** (voir §3, test `curl`) : sans accès à `huggingface.co` et aux dépôts de paquets, rien ne s'installe.
**Si une condition échoue : arrêtez-vous et dites-le moi**, ne contournez pas.

## 2. Créer l'instance (console AWS → EC2 → Lancer une instance)
**Seulement après accord du responsable du projet** (cela facture).
| Champ de la console | Valeur |
|---|---|
| Nom | `alerte-gpu` |
| Images (AMI) | *Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 24.04)* (recherche « Deep Learning Base OSS Nvidia ») |
| Type d'instance | `g5.2xlarge` |
| Paire de clés | créer `alerte-gpu` (RSA, `.pem`) ; sur votre poste : `chmod 400 alerte-gpu.pem` (Windows : restreindre les droits du fichier à votre compte) |
| Paramètres réseau | VPC par défaut ; **attribuer une IP publique : Activer** ; groupe de sécurité *nouveau* : **une seule règle entrante : SSH, TCP 22, Source = Mon IP** |
| Stockage | volume racine **200 Gio, gp3** ; chiffrement : activé (par défaut) |
| Détails avancés | **Protection contre la résiliation : Activer** ; Comportement à l'arrêt : *Arrêter* ; rôle IAM : aucun |
| Balises | `Project=ALERTE`, `Owner=<votre nom>` |
Équivalent CLI (à n'exécuter qu'avec accord) : `aws ec2 run-instances --region <RÉGION> --instance-type g5.2xlarge --image-id <AMI-ID> --key-name alerte-gpu --security-group-ids <SG-ID> --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=200,VolumeType=gp3}' --disable-api-termination --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=alerte-gpu}]'` (l'identifiant d'AMI se lit dans la console ; le nom du périphérique racine peut différer : à vérifier).
**Notez** : l'IP publique (elle **change à chaque arrêt/démarrage**), la région, l'identifiant de l'instance, l'heure de démarrage.

## 3. Préparer la machine (SSH)
```bash
ssh -o ServerAliveInterval=30 -i alerteK.pem ubuntu@<IP-PUBLIQUE>
# --- sur l'instance ---
nvidia-smi                                   # doit afficher « NVIDIA A10G » et ≈ 23 Go de mémoire
docker --version && docker compose version   # si « compose » est absent : sudo apt-get install -y docker-compose-v2
curl -sI https://huggingface.co | head -1    # sortie Internet : doit afficher « HTTP/2 200 » (ou 301/302) — sinon ARRÊT : voir §1 (d)
sudo apt-get update
# Ubuntu 22.04 (cas d'AlerteVM) : Python 3.12 vient d'un dépôt supplémentaire. Sur Ubuntu 24.04 cette ligne est inutile.
sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt-get update
sudo apt-get install -y git tmux python3.12 python3.12-venv python3-pip \
     tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng tesseract-ocr-ara libpango-1.0-0 libpangoft2-1.0-0 rsync
python3.12 --version                          # 3.12.x   (attention : `python3 --version` affiche encore 3.10 sur 22.04 : c'est normal, utiliser python3.12)
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash && . ~/.nvm/nvm.sh && nvm install 22     # Node 22 pour construire l'interface
```
Vérification : `nvidia-smi`, `python3 --version`, `node --version` (v22.x), `tesseract --list-langs` (ara, eng, fra).

## 4. Envoyer le code et les PDF (depuis VOTRE poste)
```bash
# code : si le dépôt est accessible depuis l'instance
ssh -i alerteK.pem ubuntu@<IP> "git clone --branch Rudy https://github.com/RudyTchamba/ALERTE.git ~/ALERTE"
# sinon (dépôt privé) : copie directe, sans dépendances ni données
rsync -avz --exclude node_modules --exclude .venv --exclude data --exclude data-kb-build --exclude '.env' \
      -e "ssh -i alerteK.pem" alerte-platform/ ubuntu@<IP>:~/ALERTE/alerte-platform/
# PDF sources (≈ 136 Mo, hors dépôt) :
rsync -avz -e "ssh -i alerteK.pem" <dossier local>/alerte/data/docs/ ubuntu@<IP>:~/pdf/
```
(La branche et l'URL du dépôt sont celles de `git remote -v` au 27/11/2026 ; ajustez si elles changent.) Vérification sur l'instance : `ls ~/ALERTE/alerte-platform/scripts && ls ~/pdf/CM | wc -l` → `17`.

## 5. Démarrer les modèles (sur l'instance, dans tmux)
```bash
cd ~/ALERTE/alerte-platform
tmux new -s modeles
# Embeddings (Ollama sur le GPU, limité à 127.0.0.1) :
docker compose -f deploy/compose.models.yml -f deploy/compose.models.gpu.yml up -d ollama
docker compose -f deploy/compose.models.yml exec ollama ollama pull bge-m3
# Génération (vLLM, 75 % du GPU, contexte 8 192, limité à 127.0.0.1:8001) :
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ VLLM_GPU_UTILIZATION=0.75 VLLM_MAX_MODEL_LEN=8192 \
  docker compose -f deploy/compose.models.yml -f deploy/compose.models.gpu.yml --profile vllm up -d vllm
docker compose -f deploy/compose.models.yml --profile vllm logs -f vllm      # attendre « Application startup complete » (téléchargement du modèle : 5 à 15 min) ; Ctrl-C pour quitter les journaux
curl http://127.0.0.1:11434/v1/models                 # bge-m3
curl http://127.0.0.1:8001/v1/models                  # Qwen/Qwen2.5-14B-Instruct-AWQ
nvidia-smi                                            # mémoire utilisée : notez-la (vLLM + Ollama)
```
**Limites connues** : (1) l'image vLLM est figée en `v0.8.5` (compatible Qwen2.5 ; un autre modèle peut exiger plus récent) ; (2) ce serveur vLLM ne demande **pas** de clé d'API, il n'écoute que sur `127.0.0.1` ; (3) si `vllm` échoue par manque de mémoire GPU, baissez `VLLM_GPU_UTILIZATION` (0.70) ou `VLLM_MAX_MODEL_LEN` (6144) et relancez.
*Alternative déjà scriptée* (vLLM seul avec clé d'API, **sans** partage du GPU avec Ollama) : `scripts/aws/setup_vllm.sh` (voir [aws-gpu-model.md](../runbooks/aws-gpu-model.md)) ; dans ce cas, mettez les embeddings sur le CPU de l'instance.

## 6. Installer et configurer l'application (sur l'instance)
```bash
cd ~/ALERTE/alerte-platform
python3.12 scripts/setup.py --skip-frontend           # crée backend/.venv, installe les dépendances, crée backend/.env
cd frontend && . ~/.nvm/nvm.sh && npm ci && npm run build && cd ..        # construit l'interface (servie par l'API)
```
Éditez `backend/.env` (`nano backend/.env`) — **valeurs exactes** :
```ini
ALERTE_DATA_DIR=/home/ubuntu/alerte-data
ALERTE_LLM_MODE=openai_compat
ALERTE_LLM_BASE_URL=http://127.0.0.1:8001/v1
ALERTE_LLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
ALERTE_EMBED_PROVIDER=openai_compat
ALERTE_EMBED_BASE_URL=http://127.0.0.1:11434/v1
ALERTE_EMBED_MODEL=bge-m3
ALERTE_EMBED_BATCH_SIZE=16
ALERTE_TESSDATA_DIR=/usr/share/tesseract-ocr/5/tessdata
ALERTE_OCR_LANGS=ara+fra+eng
ALERTE_CORS_ORIGINS=http://localhost:8000
```
(Si `/usr/share/tesseract-ocr/5/tessdata` n'existe pas : `dpkg -L tesseract-ocr-fra | grep traineddata` donne le bon dossier.) **Aucune clé n'est nécessaire** ici ; aucun secret ne va dans ce fichier tant que vLLM est sans clé.
```bash
python3.12 scripts/doctor.py          # attendu : 0 BLOQUANT (« modèle … servi » pour génération ET embeddings)
python3.12 scripts/hardware_probe.py --label aws-g5-2xlarge --out ~/rapports      # à me renvoyer
```

## 7. Mesurer, construire la base, démarrer
```bash
cd ~/ALERTE/alerte-platform
python3.12 scripts/llm_bench.py --url http://127.0.0.1:8001/v1 --model Qwen/Qwen2.5-14B-Instruct-AWQ --calls 5 --out ~/rapports/bench-14b.json     # secondes par appel : à me renvoyer
python3.12 scripts/llm_bench.py --url http://127.0.0.1:8001/v1 --model Qwen/Qwen2.5-14B-Instruct-AWQ --calls 6 --parallel 2 --out ~/rapports/bench-14b-par2.json
cd backend && source .venv/bin/activate
python scripts/build_kb_from_pdfs.py --country CM --src ~/pdf/CM --publish      # espace + base + vecteurs + publication ; COPIER le jeton affiché
tmux new -s alerte
python -m uvicorn app.main:app_factory --factory --host 127.0.0.1 --port 8000    # à laisser tourner (Ctrl-b d pour détacher)
curl http://127.0.0.1:8000/api/v1/health
```

## 8. Se connecter depuis votre poste
```bash
ssh -i alerteK.pem -N -L 8000:127.0.0.1:8000 ubuntu@<IP-PUBLIQUE>      # à laisser ouvert
```
Ouvrez http://localhost:8000/access → *Se connecter avec un jeton* → jeton noté à l'étape 7. Puis suivez le [parcours B](../runbooks/guide-parcours-A-et-B.md) (les agents utilisent `Qwen/Qwen2.5-14B-Instruct-AWQ`). Importer l'espace, les mandats et le scénario : commandes #18 à #22 du [catalogue](../runbooks/catalogue-commandes-et-fichiers.md), à lancer **sur l'instance** avec `--api http://127.0.0.1:8000`.

## 9. Contrôle des coûts et arrêt
* Une instance GPU facture tant qu'elle est **démarrée** : `aws ec2 stop-instances --instance-ids <id> --region <RÉGION>` (ou *Console → Arrêter*) après chaque session. **Jamais « Résilier »** (la protection l'empêche). Notez heure de démarrage et d'arrêt.
* Après un arrêt puis un démarrage : l'IP change ; les conteneurs redémarrent seuls (`restart: unless-stopped`), **pas** l'application : relancez le `uvicorn` du §7.
* Le disque (200 Go) est facturé même à l'arrêt.

## 10. Ce que vous me renvoyez
`alerte-hardware-aws-g5-2xlarge.txt/.json`, `bench-14b.json`, `bench-14b-par2.json`, la sortie de `nvidia-smi` pendant que vLLM et Ollama tournent, la sortie de `doctor.py`, et **toute erreur telle quelle**. Avec cela je remplis [dimensionnement.md](dimensionnement.md) et je valide ou corrige ce choix de machine.

## Sécurité
Ports ouverts : **22 depuis votre IP seulement**. Aucun secret dans le dépôt, les captures ou le chat. Les données de démonstration sont publiques (aucune donnée personnelle).

# Modèle plus performant sur AWS (option A) — sans toucher à l'installation locale

**Principe.** Seul le modèle de *génération* (les agents, le projet de texte, le juge IA) part sur une machine AWS avec
GPU. L'application, la base, les documents et les **embeddings** (recherche) restent sur le portable. On bascule entre
les deux modèles avec une commande, et on revient au local à tout moment.

```
Portable : ALERTE (backend + interface + base) ──tunnel SSH──► EC2 GPU : vLLM (Qwen2.5-32B-Instruct-AWQ)
           Ollama local : bge-m3 (recherche) + qwen2.5:7b (repli local)
```

Ce qui ne change jamais : la base de données, les exercices existants (le modèle utilisé est inscrit dans le registre
de chaque exercice), Ollama local. Chaque bascule sauvegarde `backend/.env` (`backend/.env.bak-…`).

## 1. Préparer le compte AWS (une fois, à faire tôt)

1. Console AWS → **Service Quotas** → *Amazon EC2* → « **Running On-Demand G and VT instances** » : demander au moins
   **8 vCPU** dans ta région (un compte neuf est souvent à 0 ; l'accord peut prendre de quelques heures à quelques jours).
2. Choisir la région. `me-central-1` (Émirats) renforce l'argument de souveraineté pour le jury, mais les GPU n'y sont
   pas toujours disponibles : à défaut, `eu-west-1`, `eu-central-1` ou `us-east-1`.
3. **EC2 → Paires de clés → Créer** (format `.pem`), puis sur le portable : `chmod 400 ~/Téléchargements/alerte-gpu.pem`.

## 2. Lancer l'instance

EC2 → **Lancer une instance** :

| Champ | Valeur |
|---|---|
| Nom | `alerte-gpu` |
| AMI | **Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04 ou 24.04)** (pilotes, Docker, toolkit NVIDIA inclus) |
| Type | **g6e.xlarge** (L40S 48 Go) → Qwen2.5-32B · ou **g5.xlarge** (A10G 24 Go) → Qwen2.5-14B |
| Paire de clés | `alerte-gpu` |
| Réseau / groupe de sécurité | **SSH (22) depuis « Mon IP » uniquement**. N'ouvre AUCUN autre port. |
| Stockage | **150 Go** gp3 (l'AMI occupe déjà ~60 Go ; 100 Go ne suffisent pas avec l'image vLLM et le modèle) |

Note l'**IP publique** de l'instance : elle **change à chaque arrêt/démarrage** (sauf IP élastique) ; penser à mettre à
jour la commande du tunnel et, si ton IP à toi change (VPN, WARP), la règle SSH du groupe de sécurité. Les tarifs varient selon la région : vérifie-les sur la page de prix EC2, et
**arrête l'instance** (« Arrêter », pas « Résilier ») quand tu ne t'en sers pas : on ne paie alors que le disque.

## 3. Installer le serveur de modèle (sur l'instance)

Depuis le dossier `alerte-platform` du portable :

```bash
scp -i ~/Téléchargements/alerte-gpu.pem scripts/aws/setup_vllm.sh ubuntu@<IP>:~
ssh -o ServerAliveInterval=30 -i ~/Téléchargements/alerte-gpu.pem ubuntu@<IP>
# sur l'instance, DANS tmux (une coupure SSH n'arrête pas l'installation ; revenir avec `tmux attach -t vllm`) :
tmux new -s vllm
MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ bash setup_vllm.sh      # g5.xlarge : MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
```

Le script choisit seul la longueur de contexte (16 384 jetons si le GPU a au moins 40 Go, 8 192 sur une A10G ; forcer
avec `MAX_MODEL_LEN=…`) et refuse de démarrer s'il reste moins de 35 Go libres sur le disque.

Le script vérifie le GPU, génère une **clé d'API**, lance vLLM (qui redémarre tout seul avec l'instance), attend le
modèle (5 à 15 min la première fois) et affiche la clé et les commandes suivantes. **Ne colle jamais cette clé (ni la
sortie de `docker logs`, qui la contient) dans un chat ou une capture** ; pour en changer : `sudo rm /etc/alerte-vllm.env`
puis relancer le script, et refaire `init-aws`. vLLM n'écoute que sur
`127.0.0.1` : il n'est **pas** joignable depuis Internet.

## 4. Relier le portable (tunnel SSH)

Dans un terminal du portable, à laisser ouvert pendant l'utilisation :

```bash
ssh -o ServerAliveInterval=30 -i ~/Téléchargements/alerte-gpu.pem -N -L 8001:127.0.0.1:8000 ubuntu@<IP>
```

Le modèle AWS est alors visible sur le portable à l'adresse `http://localhost:8001/v1`.

## 5. Enregistrer le préréglage AWS et basculer

Depuis `alerte-platform` :

```bash
python3 scripts/llm_target.py init-aws --url http://localhost:8001/v1 --model Qwen/Qwen2.5-32B-Instruct-AWQ --key <clé affichée à l'étape 3>
python3 scripts/llm_target.py status      # « local → ok » et « aws → ok »
python3 scripts/llm_target.py aws         # refuse si le serveur AWS ne répond pas : rien n'est modifié
```

Puis **redémarrer le backend** : `Ctrl+C` dans le terminal de `dev.py`, puis `python3 scripts/dev.py --host`.

**Revenir au local** : `python3 scripts/llm_target.py local`, puis redémarrer le backend. C'est tout.

## 6. Mesurer l'apport du grand modèle

Avec le modèle AWS actif, rejouer le même exercice et comparer à EX-022 (joué avec le 7B local) :

```bash
cd backend
.venv/bin/python scripts/fix_cameroon_kb.py --token <jeton animateur> --rerun --ref EX-022 \
    --title "Crue de l'Extrême-Nord — Qwen2.5-32B (AWS)"
```

Le script affiche les lacunes disparues, nouvelles et confirmées. Le taux de citations valides et le juge IA se
comparent ensuite dans l'interface (Salle de simulation, Évaluation). Le registre de chaque exercice garde le modèle et
le serveur utilisés : les deux résultats restent traçables.

## Option : les deux modèles en même temps

Sans basculer tout le système, on peut donner le modèle AWS à **certains agents seulement** : écran *Agents* → profil
de modèle `openai_compat`, modèle `Qwen/Qwen2.5-32B-Instruct-AWQ`, *endpoint* `ALERTE_LLM_AWS_BASE_URL`, et
`{"api_key_ref": "ALERTE_LLM_AWS_API_KEY"}` dans *extra* ; puis attribuer ce profil aux agents voulus.

## Dépannage

| Symptôme | Cause / remède |
|---|---|
| `llm_target.py aws` : « injoignable » | le tunnel SSH n'est pas ouvert (étape 4) ou l'instance est arrêtée |
| « refusé (HTTP 401) » | mauvaise clé : la relire sur l'instance avec `sudo cat /etc/alerte-vllm.env` |
| « modèle absent » | le nom passé à `init-aws` diffère de celui du serveur : `--model` doit être identique à `MODEL` |
| `setup_vllm.sh` : vLLM s'arrête (mémoire) | modèle trop gros pour le GPU : 14B sur g5, ou `MAX_MODEL_LEN=8192` |
| vLLM : `Engine core initialization failed` | lire la vraie cause plus haut : `docker logs alerte-vllm 2>&1 \| grep -iE "error\|memory\|space"` ; vérifier `df -h /` |
| `df -h /` à 100 %, `No space left on device` | `docker stop alerte-vllm` ; agrandir le volume (EC2 → Volumes → Modifier → 150 Go, sans arrêt) ; puis `sudo TMPDIR=/opt/dlami/nvme growpart /dev/nvme0n1 1` (le `TMPDIR` évite l'échec « failed to make temp dir ») et `sudo resize2fs /dev/nvme0n1p1` ; supprimer les téléchargements partiels : `sudo find /opt/hf-cache -name "*.incomplete" -delete` ; relancer le script. **Ne jamais agrandir la partition 15** (`/boot/efi`) |
| Connexion SSH coupée pendant l'installation | relancer le script dans `tmux` (étape 3) ; `ServerAliveInterval=30` ; garder VPN/WARP dans le même état |
| `ssh` bloqué, sans réponse | la règle SSH du groupe de sécurité ne correspond pas à ton IP actuelle (IPv4 vs IPv6, VPN) : mettre `<ton IPv4>/32` |
| « Insufficient capacity » au lancement | essayer une autre zone de disponibilité (sous-réseau) ou un autre type (g5.xlarge, g6.xlarge) ou une autre région |
| Agents « modèle indisponible » pendant un exercice | tunnel coupé : le rouvrir, ou `llm_target.py local` + redémarrage |

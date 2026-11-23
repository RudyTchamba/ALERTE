#!/usr/bin/env bash
# Installe un serveur de modèle vLLM (API compatible OpenAI) sur une instance EC2 GPU, pour ALERTE.
#
# Prérequis : AMI « Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu) » (pilotes NVIDIA, Docker et
# nvidia-container-toolkit déjà installés), disque racine >= 100 Go.
#
# Usage (sur l'instance) :
#   MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ bash setup_vllm.sh      # g6e.xlarge (L40S 48 Go) — défaut
#   MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ bash setup_vllm.sh      # g5.xlarge  (A10G 24 Go)
# Lancer dans tmux (`tmux new -s vllm`) : une coupure SSH n'interrompt alors pas l'installation.
#
# Sécurité : le serveur n'écoute QUE sur 127.0.0.1:8000 (jamais exposé à Internet) ; on y accède par tunnel SSH.
# Il exige une clé d'API, générée une fois et gardée dans /etc/alerte-vllm.env (lisible par root seulement).
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-32B-Instruct-AWQ}"
IMAGE="${VLLM_IMAGE:-vllm/vllm-openai:v0.8.5}"
ENV_FILE=/etc/alerte-vllm.env

echo "== 1/5 Vérification du GPU et de Docker"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || { echo "GPU NVIDIA introuvable : mauvaise AMI ou mauvais type d'instance"; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker indisponible : utiliser l'AMI Deep Learning Base (Ubuntu)"; exit 1; }
# Contexte : 16384 jetons si le GPU a >= 40 Go, sinon 8192 (A10G 24 Go : 16384 laisse trop peu de marge mémoire)
GPU_MIB="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')"
MAX_LEN="${MAX_MODEL_LEN:-$([ "${GPU_MIB:-0}" -ge 40000 ] && echo 16384 || echo 8192)}"
echo "  contexte max : $MAX_LEN jetons"
# Disque : l'AMI occupe déjà ~60 Go ; image vLLM (~10 Go) + modèle (10 à 20 Go) exigent ~35 Go libres
FREE_GB="$(df -BG --output=avail / | tail -1 | tr -dc '0-9')"
if [ "${FREE_GB:-0}" -lt 35 ]; then
  echo "Disque presque plein (${FREE_GB} Go libres, 35 nécessaires). Agrandir le volume à 150 Go (EC2 → Volumes →"
  echo "Modifier), puis : sudo TMPDIR=/opt/dlami/nvme growpart /dev/nvme0n1 1 && sudo resize2fs /dev/nvme0n1p1"
  exit 1
fi
docker run --rm --gpus all "$IMAGE" nvidia-smi >/dev/null 2>&1 || echo "  (premier téléchargement de l'image vLLM : quelques minutes)"

echo "== 2/5 Clé d'API (conservée entre deux lancements)"
if ! sudo test -f "$ENV_FILE"; then
  KEY="$(openssl rand -hex 24)"
  echo "VLLM_API_KEY=$KEY" | sudo tee "$ENV_FILE" >/dev/null
  sudo chmod 600 "$ENV_FILE"
fi
KEY="$(sudo sed -n 's/^VLLM_API_KEY=//p' "$ENV_FILE")"

echo "== 3/5 Lancement de vLLM ($MODEL) — redémarre tout seul avec l'instance"
sudo mkdir -p /opt/hf-cache
docker rm -f alerte-vllm >/dev/null 2>&1 || true
docker run -d --name alerte-vllm --restart unless-stopped --gpus all --ipc=host \
  -p 127.0.0.1:8000:8000 -v /opt/hf-cache:/root/.cache/huggingface \
  "$IMAGE" --model "$MODEL" --served-model-name "$MODEL" --max-model-len "$MAX_LEN" \
  --gpu-memory-utilization 0.92 --api-key "$KEY" >/dev/null

echo "== 4/5 Attente du modèle (téléchargement + chargement : 5 à 15 min la première fois)"
for i in $(seq 1 180); do
  if curl -sf -H "Authorization: Bearer $KEY" http://127.0.0.1:8000/v1/models >/dev/null; then break; fi
  if ! docker ps --format '{{.Names}}' | grep -q '^alerte-vllm$'; then
    echo "vLLM s'est arrêté. Dernières lignes du journal :"; docker logs --tail 40 alerte-vllm; exit 1
  fi
  sleep 10
done
curl -sf -H "Authorization: Bearer $KEY" http://127.0.0.1:8000/v1/models >/dev/null || { echo "Délai dépassé : docker logs alerte-vllm"; exit 1; }

echo "== 5/5 Test d'une réponse JSON"
curl -s -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" http://127.0.0.1:8000/v1/chat/completions \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Réponds en JSON {\\\"ok\\\":true}\"}],\"max_tokens\":20,\"temperature\":0}" \
  | head -c 300; echo

cat <<EOF

✅ Serveur prêt.
   Modèle   : $MODEL
   Clé d'API: $KEY      (à recopier dans la commande init-aws ci-dessous, ne pas la partager)

Sur TON PORTABLE :
  1) tunnel (laisser ouvert) :  ssh -i <ta-cle.pem> -N -L 8001:127.0.0.1:8000 ubuntu@<IP-publique>
  2) préréglage :              python3 scripts/llm_target.py init-aws --url http://localhost:8001/v1 --model $MODEL --key $KEY
  3) bascule :                 python3 scripts/llm_target.py aws   (puis redémarrer dev.py)
EOF

# Sonde matérielle — savoir quelle machine peut héberger les modèles

**Pourquoi.** Avant de choisir un modèle de langage ou une instance AWS, il faut connaître les faits des machines disponibles
(GPU, VRAM, RAM, disque, Docker, WSL2, Ollama). La sonde `scripts/hardware_probe.py` relève ces faits. Elle **ne mesure aucune
performance** et ne modifie rien sur la machine.

**Ce que le rapport contient / ne contient pas.** Il contient : système, CPU, RAM, disque (volume courant), GPU et VRAM, versions
de Docker/Compose/Ollama/Git/Python/Node/Tesseract, WSL2 (Windows), noms des modèles Ollama installés. Il ne contient **ni nom de
machine, ni nom d'utilisateur, ni adresse IP/MAC, ni variable d'environnement, ni clé**. Relisez-le tout de même avant de l'envoyer.

**Prérequis.** Python 3.9 ou plus récent. Aucune dépendance à installer. Si Python est absent, voir « Sans Python » plus bas.

| | |
|---|---|
| Durée | quelques secondes (jusqu'à ~40 s sous Windows : PowerShell) |
| Fichiers produits | `alerte-hardware-<étiquette>.txt` (lisible) et `.json` (comparaison) dans le dossier `--out` |
| Réseau | aucun, sauf un `GET http://localhost:11434/api/tags` local pour lister les modèles Ollama |
| Écrase des données | uniquement un ancien rapport du même nom |

## 1. Coéquipier sous Linux

Terminal, depuis la racine du dépôt (`alerte-platform/`) :

```bash
git pull                                   # facultatif : pour récupérer le script (ou copier seulement scripts/hardware_probe.py)
python3 scripts/hardware_probe.py --label linux-gpu --out ~/alerte-rapports
```

Vérification : le dernier message affiche « Rapports écrits : … ». Envoyez `alerte-hardware-linux-gpu.txt` **et** `.json`.

Si `nvidia-smi` est absent alors que la machine a un GPU NVIDIA : le pilote n'est pas installé (le rapport le dira). Ne l'installez
pas pour la sonde : signalez-le simplement.

## 2. Coéquipier sous Windows

PowerShell (pas besoin d'être administrateur), depuis le dossier `alerte-platform` :

```powershell
python scripts\hardware_probe.py --label windows-gpu --out $HOME\alerte-rapports
# si « python » n'est pas reconnu :
py -3 scripts\hardware_probe.py --label windows-gpu --out $HOME\alerte-rapports
```

Notes :
- La VRAM affichée par Windows (`AdapterRAM`) est plafonnée à 4 Go ; la sonde s'appuie sur `nvidia-smi` (installé avec le pilote
  NVIDIA). S'il est absent, la VRAM réelle est **inconnue** : ouvrez le Gestionnaire des tâches → Performances → GPU et notez
  « Mémoire GPU dédiée ».
- La sonde indique si WSL2 est présent et la liste de ses distributions ; si Docker Desktop est installé, elle donne ses versions.
- **Cette sonde a été écrite pour Windows mais n'a pas encore été exécutée sur Windows** (seulement sur Linux). Si une ligne est
  manquante ou erronée, envoyez la sortie telle quelle : c'est une information utile, pas un échec.

## 3. macOS (facultatif)

```bash
python3 scripts/hardware_probe.py --label macos --out ~/alerte-rapports
```
Sur Apple Silicon la mémoire est unifiée : la RAM totale tient lieu de VRAM. Non testé sur macOS.

## 4. Instance AWS (à exécuter par le coéquipier qui détient les accès)

Il faut qu'une instance existe déjà ; **cette procédure ne crée aucune ressource**. Sur l'instance, en SSH :

```bash
# 1) récupérer le script (au choix : git clone du dépôt, ou scp du seul fichier scripts/hardware_probe.py)
python3 scripts/hardware_probe.py --label aws-<type-instance> --out ~/alerte-rapports
# 2) informations complémentaires propres à AWS (aucune donnée personnelle)
curl -s -m 3 http://169.254.169.254/latest/meta-data/instance-type ; echo     # type d'instance (IMDS)
nvidia-smi --query-gpu=name,memory.total --format=csv
```
Si le curl n'affiche rien (IMDSv2 exigé), notez le type d'instance affiché dans la console EC2. Envoyez aussi : la **région**, et la
valeur des quotas « Running On-Demand G and VT instances » (console AWS → Service Quotas → EC2), car sans quota aucune instance GPU
ne démarrera. **Ne démarrez ni ne créez aucune instance sans l'autorisation du responsable du projet.**

## 5. Sans Python

- **Linux/macOS** : `uname -a ; lscpu | head -20 ; free -h ; df -h . ; nvidia-smi ; docker --version ; ollama --version`
- **Windows (PowerShell)** :
  ```powershell
  Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
  Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,TotalVisibleMemorySize,FreePhysicalMemory
  nvidia-smi ; docker --version ; wsl --status ; ollama --version
  ```
  Ne collez pas la sortie de `hostname`, `ipconfig` ou `whoami`.

## 6. Ce qu'on fait des rapports

Comparer les machines (VRAM par carte, RAM, disque, Linux ou Windows, Docker/WSL2) **avant** de décider laquelle héberge la génération et
laquelle, éventuellement, les embeddings. Le dimensionnement par modèle (poids, quantification, cache de contexte, concurrence) est un
document distinct, rempli à partir de ces chiffres : il n'est pas encore écrit, et aucune instance AWS ne doit être recommandée avant.

*Vérification : `hardware_probe.py` exécuté sur Linux (cette machine de développement, sans GPU) : [OK]. Windows, macOS, AWS, GPU NVIDIA : NOT TESTED.*

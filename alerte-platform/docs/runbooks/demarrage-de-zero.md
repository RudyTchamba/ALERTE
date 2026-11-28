# Démarrer ALERTE de zéro (après un simple `git clone`)

Ce guide part d'un dossier **vide** : vous venez de cloner le dépôt, vous n'avez **rien installé, rien construit**. Vous allez tout faire vous-même : configurer, construire la base de connaissances, la vérifier, la publier, puis tester.

## 1. Ce que contient le clone, et ce qu'il ne contient PAS
| Élément | Dans le clone ? | Explication |
|---|---|---|
| `alerte-platform/knowledge_bases/` | **oui, mais ce n'est PAS la base construite** | données d'auteur versionnées : métadonnées des documents (`curation/`), 14 mandats, consignes des agents, 50 questions d'évaluation. **Aucun passage, aucun vecteur, aucun index.** |
| La **base construite** (documents découpés, vecteurs, index) | **non** | elle se construit sur votre machine à partir des PDF et vit dans `alerte-platform/backend/data/` (ignoré par git) |
| Les **PDF sources** (44 fichiers, ≈ 136 Mo ; 17 pour le Cameroun) | **non** | droits de redistribution non confirmés : l'équipe vous les transmet à part (dossier `alerte/data/docs/` avec les sous-dossiers `CM`, `AE`, `GL`, `ITU`). **Obtenez-les avant de commencer** |
| Le pack de démonstration `demo/rising-waters/` (scénarios, agents, mandats, actions) | **oui** | déjà généré : vous n'avez **pas** à le régénérer |
| `backend/.env` (votre configuration) | **non** | à créer vous-même (étape 3) |
| Python, Node, Tesseract, Ollama, modèles | **non** | à installer vous-même (étapes 2 et 4) |

**Dossier des PDF** : dans les commandes ci-dessous, `<PDF>` désigne le dossier qui contient les sous-dossiers `CM`, `AE`… (par exemple `~/alerte/data/docs`). Seul `<PDF>/CM` est nécessaire pour la démonstration Rising Waters.

## 2. Installer (Terminal 1, dossier `alerte-platform`)
Choisissez votre système : [Linux](../deploiement/linux.md) ou [Windows](../deploiement/windows.md) (prérequis : Python 3.12, Node 22, Git, Tesseract avec `fra`, `eng`, `ara`). Puis :
```bash
cd alerte-platform
python3 scripts/setup.py          # crée backend/.venv, installe les dépendances, copie .env.example vers backend/.env, npm ci   (Windows : python scripts\setup.py)
python3 scripts/doctor.py         # lisez-le : les lignes BLOQUANT se corrigent avant d'aller plus loin
```
Durée : 5 à 15 minutes. Vérification : `doctor.py` ne signale plus que l'absence de serveur de modèles (étape 4).

## 3. Configurer `backend/.env`
Ouvrez `backend/.env` (créé à l'étape 2) et renseignez **au minimum** (explications : [configuration-env.md](configuration-env.md)) :
```ini
ALERTE_EMBED_BASE_URL=http://localhost:11434/v1
ALERTE_EMBED_MODEL=bge-m3
ALERTE_TESSDATA_DIR=<chemin ABSOLU du dossier tessdata contenant ara, fra, eng>      # Linux : souvent /usr/share/tesseract-ocr/5/tessdata
```
Les variables du modèle de **génération** (`ALERTE_LLM_BASE_URL`, `ALERTE_LLM_MODEL`) ne servent qu'au **parcours B** (modèle réel) : laissez-les pour plus tard.
Après toute modification du `.env` : **redémarrez** le backend.

## 4. Installer le serveur d'embeddings (obligatoire pour construire la base)
Sans vecteurs, la base ne peut **pas** être publiée. Avec Ollama ([linux.md](../deploiement/linux.md) §2 ou [windows.md](../deploiement/windows.md) §3) :
```bash
ollama pull bge-m3
curl http://localhost:11434/v1/models       # doit lister bge-m3
python3 scripts/doctor.py                   # « Serveur de embeddings … modèle bge-m3 servi » : OK
```

## 5. Construire, vérifier et publier la base du Cameroun (CM)
Une seule commande, **reprenable** (Terminal 1, `backend/`, venv activé) :
```bash
cd backend
source .venv/bin/activate                    # Windows : .\.venv\Scripts\Activate.ps1
python scripts/build_kb_from_pdfs.py --country CM --src <PDF>/CM 2>&1 | tee ../build-cm.log
```
(`tee` conserve la sortie dans `backend/../build-cm.log` : si vous ratez le jeton à l'écran, `grep "jeton propriétaire" ../build-cm.log` le retrouve ; **ce fichier contient un secret** : protégez-le avec `chmod 600 ../build-cm.log` puis supprimez-le une fois le jeton noté. **N'interrompez pas** la construction avec Ctrl+C : si cela arrive, relancez la même commande, elle reprend.)
Elle enchaîne : contrôles (PDF présents, embeddings joignables et modèle servi) → création de l'**espace de travail** (**copiez le jeton propriétaire affiché : il ne l'est qu'UNE fois**) → création de la base `CM` → copie des 17 PDF → enregistrement → métadonnées → **construction** (extraction/OCR, découpage, vecteurs, index, cohérence) → état final.
**Durée** : de 20 minutes à plusieurs heures selon la machine (OCR et embeddings sur CPU : lent ; avec GPU : bien plus rapide). **Si elle s'arrête** (erreur, coupure, `ReadTimeout`), relancez **la même commande** : elle reprend. Contre un `ReadTimeout`, dans `backend/.env` : `ALERTE_EMBED_BATCH_SIZE=2` et `ALERTE_EMBED_TIMEOUT_S=300`.

**Valider vous-même** (obligatoire avant de publier) :
```bash
python -m app.cli knowledge status --country CM --documents
python -m app.cli knowledge check --country CM
```
Attendu : 17 documents **prêts**, aucun en échec ; **vecteurs = passages** (par exemple `1351/1351` : le nombre exact peut varier légèrement selon l'OCR) ; les six contrôles de `check` à OK. Un document « à relire » (page d'OCR douteuse) n'empêche pas la publication ; **un document en échec ou un vecteur manquant l'empêche** (le message le dit).

**Publier** (vous-même) :
```bash
python -m app.cli knowledge publish --country CM --note "v1 : base reconstruite à partir des PDF"
python -m app.cli knowledge kb-list          # CM … ready = construction COMPLÈTE (cela ne dit PAS si la base est publiée)
python -m app.cli knowledge status --country CM | grep -E "active_version|general_status"    # active_version: 1 = publiée ; None = pas encore publiée
```
(ou `python scripts/build_kb_from_pdfs.py --country CM --src <PDF>/CM --publish`, qui publie à la fin si tout est complet.)
**Test de la barrière** : tant que des vecteurs manquent, `publish` répond « vectorisation incomplète » : c'est voulu.

## 6. Démarrer l'application (Terminal 2, `alerte-platform`)
```bash
cd alerte-platform && python3 scripts/dev.py          # backend :8000 + interface :5173 ; Ctrl-C arrête les deux
curl http://localhost:8000/api/v1/health              # {"status":"ok"}
```
Ouvrez http://localhost:5173/access → **« Se connecter avec un jeton »** → collez le **jeton propriétaire** noté à l'étape 5. Vous retrouvez l'espace et la base CM publiée (page *Bases de connaissances*).
Si vous avez perdu le jeton : le jeton d'origine n'est **pas récupérable**, mais quiconque a accès au dossier de données peut en **émettre un nouveau** (les anciens restent valables) : `python -m app.cli workspace new-token --label "secours"` (dossier `backend/`, venv activé ; le jeton s'affiche UNE fois, notez-le dans un endroit privé).

## 7. Préparer le reste de la démonstration et tester
Avec le jeton (Terminal 1, `backend/`) :
```bash
python scripts/seed_rising_waters.py --token <jeton> --from 2 --until 4 --allow-missing-kbs      # pays, institutions, actions, 14 mandats « proposés »
```
Puis **suivez le [parcours A (SANS IA)](guide-parcours-A-et-B.md)** depuis A8 (valider des mandats) ; les valeurs de chaque champ sont dans le [guide champ par champ](guide-champs-formulaires.md) ; toutes les commandes sont dans le [catalogue](catalogue-commandes-et-fichiers.md).
Le **parcours B** (modèle réel) exige un serveur de génération et le **nom exact** du modèle servi : ne le lancez pas avec un petit modèle en croyant valider les agents.

## 8. Si quelque chose ne marche pas
| Symptôme | Cause probable | Correction |
|---|---|---|
| `build_kb_from_pdfs.py` : « aucun PDF trouvé » | mauvais dossier | `--src` doit contenir **directement** les `.pdf` (par exemple `<PDF>/CM`) |
| « des documents attendus … sont ABSENTS du dossier source » | PDF manquants | compléter avec **tous** les PDF fournis (17 pour CM) |
| « serveur d'embeddings injoignable » / « modèle non servi » | Ollama arrêté, modèle non téléchargé | `ollama pull bge-m3` ; `curl http://localhost:11434/v1/models` |
| « langues OCR absentes » | `ALERTE_TESSDATA_DIR` faux | chemin absolu ; `tesseract --list-langs --tessdata-dir <chemin>` |
| `publish` : « vectorisation incomplète » | embeddings non terminés | relancer l'étape 5 (même commande) |
| `ModuleNotFoundError` | venv non activé | `source backend/.venv/bin/activate` |
| L'interface ne voit pas votre espace | autre dossier de données | lancez le backend **depuis `backend/`** (dossier `data/` relatif) ou fixez `ALERTE_DATA_DIR` en absolu pour la CLI **et** le backend |

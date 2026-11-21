> **Annexe — Recherche : portabilité Linux/Windows/macOS, PDF, OCR, CI GitHub Actions, Podman.**
> Matériau de recherche brut produit le 2026-11-21 par un sous-agent (modèle Haiku 5.5), relu en partie par l'architecte. Les marqueurs « non vérifié » / `[NV]` / `[V]` / `[P]` / `[S]` / `[LU]` / `[SUPPOSÉ]` sont ceux du sous-agent. Pièce justificative, pas une spécification.

---

# 14. Portabilité, PDF, OCR, CI (Linux / Windows / macOS, sans Docker obligatoire)

Date de recherche : 2026-11-21. Légende : **[V]** vérifié sur la page officielle lue ; **[P]** partiellement vérifié (page lue, point précis non confirmé) ; **[NV]** non vérifié (fondé sur la connaissance générale, à confirmer avant adoption).

## 1. Génération de PDF côté serveur

| Option | Licence | Points vérifiés | Arabe / RTL | Statut |
|---|---|---|---|---|
| WeasyPrint | BSD-3-Clause [V] (page GitHub) | Python 3.11+ [V] ; Pango 1.44+ requis [V] ; Linux via paquets distro, macOS via `brew install weasyprint` [V] ; Windows : exécutable GitHub ou MSYS2 + `pacman -S mingw-w64-ucrt-x86_64-pango` puis pip [V] ; antivirus signalent parfois l'exécutable [V] | Shaping/bidi via Pango/HarfBuzz [NV] ; la doc lue ne le confirme pas [P] | Recommandé (primaire) |
| xhtml2pdf | Apache-2.0 [V] | Basé sur ReportLab [V] ; CSS étendu (flexbox, @font-face, @page, variables CSS) [V] ; RTL arabe/hébreu/persan/ourdou via bidi pur Python [V] | Oui [V] | Repli recommandé (pas de lib système Pango) |
| ReportLab | Édition open source : BSD [NV] (page reportlab.com non lue, erreur) | API programmatique, pas de HTML/CSS | Non confirmé [NV] | Non retenu pour rapports HTML |
| fpdf2 | LGPL-3.0 [V] (dépôt py-pdf/fpdf2) ; Python 3.10+ [V] | Polices TTF/Unicode embarquées [V] ; pas de layout HTML | RTL non confirmé [P] | Acceptable si on code le layout à la main |
| Playwright / Chromium headless | Apache-2.0 [V] | `npx playwright install` télécharge les navigateurs ; Chrome for Testing par défaut [V] ; poids du téléchargement [NV] (plusieurs centaines de Mo) ; `--with-deps` non lu [P] | Rendu Chromium, donc bonne prise en charge [NV] | Option lourde, bonne fidélité CSS, à réserver |
| wkhtmltopdf | LGPL-3.0 [V] | **Archivé le 2 janvier 2023, lecture seule** [V] ; moteur QtWebKit [V] | — | **Ne pas utiliser** |
| Typst | Apache-2.0 [V] | Compilateur CLI indépendant, `typst compile x.typ` produit un PDF [V] ; pas de HTML en entrée | Arabe/RTL non annoncé sur la page lue [P] | Option si on accepte un langage de template dédié |
| pandoc | GPL-2.0-or-later [V] | PDF via LaTeX, Groff ms ou HTML [V] (pas de Typst/WeasyPrint cités) | — | Outil de conversion, pas moteur de rendu de l'app |
| Paged.js | MIT [NV] | Pagination CSS côté navigateur | — | Non lu ; nécessite un navigateur |

**Recommandation tranchée**
- **Primaire : WeasyPrint** (BSD-3, HTML/CSS, pagination, tableaux, polices). Sur Linux et macOS, installation directe. Sur Windows, documenter le chemin MSYS2 (Pango) et le mettre dans le README d'installation.
- **Repli : xhtml2pdf** (Apache-2.0, pas de bibliothèque système) si Pango ne s'installe pas sur une machine ou dans la CI Windows. Le faire via un extra optionnel (`pip install .[pdf-fallback]`) et un test de rendu identique par gabarit.
- **Éviter** : wkhtmltopdf (archivé), toute solution AGPL pour un service réseau.
- Arabe : bundler une police arabe libre (ex. Noto Naskh/Kufi Arabic, licence SIL OFL [NV]) et la déclarer via `@font-face` ; ne pas dépendre des polices système, qui diffèrent entre OS.

## 2. OCR

| Option | Licence | Points | Statut |
|---|---|---|---|
| Tesseract (moteur) | Apache-2.0 [NV] | Linux : `apt install tesseract-ocr` + `tesseract-ocr-ara`, `tesseract-ocr-eng` [V] ; `fra` non cité comme paquet dans la doc (présent dans l'AppImage) [P] ; Windows : installeur UB Mannheim, ajouter au PATH [V] ; macOS : `brew install tesseract` [V] | **Recommandé** |
| pytesseract | Apache-2.0 [NV] | Wrapper CLI, nécessite le binaire système | **Recommandé** (simple, portable) |
| tesserocr | MIT [NV] | Liaison C++ à compiler, plus fragile sur Windows | Non retenu |
| OCRmyPDF | MPL-2.0 [V] | Dépend de Tesseract et Ghostscript [V] ; Linux, Windows (ou WSL), macOS [V] | Option si on veut produire des PDF OCRisés ; ajoute Ghostscript |
| RapidOCR | Apache-2.0 [V] | `pip install rapidocr onnxruntime` (installation CPU, déduit) [V] ; modèles PaddleOCR convertis en ONNX, licence Apache-2.0 du code et des modèles, poids soumis à `MODEL_LICENSES.md` [V] ; arabe à vérifier dans la Model List [P] | **Repli sans installation système** |
| EasyOCR | Apache-2.0 [NV] | PyTorch, poids lourds | Non lu |
| PaddleOCR | Apache-2.0 [NV] | Dépendance PaddlePaddle, lourde | Non retenu |
| docling | MIT [V] (code) ; licences des modèles séparées [V] | Conversion de documents, OCR étendu [V] ; GraniteDocling 258M paramètres [P] ; liste de langues non trouvée [V] | Option lourde, à évaluer séparément |

**Recommandation tranchée** : Tesseract (système) + pytesseract ; `TESSDATA_PREFIX` seulement si le paquet n'installe pas les données dans le chemin par défaut (variable documentée par Tesseract, non lue dans la page d'installation [P]). Repli RapidOCR pour les environnements sans droits d'installation.

## 3. Extraction de texte PDF (sans AGPL)

| Bibliothèque | Licence | Statut |
|---|---|---|
| PyMuPDF | **AGPL-3.0** [V] ; licence commerciale Artifex [V] ; PyMuPDF Office limité à 3 pages sans clé [V] | **Exclure** pour un service réseau (obligations AGPL) sauf achat de licence |
| pypdfium2 | Apache-2.0 **ou** BSD-3-Clause [V] ; rendu et extraction de texte (par zone et recherche) [V] ; Python minimum non indiqué [P] | **Recommandé** pour rendu et texte |
| pdfplumber | MIT [V] ; basé sur pdfminer.six [V] ; testé sur Python 3.10-3.14 [V] | **Recommandé** pour tableaux/coordonnées |
| pdfminer.six | MIT [V] ; Python 3.10+ [V] | Dépendance de pdfplumber |
| pypdf | BSD-3-Clause [NV] | Lecture/fusion simple, extraction limitée |
| docling-parse | MIT [V] ; PDF « programmatic » (non scannés), extraction texte, tracés, images [V] | Option pour PDF structurés |
| unstructured | Apache-2.0 [NV] | Dépendances lourdes, non lu |

**Recommandation tranchée** : pypdfium2 (rendu, texte brut) + pdfplumber (tableaux). Pour les PDF scannés, OCR (section 2) en repli. Ne pas ajouter PyMuPDF.

## 4. Verrouillage et installation

| Élément | Statut |
|---|---|
| uv (installation, lock) | `uv.lock` + `uv sync --locked` recommandé [NV, page docs.astral.sh non lue] ; licence uv (MIT et/ou Apache-2.0) [NV] ; `astral-sh/setup-uv` épinglé SHA `1db35dd8eee11c5894872e0b383ae6c406cf738d` (commentaire `# v10.4.0`) [V] ; `enable-cache` défaut `auto` [V] ; `python-version` remplace `.python-version`/`pyproject.toml` [V] |
| Node / Vite | Vite v8.3.7 : Node **20.19+** (branche 20) ou **22.12+** (branche 22) [V] ; certains templates peuvent exiger plus [V] → fixer `.nvmrc` à Node 22 LTS et `engines` dans package.json ; verrouiller avec `package-lock.json` et `npm ci` [NV] |
| Node manager | nvm (Linux/macOS), nvm-windows, fnm (multiplateforme), Volta [NV] |
| Scripts d'installation | Éviter `make` sous Windows ; fournir `scripts/setup.py` (stdlib) ou `just`/`invoke` [NV] ; un `setup.ps1` et `setup.sh` fins qui appellent le même script Python |

## 5. GitHub Actions

| Élément | Statut |
|---|---|
| `ubuntu-latest` | Ubuntu 24.04, x64 [V] |
| `windows-latest` | Windows Server 2025, x64 [V] |
| `macos-latest` | **macOS 26, arm64** [V] ; pour x64 : `macos-15-intel` ou `macos-26-intel` [V] |
| Versions figées | Recommander `ubuntu-24.04`, `windows-2025`, `macos-15` pour éviter les migrations de `-latest` (migration progressive sur 1 à 2 mois) [V] |
| Logiciels préinstallés | Liste dans `actions/runner-images` (Readme par image). Python : 5 versions populaires, Node : 3 LTS, Docker, PostgreSQL et Tesseract non confirmés sur la page [P] → installer explicitement |
| `actions/setup-python` | v7 [V] ; `python-version` à fixer ; cache pip/pipenv/poetry (pas uv) [V] |
| `actions/setup-node` | Cache npm [NV] |
| Service containers | **Linux uniquement** [V] ; PostgreSQL sur Windows/macOS → installation native ou skip |
| Tesseract en CI | Ubuntu : `apt-get install tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra` [NV] ; macOS : `brew install tesseract` [V] ; Windows : installeur UB Mannheim ou Chocolatey [NV] |
| GPU | Larger runners GPU sur plans Team / Enterprise Cloud [V] ; sinon self-hosted |
| Tests GPU | `pytest -m gpu` avec `pytest.ini` ; job séparé sur runner self-hosted ou larger runner [NV] |
| Frontend | Vitest (unitaire) ; Playwright sur les 3 OS (matrice) [NV pour les exemples] |

**Matrice recommandée** (tests Python + Vitest sur les 3 OS ; Playwright E2E sur Ubuntu et Windows ; tests PostgreSQL sur Ubuntu uniquement)

## 6. Squelette de workflow (non exécuté)

```yaml
name: ci
on: [push, pull_request]
permissions:
  contents: read
jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-24.04
          - os: windows-2025
          - os: macos-15
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4          # version à épingler par SHA
      - uses: actions/setup-python@v7
        with:
          python-version: '3.12'
          cache: 'pip'
      - uses: astral-sh/setup-uv@1db35dd8eee11c5894872e0b383ae6c406cf738d  # v10.4.0
        with:
          enable-cache: true
      - uses: actions/setup-node@v4        # [NV] version à vérifier
        with:
          node-version: '22'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - name: Install Tesseract (Linux)
        if: runner.os == 'Linux'
        run: sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra
      - name: Install Tesseract (macOS)
        if: runner.os == 'macOS'
        run: brew install tesseract
      - name: Install Tesseract (Windows)   # [NV] installeur à figer, chemin à ajouter au PATH
        if: runner.os == 'Windows'
        shell: pwsh
        run: choco install tesseract -y
      - run: uv sync --locked
      - run: uv run pytest -m "not gpu and not postgres"
      - name: Frontend
        working-directory: frontend
        run: |
          npm ci
          npm test
```

Job PostgreSQL (Linux uniquement, service container) : à ajouter séparément avec `services:` [NV, exemple non lu].

## 7. Podman (même Dockerfile / compose)

| Point | Statut |
|---|---|
| Windows : Windows 11, WSL v2.5.1+ ou Hyper-V (Pro/Enterprise/Education), `wsl --install` requis séparément [V] | |
| `podman machine init` / `start` ; rootless par défaut ; port < 1024 demande rootful [V] | |
| Volumes Windows : chemins `c:\...`, `/c/...` ou chemin WSL ; guillemets nécessaires depuis shell Linux [V] | |
| WSL et Hyper-V ne tournent pas simultanément [V] | |
| `:Z` / `:z` (étiquetage SELinux) pour bind mounts ; `podman compose` ; docs Linux non lues [NV] | |
| macOS : `podman machine` via VM [NV] | |

Recommandation : Docker/Podman **optionnel** ; le chemin natif (uv + npm + Tesseract) doit suffire. Documenter les différences de montage.

## 8. Pièges multiplateformes concrets

1. **Noms de fichiers** : `:`, `*`, `?`, `"`, `<`, `>`, `|` interdits sous Windows ; noms réservés (CON, NUL, COM1) ; casse ignorée sous Windows/macOS par défaut. Vérifier les noms de fichiers générés (ex. horodatage `12:30`).
2. **Chemins longs** : limite 260 caractères sans `LongPathsEnabled` ; éviter les arborescences profondes (uploads, `node_modules`).
3. **Fins de ligne** : `.gitattributes` avec `* text=auto eol=lf` pour `*.sh`, `*.py`, `*.ts` ; scripts `.sh` en CRLF cassent sous Linux.
4. **Encodage** : toujours `open(..., encoding="utf-8")` ; sous Windows, l'encodage par défaut de `open()` est celui de la locale (ex. cp1252) [NV]. PEP 686 (UTF-8 par défaut) [NV, page non lue] : ne pas s'y fier avant Python 3.15.
5. **Verrous de fichiers** : sous Windows, supprimer ou renommer un fichier ouvert (SQLite, PDF ouvert dans un viewer) échoue ; fermer les handles avant `unlink`.
6. **Signaux** : `SIGTERM` n'est pas envoyé de façon fiable sous Windows ; utiliser un arrêt propre via API ou `CTRL_BREAK_EVENT` [NV].
7. **multiprocessing** : macOS et Windows utilisent `spawn` (macOS depuis 3.8) ; tout code de lancement doit être sous `if __name__ == "__main__":`, et les objets doivent être picklables.
8. **SQLite** : fichier verrouillé, chemins avec `\`, `check_same_thread` avec FastAPI [NV].
9. **Tesseract** : binaire absent du PATH sous Windows (installeur UB Mannheim) ; `TESSDATA_PREFIX` ; détecter au démarrage et renvoyer une erreur claire.
10. **Polices** : une police système arabe absente sur une machine change le rendu PDF ; bundler la police.
11. **Architecture** : `macos-latest` est arm64 ; wheels x64 uniquement (onnxruntime, PyMuPDF, etc.) à vérifier.
12. **Service containers** : PostgreSQL seulement sur Linux en CI ; les tests PostgreSQL ne doivent pas tourner en Windows/macOS sans installation native.
13. **Chemins Podman Windows** : guillemets et notation `/c/...`.
14. **Node** : Vite exige Node 20.19+ / 22.12+ ; version différente sur les postes = erreurs de build.
15. **Lockfiles** : `npm ci` (pas `npm install`) ; `uv sync --locked` pour que la CI échoue si `uv.lock` est désynchronisé.

## 9. URLs lues et URLs non lues

Lues [V] :
- https://doc.courtbouillon.org/weasyprint/stable/first_steps.html
- https://tesseract-ocr.github.io/tessdoc/Installation.html
- https://pymupdf.readthedocs.io/en/latest/about.html
- https://github.com/pymupdf/PyMuPDF
- https://vite.dev/guide/
- https://docs.github.com/en/actions/using-github-hosted-runners/using-github-hosted-runners/about-github-hosted-runners
- https://github.com/Kozea/WeasyPrint
- https://github.com/wkhtmltopdf/wkhtmltopdf
- https://github.com/py-pdf/fpdf2
- https://github.com/pypdfium2-team/pypdfium2
- https://github.com/docling-project/docling
- https://github.com/docling-project/docling-parse
- https://github.com/jsvine/pdfplumber
- https://github.com/pdfminer/pdfminer.six
- https://docs.github.com/en/actions/using-containerized-services/about-service-containers
- https://github.com/actions/runner-images
- https://github.com/astral-sh/setup-uv
- https://github.com/containers/podman/blob/main/docs/tutorials/podman-for-windows.md
- https://github.com/actions/setup-python
- https://github.com/microsoft/playwright
- https://github.com/typst/typst
- https://github.com/ocrmypdf/OCRmyPDF
- https://github.com/RapidAI/RapidOCR
- https://github.com/xhtml2pdf/xhtml2pdf
- https://github.com/jgm/pandoc
- https://www.reportlab.com (non lu, erreur)

Non lues / en échec [NV] :
- https://docs.astral.sh/uv/ et https://docs.astral.sh/uv/guides/integration/github/ (échec)
- https://podman.io/docs/installation, docs.podman.io podman-compose et podman-run (échec)
- https://peps.python.org/pep-0686/ (échec)
- https://www.reportlab.com/opensource/ (échec) ; https://github.com/MigoXLab/reportlab et gjmcdonnell/reportlab (404, non officiels)
- https://pypi.org/project/fpdf2/, /reportlab/, /pypdfium2/ (échec)
- https://github.com/microsoft/playwright : `--with-deps` non confirmé
- Licences non lues : pypdf, Tesseract Apache-2.0, pytesseract, tesserocr, EasyOCR, PaddleOCR, unstructured, Paged.js, uv, Node managers, SIL OFL

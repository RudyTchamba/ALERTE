#!/usr/bin/env python3
"""REMPLACÉ par la CLI applicative `python -m app.cli knowledge …` (mêmes services que l'API et l'interface).

L'ancien script dérivait les codes de documents du préfixe des noms de fichiers, construisait toutes les collections par défaut et
lisait les PDF dans l'ancien projet `alerte/` : trois pratiques supprimées. Équivalents :

    python -m app.cli workspace create --name "ALERTE — Corpus"
    python -m app.cli knowledge kb-create --code CM --name Cameroun
    python -m app.cli knowledge sources-migrate --map CM=<dossier source>/CM --apply --manifest <manifeste.jsonl>
    python -m app.cli knowledge adopt  --country CM --manifest <manifeste.jsonl>
    python -m app.cli knowledge curate --country CM --curation knowledge_bases/curation/documents.curation.json --manifest <manifeste.jsonl>
    python -m app.cli knowledge build  --country CM          # périmètre OBLIGATOIRE : aucune construction globale

Voir docs/knowledge-base/cli-et-pipeline.md.
"""
import sys

if __name__ == "__main__":
    sys.exit(__doc__ + "\n(script retiré : utilisez la CLI ci-dessus)")

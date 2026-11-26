# Pack Rising Waters (généré)

Généré par `backend/scripts/rising_waters_pack.py` : mandats depuis la NOUVELLE base (`knowledge_bases/curation/`), scénarios depuis `alerte/data/` (prototype, lecture seule).
Toutes les situations sont **fictives**. Voir `docs/runbooks/guide-test-complet-interface.md`.

| Fichier | Usage |
|---|---|
| `actions.csv` | **Catalogue d'actions : à importer EN PREMIER** (Pays et institutions → Registre des mandats → Catalogue d'actions → Importer un CSV) |
| `*.alerte-scenario.yaml` | Scénarios (écran Scénarios → Importer un YAML) |
| `mandats-*.csv` | Registre de mandats de la nouvelle base, sources `CM-xx` (Pays et institutions → Mandats → Importer un CSV) |
| `setup-*.json` | Pays, institutions, actions et agents (script `seed_rising_waters.py`) |
| `lacunes-attendues.PRIVE.json` | Lacunes visées par l'auteur ; **ne jamais importer dans le scénario** |

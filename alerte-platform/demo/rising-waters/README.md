# Pack Rising Waters (généré)

Généré par `backend/scripts/rising_waters_pack.py` à partir de `alerte/data/` (prototype, lecture seule).
Toutes les situations sont **fictives**. Voir `docs/runbooks/guide-test-complet-interface.md`.

| Fichier | Usage |
|---|---|
| `*.alerte-scenario.yaml` | Scénarios (écran Scénarios → Importer un YAML) |
| `mandats-*.csv` | Registre de mandats (Pays et institutions → Mandats → Importer un CSV) |
| `setup-*.json` | Pays, institutions, actions et agents (script `seed_rising_waters.py`) |
| `lacunes-attendues.PRIVE.json` | Lacunes visées par l'auteur ; **ne jamais importer dans le scénario** |

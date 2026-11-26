# Recherche hybride

Implémentation : `backend/app/knowledge/search.py` + `indexes.py`.

1. **Portée d'abord** : la portée (bases autorisées, versions publiées, documents) est dérivée du jeton / de l'agent côté backend ; chaque candidat est revérifié (`SCOPE_VIOLATION` signalée) avant d'être renvoyé. Un agent ne peut pas atteindre les chunks d'une autre base.
2. **Lexical** : FTS5 (BM25). **Sémantique** : vecteurs BGE-M3 (ChromaDB, avec index NumPy exact en garde-fou). **Article** : liste dédiée si la requête contient un numéro d'article.
3. **Fusion RRF** (k=60) des listes ; liste élargie par un thésaurus de crise avec poids 0,5 ; **pondération par autorité** après fusion (official 1,0 · summary 0,8 · unofficial 0,7 · not_found 0,6) — l'ordre change, rien n'est exclu.
4. **Filtres** : langue, type de document, article. Pays/juridiction : via la base ou le document.
5. **Statut visible** : la réponse porte `degraded` et `label` (« BM25 (FTS5) + vectoriel + RRF » ou « recherche dégradée : lexical seul »). Une base dont les chunks ne sont pas tous vectorisés n'est **pas** présentée comme entièrement vectorisée (`embedded_chunks / chunks` dans l'aperçu de la base).

## Limites
* Sans embeddings, une requête dans une langue différente du texte ne trouve pas le passage (constaté sur la base héritée du prototype : requête anglaise sur texte français).
* Pas de reranker : non démontré utile, coût non justifié ici.

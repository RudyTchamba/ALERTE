> **Annexe — Recherche : architecture logicielle, FastAPI, SQLAlchemy, React, tâches longues.**
> Matériau de recherche brut produit le 2026-11-20 par un sous-agent (modèle Haiku 5.5), relu en diagonale par l'architecte. Les marqueurs « non vérifié » / `[NV]` / `[V]` / `[S]` sont ceux du sous-agent ; toute information utilisée dans le dossier principal est citée avec son niveau de vérification. Ce fichier est une pièce justificative, pas une spécification.

---

# 04 - Recherche documentaire : bonnes pratiques d'architecture (ALERTE)

Date de la recherche : 2026-11-20. Périmètre : plateforme de simulation multi-agents d'exercices de crise (FastAPI + SQLAlchemy 2.0 + SQLite/PostgreSQL, React/TypeScript/Vite, monolithe modulaire, tâches longues, SSE, journal d'audit chaîné SHA-256, exports de bases de connaissances). Délai projet : 5 jours.

Légende : "Lu" = page lue directement ; "Snippet" = information issue d'un résultat de recherche, non vérifiée sur la page ; "Non vérifié" = affirmation de bon sens, sans source lue.

---

## 1. Modèle C4 (Context / Container / Component / Code)

(a) **Pratique** : documenter l'architecture en 3 niveaux utiles pour ALERTE : Context (système + acteurs : animateur d'exercice, joueurs, LLM externe), Container (SPA React, API FastAPI, base SQLite/PostgreSQL, worker de simulation), Component (modules internes : scénario, agents, audit, export KB). Suivre la hiérarchie software system → containers → components → code, en gardant un jeu d'abstractions réduit.
(b) **Source** : https://c4model.com/ (Lu, page d'accueil) ; https://c4model.com/abstractions (Lu). Version/date : non visibles sur la page.
(c) **Problème résolu** : diagrammes d'architecture sans vocabulaire commun, qui vieillissent ou deviennent illisibles.
(d) **Intérêt pour ALERTE** : le jury et l'équipe ont besoin d'une vue claire du passage LLM -> simulation -> audit -> export. Le niveau Context suffit pour la soutenance ; le niveau Component sert à montrer la frontière des modules.
(e) **Composant** : `docs/architecture/` (diagrammes, un par niveau, 3 niveaux maximum).
(f) **Limites** : les pages lues ne détaillent pas les règles de notation ni les pièges à éviter ; la page d'accueil se limite à présenter le modèle et son indépendance vis-à-vis des outils. Le niveau Code n'est pas utile sur 5 jours.
(g) **Vérification** : revue de présentation : chaque boîte Container a une technologie nommée et chaque flèche un verbe ou un protocole (HTTP, SSE, SQL).

## 2. Structure FastAPI : APIRouter par module et include_router

(a) **Pratique** : un `APIRouter` par module métier (ex. `routers/scenarios.py`, `routers/runs.py`, `routers/audit.py`), déclaré avec `prefix`, `tags` et `dependencies` au niveau du router ; `main.py` ne fait que créer l'application et appeler `app.include_router(...)`. Importer les sous-modules (`from .routers import runs`) plutôt que leur variable `router`.
(b) **Source** : https://fastapi.tiangolo.com/tutorial/bigger-applications/ (Lu). Version non visible sur la page.
(c) **Problème résolu** : un `main.py` qui grossit sans limite et des dépendances partagées dupliquées.
(d) **Intérêt pour ALERTE** : chaque module (agents, audit, KB) reste lisible et testable seul ; la séparation prépare un découpage futur sans gros coût.
(e) **Composant** : `backend/app/main.py` et `backend/app/<module>/router.py`.
(f) **Limites** : le document ne traite pas de la séparation domaine / infrastructure ; la structure reste plate, ce qui convient à un monolithe de 5 jours.
(g) **Vérification** : un test qui importe `app.main` et vérifie les routes attendues via `app.routes` ; revue : aucun `@app.get` hors de `main.py`.

## 3. Server-Sent Events : EventSourceResponse, ServerSentEvent, Last-Event-ID

(a) **Pratique** : utiliser `response_class=EventSourceResponse` (module `fastapi.sse`) avec une fonction `async def` qui `yield` des `ServerSentEvent(data=..., event=..., id=..., retry=...)`. Chaque événement porte un `id` monotone (ex. numéro de séquence du journal d'audit). Lire l'en-tête `Last-Event-ID` (via `Annotated[int | None, Header()]`) pour rejouer les événements manqués depuis la base.
(b) **Source** : https://fastapi.tiangolo.com/tutorial/server-sent-events/ (Lu). Page indiquant : « Added in FastAPI 0.135.0 ». Le PyPI lu indique la dernière version 0.165.0, publiée le 18 novembre 2026 (https://pypi.org/project/fastapi/, Lu).
(c) **Problème résolu** : affichage en direct de l'avancement d'une simulation sans polling, et reprise après coupure réseau.
(d) **Intérêt pour ALERTE** : le flux SSE des agents et du journal peut être reconstruit depuis la table d'audit grâce au `id`, ce qui rend la reprise fiable.
(e) **Composant** : `backend/app/<module>/stream.py` (route SSE) ; source des événements = table d'audit ou de run.
(f) **Limites** : la page annonce des comportements automatiques : `ping` toutes les 15 secondes, `Cache-Control: no-cache`, `X-Accel-Buffering: no`. `data` et `raw_data` sont mutuellement exclusifs. La page ne documente pas de limite de nombre de connexions ; ce point vient de la page MDN EventSource (voir pratique 18). Un seul processus uvicorn : le flux dépend de la mémoire du processus pour les événements en cours, d'où l'intérêt de relire depuis la base.
(g) **Vérification** : test d'intégration avec `httpx` qui ouvre le flux, reçoit N événements, puis rejoue depuis `Last-Event-ID` et vérifie l'absence de doublon.

## 4. Lifespan FastAPI (et non on_event)

(a) **Pratique** : initialiser l'engine SQLAlchemy, les répertoires d'export et le worker de tâches dans un `@asynccontextmanager` passé à `FastAPI(lifespan=...)`. Ne pas utiliser `@app.on_event`.
(b) **Source** : https://fastapi.tiangolo.com/advanced/events/ (Lu). Le page indique que `on_event` est déprécié et que `startup` / `shutdown` ne sont pas appelés si `lifespan` est fourni.
(c) **Problème résolu** : ressources partagées créées et fermées au bon moment, sans fuite de connexions.
(d) **Intérêt pour ALERTE** : le worker de simulation (pratique 21) démarre et s'arrête proprement, et récupère les runs interrompus au démarrage.
(e) **Composant** : `backend/app/main.py`.
(f) **Limites** : le lifespan ne s'applique qu'à l'application principale, pas aux sous-applications montées.
(g) **Vérification** : test avec `TestClient(app)` en contexte `with`, vérifier que l'engine est disposé à la sortie ; revue : aucun `on_event` dans le dépôt.

## 5. BackgroundTasks : réservé aux petites tâches

(a) **Pratique** : ne pas utiliser `BackgroundTasks` pour une simulation complète ; l'utiliser seulement pour des effets de bord courts (ex. notification, écriture d'un fichier de log).
(b) **Source** : https://fastapi.tiangolo.com/tutorial/background-tasks/ (Lu, citations ci-dessous).
(c) **Problème résolu** : répondre vite à une requête HTTP tout en exécutant un petit travail après la réponse.
(d) **Intérêt pour ALERTE** : éviter de noyer une simulation de plusieurs minutes dans un mécanisme sans état ni reprise.
(e) **Composant** : routes d'API ponctuelles seulement.
(f) **Limites** : la page dit : « If you need to perform heavy background computation and you don't necessarily need it to be run by the same process ... you might benefit from using other bigger tools like Celery. » et que `BackgroundTasks` est pour « small background tasks ». Pas de mécanisme de reprise documenté (déduction : une tâche interrompue n'est pas relancée).
(g) **Vérification** : revue de code : toute tâche de plus de quelques secondes passe par la file de jobs en base (pratique 21).

## 6. Facteurs 12-Factor applicables

(a) **Pratique** : appliquer six facteurs : (3) Config dans des variables d'environnement (base URL, clés LLM, chemin SQLite) ; (6) processus sans état : tout état de run dans la base, rien en mémoire seule ; (9) disposability : démarrage rapide et arrêt propre (les runs `running` sont marqués `interrupted` au démarrage) ; (10) dev/prod parity : même moteur de base en dev et en test autant que possible ; (11) logs : écrits sur stdout en flux continu, sans gestion de fichiers ; (12) admin processes : migrations Alembic et scripts d'import KB lancés comme commandes ponctuelles.
(b) **Source** : https://12factor.net/ (Lu, liste des 12 facteurs avec sous-pages /config, /processes, /disposability, /logs, /admin-processes, etc.). Les sous-pages détaillées n'ont pas été lues.
(c) **Problème résolu** : déploiement reproductible dans un conteneur unique et diagnostic par les logs.
(d) **Intérêt pour ALERTE** : un seul conteneur, mais une configuration qui sépare secrets LLM et données, et des exports de KB qui doivent être lancés hors de la requête HTTP.
(e) **Composant** : `backend/app/config.py` (pydantic-settings ou équivalent), `Dockerfile`, `scripts/` (migrations et imports).
(f) **Limites** : le facteur 7 (port binding) et le facteur 8 (concurrency) sont peu utiles pour un seul conteneur ; le facteur 6 (processus sans état) entre en conflit avec un worker en mémoire : la pratique 21 doit tenir compte de ce point.
(g) **Vérification** : `grep` dans le dépôt pour les chemins et clés codés en dur ; test de démarrage avec variables d'environnement vides qui échoue proprement.

## 7. Décisions : gabarit MADR minimal

(a) **Pratique** : tenir un registre `docs/adr/` au format MADR minimal, avec quatre sections : Title, Context and Problem Statement, Considered Options, Decision Outcome (+ sous-section optionnelle Consequences). Numéroter `0001-...md`.
(b) **Source** : https://github.com/adr/madr (Lu, page du dépôt : licence « MIT OR CC0-1.0 », branche develop, convention release/vY) ; gabarit lu sur https://raw.githubusercontent.com/adr/madr/develop/template/adr-template-minimal.md (Lu). Le site https://adr.github.io/ n'a pas pu être lu (voir liste des URLs non lisibles). La page du dépôt ne donne pas de numéro de version MADR précis : non vérifié.
(c) **Problème résolu** : traçabilité des choix (pourquoi SQLite, pourquoi pas de Celery) sans rédiger de longs documents.
(d) **Intérêt pour ALERTE** : les décisions déjà prises (monolithe, SSE, hash chain) deviennent des fichiers courts, citables pendant la soutenance.
(e) **Composant** : `docs/adr/`.
(f) **Limites** : le gabarit minimal ne comporte aucune métadonnée (pas de statut ni de date dans le front matter) ; il faut les écrire dans le corps si on les veut. Les champs `decision-makers`, `consulted`, etc. figurent dans des gabarits plus complets, non lus ici.
(g) **Vérification** : un script ou une revue qui vérifie que chaque fichier `docs/adr/*.md` contient les quatre titres de section.

## 8. Monolithe d'abord, modules à frontières claires (bounded contexts)

(a) **Pratique** : un seul déploiement, mais des modules Python séparés par contexte (ex. `scenario`, `agents`, `audit`, `kb_export`), qui ne s'importent entre eux que par une interface publique (fonctions de service), jamais par les modèles ORM d'un autre module.
(b) **Source** : https://martinfowler.com/bliki/MonolithFirst.html (Lu, 3 juin 2015) ; https://martinfowler.com/bliki/BoundedContext.html (Lu, 15 janvier 2014).
(c) **Problème résolu** : éviter les microservices prématurés tout en gardant une modularité qui permettrait de les extraire plus tard.
(d) **Intérêt pour ALERTE** : le journal d'audit et l'export KB doivent rester indépendants de la logique des agents.
(e) **Composant** : arborescence `backend/app/` ; règle vérifiable par import-linter (ou revue).
(f) **Limites** : Fowler précise qu'un monolithe ne facilite la migration que s'il est modulaire, aussi bien dans ses API que dans son stockage. Il reconnaît aussi que tous les systèmes ne se découpent pas proprement.
(g) **Vérification** : règle d'import (import-linter ou test `grep`) : `audit` n'importe pas `agents`, etc. ; un context map d'une page.

## 9. Architecture hexagonale (ports et adaptateurs) : version allégée

(a) **Pratique** : isoler uniquement les dépendances externes derrière des ports (Protocol Python) : fournisseur LLM, stockage (repository), horloge et export de fichiers. Le domaine (règles de simulation, chaîne d'audit) ne dépend ni de FastAPI ni de SQLAlchemy.
(b) **Source** : https://alistair.cockburn.us/hexagonal-architecture/ (Lu, Cockburn, 2005) : ports, adaptateurs, côtés driving et driven, possibilité de tester le cœur isolément.
(c) **Problème résolu** : tester la logique métier sans LLM réel ni base.
(d) **Intérêt pour ALERTE** : le LLM peut être remplacé par un faux fournisseur déterministe dans les tests et les démos.
(e) **Composant** : `backend/app/<module>/ports.py` (Protocol) et `adapters/`.
(f) **Limites** : appliquer l'hexagonale complète à chaque module ajoute des couches de mapping inutiles sur 5 jours. Ne l'appliquer qu'aux deux ou trois frontières utiles.
(g) **Vérification** : test unitaire du domaine sans FastAPI ni base ; grep des imports `sqlalchemy` et `fastapi` dans le domaine (doit être vide).

## 10. SQLAlchemy 2.0 : Session par requête, transactions explicites

(a) **Pratique** : créer la Session par requête (dépendance FastAPI `get_session` avec `yield`), un `sessionmaker` unique au niveau du module, transactions courtes avec `with Session.begin():` (commit automatique à la sortie, rollback sur exception). Pour les opérations qui échouent élément par élément (ex. import KB), envelopper chaque élément dans `session.begin_nested()` (SAVEPOINT).
(b) **Source** : https://docs.sqlalchemy.org/en/20/orm/session_basics.html (Lu, SQLAlchemy 2.0.58 indiqué sur la page) ; https://docs.sqlalchemy.org/en/20/orm/session_transaction.html (Lu).
(c) **Problème résolu** : fuites de connexions, transactions ouvertes trop longtemps, états partiels après erreur.
(d) **Intérêt pour ALERTE** : le journal d'audit doit être écrit dans la même transaction que l'événement métier, sinon l'enchaînement SHA-256 peut diverger.
(e) **Composant** : `backend/app/db/session.py` et `backend/app/<module>/service.py`.
(f) **Limites** : Session non thread-safe ; `commit()` en 2.0 valide toujours la transaction la plus externe. La page ne tranche pas entre « commit as you go » et « begin once » : c'est une décision de style, à documenter en ADR.
(g) **Vérification** : test qui force une exception au milieu d'un import et vérifie qu'aucune ligne partielle n'est restée ; revue : aucun `Session()` créé hors dépendance.

## 11. SQLAlchemy 2.0 async : AsyncSession, expire_on_commit=False, pas de lazy loading

(a) **Pratique** : si l'API est async, `create_async_engine("sqlite+aiosqlite:///...")`, une `AsyncSession` par tâche, `expire_on_commit=False`, et chargement explicite des relations avec `selectinload()` ; ne jamais laisser un accès de relation déclencher du SQL implicite. Sinon, appeler `await engine.dispose()` à la fermeture.
(b) **Source** : https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html (Lu, première partie ; la suite de la page n'a pas été lue).
(c) **Problème résolu** : erreurs `MissingGreenlet` et requêtes implicites dans des boucles async.
(d) **Intérêt pour ALERTE** : le worker de simulation et les flux SSE tournent dans la même boucle asyncio ; un lazy load bloquant gèlerait tous les flux.
(e) **Composant** : `backend/app/db/session.py`.
(f) **Limites** : la page présente `run_sync()` comme une approche « controversial ». La page ne nomme pas l'erreur `MissingGreenlet`. Décision à prendre : sync ou async, pas les deux. Pour 5 jours, la version synchrone (`Session` + threads) est plus sûre si l'équipe ne maîtrise pas l'async.
(g) **Vérification** : `lazy="raise"` sur les relations ; test d'intégration qui accède à chaque relation attendue.

## 12. Alembic : render_as_batch=True pour SQLite

(a) **Pratique** : dans `env.py`, `context.configure(..., render_as_batch=True)`. Utiliser `op.batch_alter_table()` pour toute migration sur SQLite.
(b) **Source** : https://alembic.sqlalchemy.org/en/latest/batch.html (Lu, relecture réussie au second essai).
(c) **Problème résolu** : SQLite a « almost no support for the ALTER statement » ; Alembic reconstruit la table (copie, suppression, renommage).
(d) **Intérêt pour ALERTE** : les migrations de schéma restent identiques pour SQLite (dev) et PostgreSQL (cible) : le réglage n'a aucun effet sur PostgreSQL.
(e) **Composant** : `backend/alembic/env.py` et `backend/alembic/versions/`.
(f) **Limites** : la migration par copie peut être lente sur de grosses tables ; elle est sans problème pour une base d'exercice. Autogenerate ne détecte pas tous les changements (types, certaines contraintes) : relire chaque migration.
(g) **Vérification** : `alembic upgrade head` sur une base vide, puis `alembic check` ou `autogenerate` qui ne produit pas de diff.

## 13. SQLite : WAL, busy_timeout, un seul écrivain

(a) **Pratique** : activer `journal_mode=WAL` à la connexion, régler un `busy_timeout` (valeur à mesurer), n'autoriser qu'un processus uvicorn avec un worker, et garder toutes les écritures courtes.
(b) **Source** : https://www.sqlite.org/wal.html (non lu directement : échec de lecture sur les deux variantes d'URL ; contenu issu du résultat de recherche https://www.sqlite.org/useovernet.html et https://www.sqlite.org/wal.html en snippet). Les pages https://www.sqlite.org/pragma.html et https://www.sqlite.org/c3ref/busy_timeout.html n'ont pas été lues.
(c) **Problème résolu** : lecteurs bloqués par l'écrivain et erreurs `database is locked`.
(d) **Intérêt pour ALERTE** : une simulation écrit des événements en continu pendant que l'interface lit le flux SSE ; WAL évite que la lecture soit bloquée.
(e) **Composant** : `backend/app/db/session.py` (event listener `connect` sur l'engine).
(f) **Limites** : WAL ne fonctionne pas sur un système de fichiers réseau (snippet de la documentation officielle SQLite : WAL ne marche pas sur un réseau car les processus doivent partager de la mémoire). Un seul écrivain à la fois ; `busy_timeout` non vérifié sur la page officielle. Passer à PostgreSQL si : plusieurs conteneurs ou machines écrivent, ou plusieurs workers uvicorn doivent écrire en même temps. Le caveat « SQLite over a network » recommande un serveur client/serveur comme PostgreSQL.
(g) **Vérification** : test de charge local (deux coroutines qui écrivent et une qui lit le flux) ; aucune erreur `database is locked` sur 1 000 écritures.

## 14. React : Thinking in React (état minimal, état au plus proche parent)

(a) **Pratique** : décomposer l'UI en composants à responsabilité unique, faire une version statique sans état, garder un état minimal (ce qui change et ne se calcule pas), placer l'état au plus proche parent commun, flux de données unidirectionnel (callbacks en props).
(b) **Source** : https://react.dev/learn/thinking-in-react (Lu).
(c) **Problème résolu** : états dupliqués et désynchronisés entre composants.
(d) **Intérêt pour ALERTE** : la liste des agents, le filtre et le journal partagent des données ; l'état minimal évite de stocker en double ce que le serveur fournit déjà.
(e) **Composant** : `frontend/src/features/*`.
(f) **Limites** : la page est un guide d'apprentissage sans règles de rangement de fichiers ni gestion des données serveur.
(g) **Vérification** : revue : aucun `useState` ne contient une valeur dérivable d'une autre (liste filtrée = calcul, pas état).

## 15. Version React et sécurité (Server Components)

(a) **Pratique** : épingler React 19 et vérifier qu'une version corrigée est utilisée ; ALERTE est une SPA Vite, sans Server Components : la vulnérabilité ne s'applique pas à l'usage prévu, mais la version doit rester à jour.
(b) **Source** : https://react.dev/blog (Lu). Dernière version mentionnée : React 19.3 (billet daté du 9 septembre 2026). Vulnérabilité RSC (3 et 11 décembre 2025), corrections dans 19.0.1, 19.1.2, 19.2.1. Le statut « stable » de 19.3 n'est pas confirmé sur la page : non vérifié.
(c) **Problème résolu** : dépendances React non corrigées.
(d) **Intérêt pour ALERTE** : la démo sera présentée ; une dépendance vulnérable est un point de revue facile à éviter.
(e) **Composant** : `frontend/package.json`.
(f) **Limites** : je n'ai pas vérifié la version publiée sur npm.
(g) **Vérification** : `npm outdated`, `npm audit` avant la démo.

## 16. Vite : version et Node.js

(a) **Pratique** : utiliser Node.js 20.19+ ou 22.12+ (fichier `.nvmrc` ou `engines`), Vite v8.x.
(b) **Source** : https://vite.dev/guide/ (Lu). Version affichée dans le menu : v8.3.7 ; prérequis Node : « Vite requires Node.js version 20.19+, 22.12+ ».
(c) **Problème résolu** : erreurs d'installation sur des versions Node trop anciennes.
(d) **Intérêt pour ALERTE** : environnement reproductible pour l'équipe.
(e) **Composant** : `frontend/package.json` (`engines`), `frontend/.nvmrc`.
(f) **Limites** : la règle des variables `VITE_` exposées au client n'a pas été lue (page `/guide/env-and-mode` non consultée). Non vérifié : toute variable `VITE_*` est publique dans le bundle ; ne jamais y mettre de clé d'API.
(g) **Vérification** : `grep -r "VITE_" frontend/` et revue de chaque clé.

## 17. Gestion de l'état serveur : TanStack Query

(a) **Pratique** : les données venant de l'API (liste des runs, KB, journal) passent par TanStack Query ; l'état local (filtre, onglet) reste dans React. Un événement SSE peut invalider une requête.
(b) **Source** : https://tanstack.com/query/latest/docs/framework/react/overview (Lu). Pas de numéro de version sur la page ; le paquet cité est `@tanstack/react-query`.
(c) **Problème résolu** : cache, dédoublonnage et rafraîchissement des données serveur à la main.
(d) **Intérêt pour ALERTE** : la vue d'un run se met à jour quand le flux SSE signale un changement.
(e) **Composant** : `frontend/src/api/` et hooks par feature.
(f) **Limites** : ajoute une dépendance et une couche à apprendre ; sur 5 jours, un petit hook `fetch` suffit si l'équipe ne connaît pas la bibliothèque.
(g) **Vérification** : test qui vérifie qu'un événement SSE déclenche un rafraîchissement.

## 18. EventSource côté client : reconnexion et Last-Event-ID

(a) **Pratique** : utiliser `EventSource` natif ; le navigateur reconnecte seul et renvoie `Last-Event-ID`. Le serveur doit donc émettre un `id` par événement et savoir rejouer depuis cet id (pratique 3). Prévoir un état d'erreur visible dans l'interface.
(b) **Source** : https://developer.mozilla.org/en-US/docs/Web/API/EventSource (Lu, MDN). Reconnexion automatique et envoi de `Last-Event-ID` : indiqués par la spécification HTML (non lue ici, relevé comme connaissance générale renforcée par MDN).
(c) **Problème résolu** : reprise du flux après coupure sans écrire de logique de reconnexion.
(d) **Intérêt pour ALERTE** : un animateur qui perd le réseau doit retrouver l'historique du run sans trou.
(e) **Composant** : `frontend/src/features/runs/useRunStream.ts`.
(f) **Limites** : HTTP/1.1 limite à environ 6 connexions SSE par navigateur et domaine (MDN). Seul GET est supporté, sans en-têtes personnalisés (donc pas de jeton `Authorization` : utiliser un cookie ou un paramètre de requête court). Ne pas ouvrir un flux par composant.
(g) **Vérification** : test manuel (couper le réseau dans les outils de développement) et test d'intégration qui vérifie que l'id reprend.

## 19. Accessibilité : WCAG 2.2 niveau AA

(a) **Pratique** : viser WCAG 2.2 niveau AA sur les écrans principaux ; porter une attention particulière aux neuf nouveaux critères, dont 2.4.11 Focus Not Obscured (Minimum), 2.5.8 Target Size (Minimum), 3.3.7 Redundant Entry et 3.3.8 Accessible Authentication (Minimum).
(b) **Source** : https://www.w3.org/TR/WCAG22/ (Lu, Recommendation publiée le 12 décembre 2024 ; 87 critères dans la table des matières, dont 4.1.1 supprimé). Le détail de chaque critère n'a pas été lu.
(c) **Problème résolu** : interface inutilisable au clavier ou pour les lecteurs d'écran.
(d) **Intérêt pour ALERTE** : une plateforme de crise doit pouvoir être utilisée sous stress, au clavier et avec contraste suffisant.
(e) **Composant** : tous les composants `frontend/src/components/`.
(f) **Limites** : AA seulement : AAA n'est pas visé. Une revue au clavier et à la loupe ne remplace pas un audit.
(g) **Vérification** : navigation au clavier de bout en bout ; axe DevTools ou Lighthouse sur les écrans principaux ; contrastes vérifiés.

## 20. Composants accessibles : Radix Primitives

(a) **Pratique** : utiliser des primitives Radix (dialogue, menu, onglets, popover) pour la gestion du focus, de l'ARIA et du clavier, et les styliser soi-même.
(b) **Source** : https://www.radix-ui.com/primitives/docs/overview/introduction (Lu). shadcn/ui non lu : non vérifié.
(c) **Problème résolu** : réimplémenter les patterns WAI-ARIA à la main, avec des bugs de focus.
(d) **Intérêt pour ALERTE** : boîtes de dialogue de confirmation d'export et de suppression de run.
(e) **Composant** : `frontend/src/components/ui/`.
(f) **Limites** : Radix ne fournit aucun style ; c'est une couche de base pour un système de design.
(g) **Vérification** : test au clavier (Tab, Échap, flèches) sur chaque primitive utilisée.

## 21. Tâches longues : file en base + worker unique dans le processus

(a) **Pratique** : ne pas introduire Celery, RabbitMQ ou Redis. Stocker chaque run dans une table `runs` avec un statut explicite (`queued`, `running`, `done`, `failed`, `interrupted`), exécuter les runs dans une tâche asyncio (ou un thread) unique démarrée par le lifespan, et marquer les runs `running` comme `interrupted` au démarrage. Les étapes sont idempotentes (clé d'étape, pas de réexécution d'un appel LLM déjà enregistré).
(b) **Sources** : https://fastapi.tiangolo.com/tutorial/background-tasks/ (Lu) pour la limite de `BackgroundTasks` ; https://arq-docs.helpmanual.io/ (Lu : arq v0.28.0, Redis requis, « pessimistic execution » : une tâche peut s'exécuter plus d'une fois, donc idempotence nécessaire) ; https://docs.celeryq.dev/en/stable/getting-started/introduction.html (Lu : Celery 5.7 indiqué, brokers RabbitMQ / Redis).
(c) **Problème résolu** : simulations qui survivent à une coupure de la requête HTTP, avec reprise après crash.
(d) **Intérêt pour ALERTE** : un run de plusieurs minutes avec appels LLM ne doit pas être perdu au redémarrage ; l'état de run sert aussi de source au flux SSE.
(e) **Composant** : `backend/app/runs/worker.py`, table `runs` et `run_steps`.
(f) **Limites** : un seul processus uvicorn (sinon chaque processus lance son worker) ; pas de répartition sur plusieurs machines ; une tâche asyncio qui bloque la boucle gèle les SSE : appels LLM en `httpx.AsyncClient`, pas de calcul CPU long. Celery et arq ajoutent Redis ou RabbitMQ, donc un service de plus, à ne pas introduire dans un conteneur unique sur 5 jours.
(g) **Vérification** : test qui démarre un run, tue le processus au milieu, redémarre et vérifie le statut `interrupted` puis la reprise à l'étape suivante ; test d'idempotence (rejouer une étape ne duplique pas l'entrée d'audit).

## 22. Journal d'audit en événements (event log) : version allégée

(a) **Pratique** : une table `audit_events` en ajout seul (append-only), avec `seq`, `prev_hash`, `hash` (SHA-256 du contenu et de `prev_hash`). Écrire l'événement dans la même transaction que l'action métier. Ne pas reconstruire l'état à partir des événements : l'état reste dans les tables métier.
(b) **Source** : https://martinfowler.com/eaaDev/EventSourcing.html (Lu, publié le 12 décembre 2005) : log d'événements, replay, snapshots, avantages (audit) et coûts (complexité, effets de bord au replay, difficulté à ajouter après coup). Le chaînage SHA-256 n'est pas couvert par cette source : décision propre à ALERTE, non sourcée.
(c) **Problème résolu** : prouver qu'un journal n'a pas été modifié et reconstituer une séquence d'événements.
(d) **Intérêt pour ALERTE** : exigence de traçabilité de l'exercice et des décisions des agents.
(e) **Composant** : `backend/app/audit/`.
(f) **Limites** : la chaîne détecte une modification mais ne protège pas contre la suppression de la fin du journal sans un ancrage externe (non vérifié, point de conception). Event sourcing complet : à éviter (voir liste ci-dessous).
(g) **Vérification** : test qui modifie un événement en base et vérifie que `verify_chain()` échoue ; test de suppression d'un événement intermédiaire.

## 23. Idempotence et machine à états pour les workflows

(a) **Pratique** : décrire les statuts d'un run et les transitions autorisées dans une table en code (dict de transitions) ; refuser toute transition absente ; chaque commande porte une clé d'idempotence.
(b) **Source** : aucune source officielle lue ; l'idempotence est décrite comme exigence par arq (https://arq-docs.helpmanual.io/, Lu). Non vérifié : formulation générale de machine à états (recommandation de conception).
(c) **Problème résolu** : transitions incohérentes (`done` puis `running`) et doubles exécutions après reprise.
(d) **Intérêt pour ALERTE** : un run ne doit passer à `done` qu'une fois.
(e) **Composant** : `backend/app/runs/state.py`.
(f) **Limites** : une bibliothèque de machine à états n'est pas nécessaire ; un dict et des tests suffisent.
(g) **Vérification** : test paramétré qui parcourt toutes les paires (état, action) et vérifie l'exception pour les transitions interdites.

---

## Pratiques à NE PAS appliquer au vu du délai de 5 jours

- Microservices, ou un service par agent.
- Event sourcing complet (reconstruction de l'état par replay) : seul le journal d'audit en ajout seul est retenu.
- Architecture hexagonale appliquée à chaque module avec couches de mapping complètes.
- Celery, RabbitMQ, Redis, arq : un service de plus pour une simulation qui tient dans un conteneur.
- PostgreSQL dès le départ : garder SQLite (WAL) et prévoir le passage uniquement si plusieurs écrivains apparaissent.
- Async SQLAlchemy de bout en bout si l'équipe ne le maîtrise pas : préférer la version synchrone.
- Redux, Zustand ou un store global : l'état local suffit ; TanStack Query seulement si le temps le permet.
- React Server Components, Next.js.
- Niveau C4 Code et diagrammes de déploiement détaillés (Kubernetes, etc.).
- MADR complet avec toutes les métadonnées : le gabarit minimal suffit.
- WCAG AAA et audit d'accessibilité complet.
- Tests de charge au-delà d'un test local simple.
- GraphQL, multi-tenant, authentification fédérée.

## URLs non lisibles ou partiellement lues

- https://adr.github.io/ : échec de lecture aux deux essais (remplacé par https://github.com/adr/madr et le gabarit brut).
- https://www.sqlite.org/wal.html et https://sqlite.org/wal.html : échec aux deux essais ; seul le snippet de recherche a été utilisé (non vérifié sur la page).
- https://www.sqlite.org/pragma.html : échec aux deux essais ; busy_timeout, synchronous et foreign_keys non vérifiés.
- https://www.sqlite.org/c3ref/busy_timeout.html : échec ; non vérifié.
- https://vite.dev/guide/env-and-mode : non consulté ; règle VITE_ non vérifiée.
- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html : lu seulement sur la première partie (100 000 caractères sur 344 664) ; l'erreur `MissingGreenlet` n'est pas citée par la page.
- https://fastapi.tiangolo.com/tutorial/server-sent-events/ : lu ; la limite de connexions n'est pas documentée sur cette page.
- https://pypi.org/project/fastapi/ : lu partiellement (100 000 caractères sur 128 893), suffisant pour la version.
- https://www.w3.org/TR/WCAG22/ : lu partiellement (100 000 caractères sur 269 706) ; critères individuels non détaillés.
- Sous-pages 12factor.net (/config, /processes, /disposability, /logs, /admin-processes) : listées, non lues une à une.
- https://c4model.com/ : la page d'accueil ne détaille pas les règles de notation ni les anti-patterns.
- https://www.radix-ui.com/... : une seule page lue ; shadcn/ui non lu.
- https://github.com/adr/madr : pas de version MADR précise.
- https://react.dev/learn/thinking-in-react : lu ; statut stable de React 19.3 non confirmé.
- Hexagonal et MonolithFirst : sources secondaires non citées ; la page Cockburn a été lue directement.

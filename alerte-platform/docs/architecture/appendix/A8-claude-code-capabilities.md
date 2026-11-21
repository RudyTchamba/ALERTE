> **Annexe — Capacités vérifiées de Claude Code (modèles, sous-agents, advisor).**
> Matériau de recherche brut produit le 2026-11-20 par un sous-agent (modèle Haiku 5.5), relu en diagonale par l'architecte. Les marqueurs « non vérifié » / `[NV]` / `[V]` / `[S]` sont ceux du sous-agent ; toute information utilisée dans le dossier principal est citée avec son niveau de vérification. Ce fichier est une pièce justificative, pas une spécification.

---

# 08 - Vérification des capacités Claude Code (doc officielle)

Date de vérification : 2026-11-20
Sources principales :
- Sous-agents : https://code.claude.com/docs/en/sub-agents.md
- Advisor (Claude Code) : https://code.claude.com/docs/en/advisor.md
- Advisor tool (API) : https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool.md
- Workflows : https://code.claude.com/docs/en/workflows.md
- Hooks : https://code.claude.com/docs/en/hooks.md
- Permissions : https://code.claude.com/docs/en/permissions.md
- Modèles : https://platform.claude.com/docs/en/models/{haiku-5-5,opus-5-5,sonnet-5-5,fable-5-2}/overview.md

Légende : [V] vérifié dans la doc ; [P] partiellement vérifié ; [NV] non vérifié / non trouvé.

---

## 1. Sous-agents personnalisés [V]

**Emplacement**
- Projet : `.claude/agents/*.md` (scan récursif ; Claude Code remonte aussi jusqu'à la racine du dépôt).
- Utilisateur : `~/.claude/agents/*.md`.
- L'identité vient du champ `name`, pas du chemin.
- Autres sources : réglages managés (priorité 1), flag CLI `--agents` (2), dossiers `agents/` des plugins (5).

**Frontmatter**

| Champ | Requis | Valeurs / rôle |
|---|---|---|
| `name` | oui | identifiant unique, 256 car. max, sans `:` |
| `description` | oui | quand déléguer au sous-agent |
| `tools` | non | liste séparée par virgules ou liste YAML ; hérite de tous les outils si omis |
| `disallowedTools` | non | outils à retirer |
| `model` | non | `sonnet`, `opus`, `haiku`, `fable`, un ID complet (ex. `claude-opus-5-5`), ou `inherit` |
| `isolation` | non | `worktree` (oui, ce champ existe) : exécution dans un worktree git temporaire, branché sur la branche par défaut (pas sur le HEAD du parent) ; nettoyé automatiquement si aucun changement |
| `effort` | non | `low`, `medium`, `high`, `xhigh`, `max` |
| `permissionMode` | non | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan` |
| `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `color`, etc. | non | voir la page |

Exemple officiel :
```markdown
---
name: code-improver
description: Scans files and suggests improvements. Use after writing or modifying code.
tools: Read, Grep, Glob
model: sonnet
isolation: worktree
effort: high
---
```

**Ordre de résolution du modèle** : 1) paramètre `model` du tool Agent ; 2) champ `model` du sous-agent ; 3) variable `CLAUDE_CODE_SUBAGENT_MODEL` ; 4) modèle de la conversation principale.

**Tool Agent**
- `model` : accepte un **alias uniquement** (`sonnet`, `opus`, `haiku`, ...), pas un ID complet ni `inherit`.
- `isolation` : la page indique qu'un appel Agent peut passer `isolation`, mais ne liste pas les valeurs acceptées. Valeur attendue `worktree` d'après le champ frontmatter [P] ; à confirmer dans le schéma actuel du tool.
- `effort` : paramètre par invocation (Claude Code v2.1.292+), pour les sous-agents non-fork.

**Coûts** : chaque sous-agent a sa propre fenêtre de contexte et ses propres requêtes, comptées dans les mêmes limites d'usage. Les résultats renvoyés consomment du contexte dans la conversation principale. Les descriptions combinées au-delà de 15 000 tokens déclenchent un avertissement au démarrage.

---

## 2. Flag `--advisor` [V]

Le flag **existe** dans la doc anglaise : `claude --advisor opus`.

**Ce qu'il fait**
- Définit le modèle conseiller pour une seule session, sans modifier le réglage persistant `advisorModel`. Le flag prime sur ce réglage pour la session.
- Trois moyens de l'activer : commande `/advisor` (sauvegardée dans `advisorModel`), réglage `"advisorModel": "opus"` dans settings.json, flag `--advisor` (session seule).
- Il n'apparaît pas dans `claude --help`.
- Désactivation : `/advisor off` ; variable `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1` (rend `--advisor` sans effet).

**Consultation**
- Le modèle principal (exécuteur) décide quand appeler le conseiller ; aucun réglage ne force ou plafonne les appels. On peut le demander dans le prompt.
- Le conseiller est un outil serveur, exécuté côté Anthropic, et reçoit la conversation complète (appels d'outils et résultats compris).
- Affichage : ligne `Advising`, puis `Reviewed`, `Declined` ou `Advisor unavailable (<code>)`. `Ctrl+O` affiche le conseil.

**Paires acceptées (extrait)**
- Haiku 4.5 : Fable, Opus, Sonnet, Haiku 5.5.
- Sonnet 5 / Haiku 5.5 : Fable, Opus 4.7+, Sonnet 5+, Haiku 5.5.
- Opus 4.7 / 4.8 : Fable, Opus 4.7+, Sonnet 5.5.
- Sonnet 5.5 : Fable, Opus 5+, Sonnet 5.5.
- Opus 5 / 5.5 : Fable, Opus 5+.
- Fable 5.2 : Fable 5.2 seul.
- Le conseiller doit être au moins aussi capable que le modèle principal. Un conseiller de rang inférieur n'est pas attaché aux requêtes.
- Alias `fable`, `opus`, `sonnet` ; ou ID complet (`claude-opus-5-5`, `claude-haiku-5-5`).
- Un lancement avec un conseiller invalide échoue ; en session `--background`, il démarre sans conseiller.

**Fournisseurs** : API Anthropic, Claude Platform on AWS, Claude Models on Google Cloud (Anthropic managed). Pas Bedrock, Google Cloud Agent Platform, Microsoft Foundry. Fonctionnalité expérimentale. Nécessite Claude Code v2.1.300+ sur les deux plateformes cloud indiquées. Dépend d'un flag de fonctionnalité récupéré depuis Anthropic (incompatible avec certaines variables comme `DISABLE_TELEMETRY`).

**Coûts et limites**
- API : tokens du conseiller facturés aux tarifs du conseiller, en plus de l'exécuteur.
- Abonnement : compte dans les limites du forfait ; un conseiller Fable peut être facturé sur les crédits d'usage selon le forfait.
- Consentement unique requis pour Fable selon le forfait (`/model fable`).
- Sortie typique du conseiller : 400 à 700 tokens de texte (API).
- Pas de plafond de session dans Claude Code. Côté API, `max_uses` (optionnel) plafonne les appels par tour.
- Activer ou désactiver l'advisor en cours de session ne casse pas le cache de prompt.

**Remarque** : une version traduite de la doc (allemand, portugais, italien) indique que le flag est « accepté mais sans effet » ; la version anglaise ne le dit pas. Vérifier avec `claude --help` / la version installée [NV pour ces versions].

---

## 3. « JEV » [NV, introuvable]

Recherche dans la doc Claude Code et sur le web (termes JEV + mode/agent/effort/thinking/verification) : **aucun résultat**. Rien dans la doc officielle ne correspond à « JEV ». Ne pas l'utiliser comme nom de fonctionnalité sans source. Si le terme vient d'un document interne ou d'un autre outil, le préciser.

---

## 4. Modèles et identifiants [V]

Confirmés sur les pages officielles de modèles (platform.claude.com) :

| Modèle | ID API | Contexte | Sortie max | Prix entrée / sortie (MTok) | Effort par défaut | Sortie |
|---|---|---|---|---|---|---|
| Fable 5.2 | `claude-fable-5-2` | 1M | 128K | 8 $ / 40 $ | high | 9 nov. 2026 |
| Opus 5.5 | `claude-opus-5-5` | 1M | 128K | 4 $ / 20 $ | medium | 22 sept. 2026 |
| Sonnet 5.5 | `claude-sonnet-5-5` | 1M | 128K | 2 $ / 10 $ | high | 28 sept. 2026 |
| Haiku 5.5 | `claude-haiku-5-5` | 1M | 128K | 0,10 $ / 0,50 $ (tarif palier : 0,50 $ / 2,50 $ au-delà de 100K tokens) | medium | 7 oct. 2026 |

- Les quatre IDs demandés sont exacts.
- Le cache en lecture est à 2,5 % (Fable) ou 5 % (Opus 5.5, Sonnet 5.5) ou 10 % du tarif d'entrée (pages de modèles).
- Batch API : -50 %.
- Opus 5.5 : réflexion adaptative toujours active, non désactivable.
- Fable 5.2 : `tool_choice` forcé (`any`, `tool`) renvoie une erreur 400 ; exige une rétention de données de 30 jours.
- Sonnet 5.5 : `temperature`, `top_p`, `top_k` renvoient une erreur 400.
- Haiku 5.5 : omettre `temperature`, `top_p`, `top_k`.
- Dans Claude Code, les alias `sonnet`, `opus`, `haiku`, `fable` sont résolus vers la version par défaut de chaque famille (la version peut évoluer avec Claude Code).

---

## 5. Workflows multi-agents (« ultracode ») [V]

Le terme **« ultracode » existe** dans la doc, mais désigne le réglage d'effort qui active l'orchestration automatique par workflow, pas un nom de produit distinct.

**Disponibilité**
- Dynamic workflows : tous les forfaits payants, accès API Anthropic, Amazon Bedrock, Google Cloud Agent Platform, Microsoft Foundry.
- Sur Pro : à activer dans la ligne « Dynamic workflows » de `/config`.
- Désactivation : `/config`, `"disableWorkflows": true` (settings), `CLAUDE_CODE_DISABLE_WORKFLOWS=1`, ou réglage managé.

**Opt-in**
- Mot-clé `ultracode` dans un prompt tapé à la main (terminal, extension IDE, Remote Control) ; ou demande explicite « use a workflow ».
- Pas déclenché avec `-p`, en tâche planifiée, via webhook ou commentaire de PR.
- `/effort ultracode` : active le mode pour toute la session (au niveau d'effort de la session ; `claude --effort ultracode` lance avec `xhigh`). Réglage `ultracode` pour le démarrage de chaque session. `/effort ultracode off` pour désactiver.
- Validation : en mode manuel, une confirmation par lancement ; en auto, première fois seulement ; en `-p` / SDK, pas d'invite, il faut une règle `allow` `Workflow` (ou `Workflow(<nom>)`), le mode auto, `bypassPermissions` ou un hook `PreToolUse` qui renvoie `allow`.

**Coût**
- Chaque workflow lance de nombreux sous-agents ; la consommation est nettement plus élevée qu'en conversation simple. Avec ultracode, chaque tâche de la session est concernée et les limites de forfait sont atteintes plus vite.
- Limites runtime : 16 agents concurrents par défaut (`CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS`, 1 à 256) ; 1 000 agents par exécution ; 4 096 éléments par `parallel()`/`pipeline()`.
- Avertissement « Large workflow » au-delà de 25 agents ou 1,5 M tokens projetés (sauf avec ultracode).
- Guide de taille (`workflowSizeGuideline`) : `small` (<5 agents), `medium` (<10, défaut), `large` (<50), `unrestricted`. Défaut `small` sur Pro (v2.1.271+).
- Modèle des agents : même ordre que les sous-agents.

---

## 6. Hooks et permissions (principe, rien créé) [V, sauf mention]

**Hook PreToolUse**
- Déclaré dans `settings.json` sous la clé `hooks`, par événement, avec groupes de `matcher` et handlers :
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [
          { "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/restrict-writes.sh",
            "timeout": 30 }
        ]
      }
    ]
  }
}
```
- Entrée JSON sur stdin : `tool_name`, `tool_input`, `tool_use_id`, `cwd`, `permission_mode`, etc. Le chemin est dans `tool_input.file_path` (confirmé dans l'exemple MCP ; schéma Write/Edit non lu intégralement [P]).
- Refus : exit code 2 (message sur stderr), ou JSON stdout avec `hookSpecificOutput.permissionDecision: "deny"` et `permissionDecisionReason`.
- Un hook exit 2 bloque même si une règle `allow` existe.
- Un hook qui renvoie `allow` ne contourne pas les règles `deny` ni `ask`.
- Un timeout ne bloque pas par défaut ; `"onFailure": "block"` pour bloquer en cas d'échec [P].
- Règle de principe : un hook est déterministe (script), mais la doc recommande les règles de permission pour les refus stricts ; le champ `if` est « best-effort ».
- Comportement des hooks en mode `bypassPermissions` : non confirmé [NV].
- Emplacement : `.claude/settings.json` (partagé, versionnable) ou `.claude/settings.local.json` (perso).
- Principe pour « alerte-platform/ uniquement » : le hook doit lire `tool_input.file_path`, le résoudre (chemin absolu, `..`, liens symboliques) et refuser s'il n'est pas sous `alerte-platform/`. Pour les lectures et l'édition, combiner avec les règles de permission.

**Règles de permission (`permissions` dans settings.json)**
- Clés : `allow`, `ask`, `deny`, `defaultMode`. Ordre d'évaluation : deny, puis ask, puis allow. La première correspondance l'emporte.
- Règles `Edit(...)` et `Read(...)` : syntaxe gitignore. `//chemin` = absolu depuis la racine ; `~/` = home ; `/chemin` = relatif au répertoire des réglages (pas à la racine du FS) ; `chemin` ou `./chemin` = relatif au répertoire courant.
- `Write(...)`, `Glob(...)`, `Grep(...)` avec un chemin ne sont pas appliqués : utiliser `Edit(...)` à la place (`Edit` couvre Write, NotebookEdit).
- Un `Read` deny bloque aussi Edit et Write sur le même chemin.
- Un `deny` bare (`Bash`, `Edit`) retire complètement l'outil du contexte de Claude.
- Un deny Bash est un filtre sur le texte de la commande, pas une frontière de sécurité.
- Un deny sur les écritures ne se formule pas comme « tout sauf X » de façon directe ; une règle allow-list n'existe pas pour ce cas dans la doc.
- Option native : `permissions.blockWritesOutsideWorkingDirectories` (v2.1.314+) : refuse Write, Edit, NotebookEdit en dehors des répertoires de travail. Ce n'est pas une restriction à un sous-dossier, et elle ne couvre ni Bash ni les sous-processus.
- Option : `permissions.disableBypassPermissionsMode` / `disableAutoMode` = `"disable"` (utile en managé).
- `permissions.denyInsteadOfPrompting` : refuse au lieu de demander (sessions non surveillées).
- La doc précise : « Permission rules are enforced by Claude Code, not by the model. »
- Sandboxing (`/sandboxing`) : application au niveau OS pour les commandes shell, indépendante du texte de commande.

---

## Points à confirmer [NV]
- Valeurs exactes acceptées par le paramètre `isolation` du tool Agent (seul le frontmatter `worktree` est confirmé).
- Comportement des hooks PreToolUse en `bypassPermissions`.
- Schéma exact des entrées Write/Edit dans `tool_input` (page hooks tronquée).
- Terme « JEV » : introuvable.

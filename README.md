Pour aller plus vite : [GETTING-STARTED](GETTING-STARTED.md)

## Étape 1 – Extraction

### Source

[API PandaScore](https://developers.pandascore.co/) (offre gratuite), données esport de League of Legends.

Choisie car elle couvre toutes les compétitions professionnelles (LEC, LCK, LFL, Worlds…) avec des identifiants qui relient ligues, saisons, tournois, matchs, équipes et joueurs : ces liens servent directement de clés pour la base relationnelle.

### Données extraites

| Fichier (`data/raw/`) | Endpoint | Période | Lignes |
|---|---|---|---|
| `leagues.json.gz` | `/lol/leagues` | tout | 136 |
| `series.json.gz` | `/lol/series` | depuis 2020 | 660 |
| `tournaments.json.gz` | `/lol/tournaments` | depuis 2020 | 1 593 |
| `matches.json.gz` | `/lol/matches` | depuis 2020 | 35 652 |
| `teams.json.gz` | `/lol/teams` | tout | 1 948 |
| `players.json.gz` | `/lol/players` | tout | 9 913 |

Écartés :
- statistiques détaillées des parties (kills, or…) : réservées aux offres payantes (403) ;
- classements par tournoi : une requête par tournoi, trop coûteux ; recalculables depuis les matchs ;
- champions : non reliés aux autres données.

### Fonctionnement

Lancement : `python -m etl.run` (script : `etl/extract/extract.py`).

- Chaque endpoint est parcouru page par page (100 lignes par requête), trié par `id`.
- Les réponses sont enregistrées telles quelles, en JSON compressé gzip (`matches` dépasse 100 Mo non compressé, limite de GitHub).
- Un fichier déjà présent n'est pas retéléchargé : relancer le script ne consomme aucune requête. Supprimer un fichier pour le réextraire.
- Quota de l'API : 1 000 requêtes par heure. L'extraction complète en coûte environ 500. Le script vérifie le quota restant avant chaque endpoint et attend automatiquement quand l'API demande de ralentir (erreur 429).

## Étape 2 – Transformation

Lancement : `python -m etl.run`, juste après la validation des contrats d'entrée (script : `etl/transform/transform.py`). Les fichiers bruts ne sont jamais modifiés.

### Tables produites (`data/processed/`, CSV)

| Fichier | Contenu | Lignes |
|---|---|---|
| `leagues.csv` | ligues ayant au moins une série, un tournoi ou un match depuis 2020 | 108 |
| `series.csv` | saisons (ex. « LEC Spring 2024 ») | 664 |
| `tournaments.csv` | phases d'une saison (saison régulière, playoffs…) | 1 596 |
| `teams.csv` | équipes | 1 948 |
| `players.csv` | joueurs | 9 913 |
| `matches.csv` | matchs | 35 619 |
| `match_teams.csv` | les 2 équipes de chaque match, avec score et `is_winner` | 71 238 |
| `games.csv` | parties de chaque match (un BO5 = jusqu'à 5 parties) | 61 328 |

Chaque table a un identifiant `id` unique. Les liens vers une autre table s'appellent `<table>_id` (ex. `tournament_id`, `winner_team_id`).

### Traitements

- **Aplatissement** : les données imbriquées dans les matchs sont sorties dans leurs propres tables (`match_teams` depuis `opponents`/`results`, `games` depuis `games`).
- **Colonnes** : seules les colonnes utiles sont gardées (logos, liens de streaming, bloc `videogame` toujours égal à « LoL » retirés). Noms en `snake_case`, `serie_id` renommé `series_id`, `winner_id` renommé `winner_team_id`.
- **Doublons** : une seule ligne par `id`.
- **Valeurs manquantes** : textes vides remplacés par une valeur vide. Les informations inconnues restent vides (ex. 1 449 joueurs sans nationalité, 259 sans rôle). Les 33 matchs « TBD vs TBD » sans équipes sont supprimés.
- **Formats** : dates converties en UTC, `tier` en minuscules (`unranked` remplacé par vide), identifiants en entiers.
- **Dates incohérentes** : quand la fin est avant le début, la fin est mise à vide (1 série, 3 matchs, 1 partie). Exemple : la série 7032 commence le 16/09/2023 et finit le 17/01/2023.
- **Unités** : durée des parties passée de secondes en minutes (`length_minutes`). Sont mises à vide : les 95 parties terminées avec une durée de 0, les 16 parties de moins d'une minute (surtout des forfaits enregistrés en quelques secondes), et les 9 parties de plus de 95 minutes. Le record professionnel est de 94 min 37 s ([Guinness](https://www.guinnessworldrecords.com/world-records/117985-longest-professional-league-of-legends-game)). Au-delà, PandaScore compte les pauses ou se contredit : par exemple SDX vs IGY (LDL, 2021) annonce 140,8 minutes alors que son début et sa fin ne sont séparés que de 41 minutes. Le prize pool `"9,000 Euro"` est séparé en `prizepool_amount = 9000` et `prizepool_currency = EUR` (code ISO). Les devises ne sont pas converties, faute de taux de change historiques.
- **Récupération des séries et tournois manquants** : le filtre « depuis 2020 » de l'extraction écarte les saisons commencées fin 2019 dont les matchs ont lieu en 2020 (ex. LCK Spring 2020, commencée le 8 septembre 2019). Sans correction, 143 matchs pointaient vers un tournoi absent et 4 tournois vers une série absente. Ces lignes sont reconstruites depuis leurs copies imbriquées dans les matchs et tournois.
- **Enrichissement** : `year` et `duration_minutes` (somme des parties, vide si l'une d'elles a une durée inconnue) dans `matches`, `is_winner` dans `match_teams` (vide pour les égalités et les matchs non joués).

### Vérifications

À la fin, le script contrôle chaque lien entre tables :
- lien obligatoire (ex. le tournoi d'un match) absent : le script s'arrête avec une erreur ;
- lien facultatif (gagnant, équipe actuelle d'un joueur) absent : il est mis à vide et signalé. Seul cas actuel : 1 joueur dont l'équipe actuelle n'existe pas dans `teams`.

### Contrats de données

Un contrat décrit ce que chaque table doit respecter : colonnes, types, valeurs autorisées, valeurs vides permises. Il est vérifié à chaque exécution, à deux endroits.

| | Contrat d'entrée | Contrat de sortie |
|---|---|---|
| Fichiers | `etl/contracts/raw/<source>.json` (JSON Schema, un par source de l'API) | `etl/contracts/processed.py` (pandera, un schéma par table CSV) |
| Vérifie | les données brutes de PandaScore, avant la transformation | les 8 tables, avant l'écriture des CSV |
| Protège contre | un changement de format de l'API | une erreur dans `transform.py` |
| Si une ligne est fausse | elle est écartée dans `data/quarantine/<source>.jsonl`, avec la date et le motif. Le pipeline continue. | le pipeline s'arrête. Le détail est écrit dans `data/quarantine/<table>_violations.csv`. |
| Arrêt | si plus de 5 % des lignes d'une source sont écartées (`MAX_REJECT_RATE` dans `etl/config.py`) | dès la première violation |

Le contrat d'entrée ne décrit que les champs lus par la transformation : l'API en envoie beaucoup d'autres, qui sont acceptés. Une ligne écartée dont d'autres lignes dépendent (ex. une équipe présente dans des matchs) arrête quand même le pipeline à la vérification des liens.

Exemple de ligne en quarantaine, si l'API renvoyait un rôle inconnu :

```json
{"quarantined_at": "2026-10-23T14:02:11+00:00", "errors": ["$.role : 'coach' is not one of ['top', 'jun', 'mid', 'adc', 'sup', None]"], "row": {"id": 1, "role": "coach", "...": "..."}}
```

Chaque contrat porte une version (`x-version` en JSON, `VERSION` en Python), suivant MAJEUR.MINEUR.CORRECTIF : ajouter un champ facultatif augmente le MINEUR, supprimer un champ ou changer son type augmente le MAJEUR.

### Matchs nuls

307 matchs terminés n'ont pas de gagnant (`draw = True`). Ce n'est pas une erreur : une partie ne peut pas finir sur un nul, mais un match en BO2 (deux parties) peut finir à 1-1. Les 307 nuls sont tous des BO2 à 1-1, surtout en LCS Academy, NACL et European Pro League, qui utilisaient ce format en saison régulière ([NACL 2023](https://lolesports.com/news/2023-nacl-summer-split-primer)).

## Étape 3 – Chargement

Lancement : `python -m etl.run`, après la transformation (scripts : `etl/load/`). Les 8 CSV de `data/processed/` sont chargés dans la base SQLite `database/lol.db` (non versionnée : elle se régénère).

| Fichier | Rôle |
|---|---|
| `schema.sql` | tables, clés primaires, liens entre tables, index. Peut être relancé sans effet (`IF NOT EXISTS`) |
| `db.py` | `get_connection()` : ouvre la base, active les liens entre tables, valide si tout va bien, annule en cas d'erreur, ferme toujours |
| `load.py` | lit les CSV et les écrit table par table |

### Fonctionnement

- **Upsert** : chaque ligne est insérée, ou mise à jour si son `id` existe déjà (`INSERT ... ON CONFLICT DO UPDATE`). Clé de `match_teams` : `(match_id, team_id)`. Relancer le chargement ne crée donc aucun doublon : deux exécutions de suite donnent 108 ligues, 35 619 matchs, etc.
- **Une seule transaction** : les 8 tables sont validées ensemble ou pas du tout. Si `games` échoue, `matches` n'est pas écrit non plus.
- **Ordre** : ligues, équipes, séries, tournois, joueurs, matchs, `match_teams`, parties. Un parent est chargé avant ses enfants.
- **Contrôles avant validation** : nombre de lignes en base égal à celui du CSV, et `PRAGMA foreign_key_check` sans lien cassé. Sinon le chargement est annulé et le pipeline s'arrête.
- **Types** : les vides deviennent `NULL`, les booléens `0`/`1`, les dates du texte UTC (`2020-01-03 08:20:06+00:00`).
- **Limite** : une ligne supprimée du CSV n'est pas supprimée de la base par l'upsert. Le contrôle du nombre de lignes le signale ; supprimer `database/lol.db` règle le cas.

## Étape 4 – Interface web

Lancement (depuis la racine du projet, après le chargement) :

```bash
python -m streamlit run web/app.py
```

L'interface ([Streamlit](https://streamlit.io/) et [Plotly](https://plotly.com/python/)) est un tableau de bord : elle lit `database/lol.db` en lecture seule et ne peut rien modifier.

Filtres (barre latérale) : période et ligues. Ils s'appliquent à tout le tableau de bord, sauf au nombre de joueurs actifs. Les statistiques portent sur les matchs terminés.

| Zone | Contenu |
|---|---|
| Chiffres clés | matchs, ligues, équipes, durée moyenne d'une partie, joueurs actifs |
| Graphiques | matchs par année, ligues les plus actives, équipes les plus victorieuses, durée des parties |
| Tableau | les 10 derniers matchs terminés |

| Fichier | Rôle |
|---|---|
| `web/app.py` | mise en page du tableau de bord |
| `web/queries.py` | requêtes SQL et connexion en lecture seule |
| `web/components.py` | graphiques et cartes communs : même couleur, mêmes marges partout |
| `.streamlit/config.toml` | thème clair et sombre (couleurs identiques à celles des graphiques) |

## Étape 5 – Orchestration avec Airflow

Le pipeline tourne aussi comme un workflow [Airflow](https://airflow.apache.org/) (DAG `lol_etl`, fichier `dags/lol_etl.py`), dans Docker :

```bash
docker compose up -d --build
```

La même commande lance aussi l'interface Streamlit sur http://localhost:8501. Airflow est sur http://localhost:8080 (pas de connexion en local). Le DAG est en pause à la création : l'activer dans l'interface ou cliquer sur « Trigger » pour un lancement manuel. `docker compose down` arrête tout.

```
extract_<source> → validate_<source> ─┐   (6 sources en parallèle, sauf les extractions)
                                      ├→ transform → load
```

| Tâche | Rôle |
|---|---|
| `extract_<source>` | télécharge un endpoint de l'API vers `data/raw/`. Une seule extraction à la fois (quota partagé) |
| `validate_<source>` | contrat d'entrée : les lignes conformes vont dans `data/validated/`, les autres en quarantaine. Échec au-delà de 5 % |
| `transform` | nettoyage, contrat de sortie, écriture des CSV de `data/processed/` |
| `load` | upsert dans SQLite, contrôles avant validation de la transaction |

- **Rejouable** : l'extraction remplace les fichiers bruts à chaque exécution (`extract_endpoint(..., force=True)`), la validation et la transformation réécrivent leurs fichiers, le chargement est un upsert. Relancer un jour ou une tâche ne crée aucun doublon.
- **Reprise ciblée** : si `extract_matches` échoue, seule cette tâche est relancée, pas les 5 autres. 2 nouvelles tentatives, 10 minutes d'écart. Le quota de l'API (1 000 requêtes par heure) peut en être la cause.
- **Une exécution à la fois** (`max_active_runs=1`). Une exécution complète dure environ 9 minutes, dont 8 pour les matchs.
- **Aucune logique dans le DAG** : il appelle les fonctions de `etl/`. `python -m etl.run` reste possible sans Airflow.
- Le projet est monté dans le conteneur : Airflow écrit dans les mêmes `data/` et `database/lol.db` que l'interface web, qui voit donc les nouvelles données.
- Fichiers : `docker-compose.yml` (Airflow + PostgreSQL pour ses métadonnées), `docker/Dockerfile` (image + dépendances de `requirements-etl.txt`). Le mode `standalone` est réservé au développement local.

## Organisation du dépôt

```
settings.py          chemins partagés (aucun secret), importé par etl/ et web/
etl/                 pipeline : extract/, validate/, transform/, load/, contracts/, config.py (token API), run.py
dags/                DAG Airflow (appelle etl/)
web/                 interface Streamlit
docker/ docker-compose.yml   Airflow en local
data/                raw/, validated/, processed/, quarantine/
database/            lol.db (non versionnée)
```

`web/` n'importe jamais `etl/` : l'interface fonctionne sans le fichier `.env` et sans le token de l'API.

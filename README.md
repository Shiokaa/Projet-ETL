Pour commencer à travailler sur le projet : [GETTING-STARTED](GETTING-STARTED.md)

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

Lancement : `python main.py` (script : `scripts/extract/extract.py`).

- Chaque endpoint est parcouru page par page (100 lignes par requête), trié par `id`.
- Les réponses sont enregistrées telles quelles, en JSON compressé gzip (`matches` dépasse 100 Mo non compressé, limite de GitHub).
- Un fichier déjà présent n'est pas retéléchargé : relancer le script ne consomme aucune requête. Supprimer un fichier pour le réextraire.
- Quota de l'API : 1 000 requêtes par heure. L'extraction complète en coûte environ 500. Le script vérifie le quota restant avant chaque endpoint et attend automatiquement quand l'API demande de ralentir (erreur 429).

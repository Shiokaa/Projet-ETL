# Extraction : télécharge les données LoL de PandaScore et les enregistre en JSON brut dans data/raw/.
import gzip
import json
import math
import time

import requests

from config import RAW_DIR, START_DATE, headers, url

PER_PAGE = 100
DATE_FILTER = {"range[begin_at]": f"{START_DATE},2100-01-01T00:00:00Z"}

ENDPOINTS = {
    "leagues": {},
    "series": DATE_FILTER,
    "tournaments": DATE_FILTER,
    "matches": DATE_FILTER,
    "teams": {},
    "players": {},
}


def fetch_all(endpoint, filters):
    rows = []
    page = 1
    while True:
        params = {**filters, "page": page, "per_page": PER_PAGE, "sort": "id"}
        reponse = requests.get(f"{url}/{endpoint}", headers=headers, params=params, timeout=30)
        # Limite courte de l'API, distincte du quota horaire : on attend le délai indiqué.
        if reponse.status_code == 429:
            time.sleep(int(reponse.headers.get("Retry-After", 30)))
            continue
        reponse.raise_for_status()

        if page == 1:
            pages_needed = math.ceil(int(reponse.headers["X-Total"]) / PER_PAGE)
            remaining = int(reponse.headers["X-Rate-Limit-Remaining"])
            # On s'arrête avant de vider le quota plutôt que d'échouer au milieu de l'endpoint.
            if pages_needed > remaining:
                raise RuntimeError(
                    f"{endpoint} : {pages_needed} requêtes nécessaires, {remaining} restantes. "
                    "Relancer dans une heure."
                )

        data = reponse.json()
        rows.extend(data)
        if len(data) < PER_PAGE:
            return rows
        page += 1


def extract():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for endpoint, filters in ENDPOINTS.items():
        # Compressé : matches.json dépasse la limite de 100 Mo par fichier de GitHub.
        path = RAW_DIR / f"{endpoint}.json.gz"
        if path.exists():
            print(f"{endpoint} : déjà présent, ignoré")
            continue

        rows = fetch_all(endpoint, filters)
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        print(f"{endpoint} : {len(rows)} lignes -> {path.name}")

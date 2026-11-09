# Chemins du projet, partagés par le pipeline (etl/) et l'interface (web/). Aucun secret ici.
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
RAW_DIR = ROOT_DIR / "data" / "raw"
VALIDATED_DIR = ROOT_DIR / "data" / "validated"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
QUARANTINE_DIR = ROOT_DIR / "data" / "quarantine"
CONTRACTS_DIR = ROOT_DIR / "etl" / "contracts"
DB_PATH = ROOT_DIR / "database" / "lol.db"

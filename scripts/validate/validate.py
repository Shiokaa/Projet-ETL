# Validation des contrats : quarantaine des données brutes non conformes, arrêt si une table de sortie ne l'est pas.
import json
from datetime import datetime, timezone

import pandera.pandas as pa
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from config import CONTRACTS_DIR, MAX_REJECT_RATE, QUARANTINE_DIR
from contracts.processed import SCHEMAS

RAW_SCHEMAS = {
    path.stem: json.loads(path.read_text(encoding="utf-8")) for path in (CONTRACTS_DIR / "raw").glob("*.json")
}
# Permet au contrat des matchs de pointer vers ceux des séries et tournois par leur $id.
REGISTRY = Registry().with_resources(
    (schema["$id"], Resource.from_contents(schema)) for schema in RAW_SCHEMAS.values()
)


def validate_raw(name, rows):
    validator = Draft202012Validator(RAW_SCHEMAS[name], registry=REGISTRY)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    valid, rejected = [], []
    for row in rows:
        errors = [f"{error.json_path} : {error.message[:200]}" for error in validator.iter_errors(row)]
        if errors:
            rejected.append({"quarantined_at": now, "errors": errors, "row": row})
        else:
            valid.append(row)

    path = QUARANTINE_DIR / f"{name}.jsonl"
    path.unlink(missing_ok=True)
    if rejected:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rejected)
        print(f"  {name} : {len(rejected)} lignes non conformes -> quarantine/{path.name}")
    rate = len(rejected) / len(rows) if rows else 0
    if rate > MAX_REJECT_RATE:
        raise ValueError(f"{name} : {rate:.1%} de lignes rejetées, au-delà du seuil de {MAX_REJECT_RATE:.0%}")
    return valid


def validate_table(name, df):
    path = QUARANTINE_DIR / f"{name}_violations.csv"
    path.unlink(missing_ok=True)
    try:
        return SCHEMAS[name].validate(df, lazy=True)
    except pa.errors.SchemaErrors as e:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        e.failure_cases.to_csv(path, index=False)
        raise ValueError(
            f"{name} : {len(e.failure_cases)} violations du contrat de sortie, détail dans quarantine/{path.name}"
        ) from None

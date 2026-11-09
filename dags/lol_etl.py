# DAG Airflow : orchestre le pipeline etl/ (extraction, contrats d'entrée, transformation, chargement).
from datetime import datetime, timedelta

from airflow.sdk import dag, task

from etl.extract.extract import ENDPOINTS


@dag(
    dag_id="lol_etl",
    schedule="@hourly",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["etl", "lol"],
)
def lol_etl():
    # Une seule extraction à la fois : toutes partagent le quota de l'API PandaScore.
    @task(max_active_tis_per_dag=1)
    def extract(endpoint):
        from etl.extract.extract import extract_endpoint

        extract_endpoint(endpoint, force=True)

    @task
    def validate(source):
        from etl.validate.validate import validate_source

        validate_source(source)

    @task
    def transform():
        from etl.transform.transform import transform as run

        run()

    @task
    def load():
        from etl.load.load import load as run

        run()

    transformed = transform()
    for name in ENDPOINTS:
        extract.override(task_id=f"extract_{name}")(name) >> validate.override(task_id=f"validate_{name}")(name) >> transformed
    transformed >> load()


lol_etl()

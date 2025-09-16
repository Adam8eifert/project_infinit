from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

default_args = {
    'start_date': datetime(2024, 1, 1),
    'owner': 'adam_seifert',
    'retries': 1,
}

with DAG(
    dag_id='nsm_etl_pipeline',
    default_args=default_args,
    description='ETL pipeline pro sekty a nová náboženská hnutí v ČR',
    schedule_interval=None,  # ruční spouštění
    catchup=False,
    tags=['etl', 'scraping', 'nlp', 'db']
) as dag:

    run_spider = BashOperator(
        task_id='run_sekty_tv_spider',
        bash_command='cd /opt/airflow/project && scrapy runspider scraping/sekty_tv_spider.py',
    )

    process_nlp = BashOperator(
        task_id='run_nlp_analysis',
        bash_command='cd /opt/airflow/project && python processing/nlp_analysis.py',
    )

    load_to_db = BashOperator(
        task_id='import_csv_to_db',
        bash_command='cd /opt/airflow/project && python processing/import_csv_to_db.py',
    )

    run_spider >> process_nlp >> load_to_db

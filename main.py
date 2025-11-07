# 📁 main.py – ETL process orchestrator using OOP structure
# Designed to be simple but extensible for future enhancements

from processing.etl_pipeline import ETLPipeline
import logging

if __name__ == "__main__":
    try:
        # Initialize and run the ETL pipeline
        pipeline = ETLPipeline()
        pipeline.run_pipeline()
        
    except Exception as e:
        logging.error(f"ETL pipeline failed: {e}")
        raise

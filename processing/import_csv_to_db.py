# 📁 processing/import_csv_to_db.py

import pandas as pd
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from database.db_loader import DBConnector, Source
from datetime import datetime
import logging

class CSVtoDatabaseLoader:
    """Bezpečný import CSV dat do databáze s validací a logováním"""

    def __init__(self):
        self.db = DBConnector()
        self.session = self.db.Session()
        self.setup_logging()

    def setup_logging(self):
        """Nastavení logování pro sledování importu"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('import_log.txt'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def validate_row(self, row, csv_path):
        """Validace jednotlivých řádků dat"""
        errors = []
        
        # Kontrola prázdných hodnot
        if not row.get("url"):
            errors.append("Chybí URL")
        if not row.get("title"):
            errors.append("Chybí titulek")
        if not row.get("text") or len(str(row.get("text", "")).strip()) < 10:
            errors.append("Chybí nebo příliš krátký text")
            
        # Validace URL
        if row.get("url") and not row["url"].startswith(("http://", "https://")):
            errors.append("Neplatné URL")
            
        # Validace data
        try:
            pd.to_datetime(row.get("scraped_at"))
        except:
            errors.append("Neplatné datum")
            
        if errors:
            self.logger.warning(f"Validační chyby v {csv_path}: {', '.join(errors)}")
            return False
        return True

    def clean_row(self, row):
        """Čištění a normalizace dat"""
        return {
            "movement_id": None,  # bude doplněno později
            "source_name": str(row.get("source_name", "")).strip(),
            "source_type": str(row.get("source_type", "")).strip(),
            "publication_date": pd.to_datetime(row.get("scraped_at"), errors="coerce"),
            "sentiment_rating": None,  # bude doplněno při NLP
            "url": str(row.get("url", "")).strip(),
            "title": str(row.get("title", "")).strip(),
            "text": str(row.get("text", "")).strip()
        }

    def load_csv_to_sources(self, csv_path: str):
        """Import CSV do databáze s validací a error handlingem"""
        csv_path = Path(csv_path)
        if not csv_path.exists():
            self.logger.error(f"Soubor neexistuje: {csv_path}")
            return

        try:
            df = pd.read_csv(csv_path)
            self.logger.info(f"Načítám {len(df)} řádků z {csv_path}")

            # Kontrola požadovaných sloupců
            required_columns = {"source_name", "source_type", "title", "url", "text", "scraped_at"}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                raise ValueError(f"Chybí sloupce: {missing}")

            # Import po batches pro lepší výkon a možnost rollbacku
            batch_size = 100
            imported = 0
            skipped = 0

            for batch_start in range(0, len(df), batch_size):
                batch = df.iloc[batch_start:batch_start + batch_size]
                
                for _, row in batch.iterrows():
                    try:
                        # Validace a čištění
                        if not self.validate_row(row, csv_path):
                            skipped += 1
                            continue
                            
                        cleaned_data = self.clean_row(row)
                        source = Source(**cleaned_data)
                        self.session.add(source)
                        imported += 1
                        
                    except Exception as e:
                        self.logger.error(f"Chyba při zpracování řádku: {e}")
                        skipped += 1
                        continue
                
                try:
                    self.session.commit()
                except IntegrityError:
                    self.session.rollback()
                    self.logger.warning("Duplicitní URL - přeskakuji batch")
                    skipped += len(batch)
                except Exception as e:
                    self.session.rollback()
                    self.logger.error(f"Chyba při ukládání batch: {e}")
                    skipped += len(batch)

            self.logger.info(f"Import dokončen: {imported} importováno, {skipped} přeskočeno")
        except IntegrityError:
            self.session.rollback()
            print("⚠️ Duplicitní URL – některé záznamy již existují.")
        except Exception as e:
            self.session.rollback()
            print(f"❌ Chyba při načítání CSV: {e}")
        finally:
            self.session.close()

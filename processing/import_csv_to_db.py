# 📁 processing/import_csv_to_db.py

import pandas as pd
from sqlalchemy.exc import IntegrityError
from database.db_loader import DBConnector, Source
from datetime import datetime

class CSVtoDatabaseLoader:
    def __init__(self):
        self.db = DBConnector()
        self.session = self.db.Session()

    def load_csv_to_sources(self, csv_path: str):
        try:
            df = pd.read_csv(csv_path)

            required_columns = {"source_name", "source_type", "title", "url", "text", "scraped_at"}
            if not required_columns.issubset(df.columns):
                raise ValueError(f"CSV soubor {csv_path} neobsahuje požadované sloupce.")

            for _, row in df.iterrows():
                source = Source(
                    movement_id=None,  # bude doplněno později při mapování
                    source_name=row["source_name"],
                    source_type=row["source_type"],
                    publication_date=pd.to_datetime(row["scraped_at"], errors="coerce"),
                    sentiment_rating=None,  # sentiment bude doplněn až při NLP zpracování
                    url=row["url"]
                )
                self.session.add(source)

            self.session.commit()
            print(f"✅ Načteno z {csv_path} do tabulky sources.")
        except IntegrityError:
            self.session.rollback()
            print("⚠️ Duplicitní URL – některé záznamy již existují.")
        except Exception as e:
            self.session.rollback()
            print(f"❌ Chyba při načítání CSV: {e}")
        finally:
            self.session.close()

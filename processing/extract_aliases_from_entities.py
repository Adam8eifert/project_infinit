# 📁 processing/extract_aliases_from_entities.py
# ETL pipeline: Získání aliasů z entit (ORG) → porovnání s databází → výstup do CSV

import pandas as pd
import ast
from fuzzywuzzy import fuzz
from database.db_loader import DBConnector, Movement
from pathlib import Path

class AliasETL:
    def __init__(self, input_csv_path, similarity_threshold=80):
        self.input_path = Path(input_csv_path)
        self.output_path = Path("export/csv/aliases_from_" + self.input_path.stem + ".csv")
        self.similarity_threshold = similarity_threshold
        self.movements = self._load_movements()
        self.results = []

    def _load_movements(self):
        db = DBConnector()
        session = db.Session()
        query = session.query(Movement.id, Movement.canonical_name).all()
        session.close()
        return [(m.id, m.canonical_name) for m in query]

    def extract(self):
        df = pd.read_csv(self.input_path)
        for _, row in df.iterrows():
            raw_entities = row.get("named_entities")
            if isinstance(raw_entities, str):
                try:
                    entities = ast.literal_eval(raw_entities)
                    for ent in entities:
                        if ent.get("type") == "ORG":
                            self._match_and_store(ent["text"])
                except:
                    continue

    def _match_and_store(self, candidate):
        for mid, cname in self.movements:
            score = fuzz.token_set_ratio(candidate.lower(), cname.lower())
            if score >= self.similarity_threshold and candidate.lower() != cname.lower():
                self.results.append({
                    "movement_id": mid,
                    "alias": candidate
                })
                break

    def save(self):
        if not self.results:
            print("⚠️ Nebyly nalezeny žádné vhodné aliasy.")
            return

        df_out = pd.DataFrame(self.results)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(self.output_path, index=False, encoding="utf-8")
        print(f"✅ Uloženo {len(df_out)} aliasů do {self.output_path}")


# 🧪 Lokální test
if __name__ == "__main__":
    etl = AliasETL("export/csv/dingir_cleaned.csv")
    etl.extract()
    etl.save()

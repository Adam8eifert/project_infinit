# 📁 processing/extract_locations_from_entities.py
# ETL pipeline: Získání geografických dat z entit a vytvoření návrhů pro tabulku 'locations'

import pandas as pd
import ast
from pathlib import Path

class LocationETL:
    def __init__(self, input_csv_path, movement_id=None):
        self.input_path = Path(input_csv_path)
        self.output_path = Path("export/csv/locations_from_" + self.input_path.stem + ".csv")
        self.movement_id = movement_id  # může být None, bude potřeba doplnit ručně nebo jiným skriptem
        self.results = []

    def extract(self):
        df = pd.read_csv(self.input_path)
        for _, row in df.iterrows():
            entities_raw = row.get("named_entities")
            if isinstance(entities_raw, str):
                try:
                    entities = ast.literal_eval(entities_raw)
                    locations = [e["text"] for e in entities if e.get("type") == "LOC"]
                    for loc in locations:
                        self.results.append({
                            "movement_id": self.movement_id,
                            "municipality": loc,
                            "district": "",
                            "region": "",
                            "year_founded": ""
                        })
                except:
                    continue

    def save(self):
        if not self.results:
            print("⚠️ Nebyly nalezeny žádné lokace.")
            return

        df_out = pd.DataFrame(self.results).drop_duplicates()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(self.output_path, index=False, encoding="utf-8")
        print(f"✅ Uloženo {len(df_out)} záznamů do {self.output_path}")


# 🧪 Lokální test
if __name__ == "__main__":
    etl = LocationETL("export/csv/sekty_tv_cleaned.csv")
    etl.extract()
    etl.save()

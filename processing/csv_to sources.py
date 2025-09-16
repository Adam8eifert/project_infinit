# 📁 processing/csv_to_sources.py
# Vygeneruje návrhy pro tabulku 'sources' z čistého CSV (např. výstup z NLP)

import pandas as pd
from datetime import datetime
from pathlib import Path

class CSVToSourcesGenerator:
    def __init__(self, input_csv_path, movement_id=None):
        self.input_path = Path(input_csv_path)
        self.output_path = Path("export/csv/sources_from_" + self.input_path.stem + ".csv")
        self.movement_id = movement_id  # může být None, pokud se bude doplňovat ručně

    def generate(self):
        df = pd.read_csv(self.input_path)

        sources = []
        for _, row in df.iterrows():
            sources.append({
                "movement_id": self.movement_id,
                "source_name": row.get("source_name", "nezjištěno"),
                "source_type": row.get("source_type", "textový výstup"),
                "publication_date": row.get("scraped_at", datetime.utcnow().isoformat()),
                "sentiment_rating": row.get("sentiment", "neutrální"),
                "url": row.get("url", "")
            })

        df_out = pd.DataFrame(sources)
        df_out.to_csv(self.output_path, index=False, encoding="utf-8")
        print(f"✅ Generováno {len(df_out)} záznamů → {self.output_path}")


# 🧪 Lokální test
if __name__ == "__main__":
    generator = CSVToSourcesGenerator("export/csv/dingir_cleaned.csv")
    generator.generate()

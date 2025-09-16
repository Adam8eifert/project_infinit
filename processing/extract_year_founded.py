# 📁 processing/extract_year_founded.py
# Extrakce přibližného roku založení hnutí z textu článku nebo PDF stránky

import pandas as pd
import re
from pathlib import Path

class YearFoundedExtractor:
    def __init__(self, input_csv_path):
        self.input_path = Path(input_csv_path)
        self.output_path = Path("export/csv/year_founded_from_" + self.input_path.stem + ".csv")
        self.results = []

    def extract(self):
        df = pd.read_csv(self.input_path)
        for _, row in df.iterrows():
            text = row.get("text") or row.get("raw_text")
            if isinstance(text, str):
                year = self._find_year(text)
                if year:
                    self.results.append({
                        "file_or_url": row.get("file_name") or row.get("url"),
                        "year_founded": year,
                        "sample_text": text[:150].replace("\n", " ")
                    })

    def _find_year(self, text):
        # Hledá výrazy typu "založeno v roce 1995", "v r. 2002", "roku 2011" apod.
        matches = re.findall(r"(?:založeno|založen|vzniklo|v r\.?|roku|od roku)[^\d]{0,10}(\d{4})", text, flags=re.IGNORECASE)
        for y in matches:
            try:
                y_int = int(y)
                if 1850 < y_int < 2100:
                    return y_int
            except:
                continue
        return None

    def save(self):
        if not self.results:
            print("⚠️ Nebyly nalezeny žádné roky.")
            return

        df_out = pd.DataFrame(self.results)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(self.output_path, index=False, encoding="utf-8")
        print(f"✅ Extrahováno {len(df_out)} roků → {self.output_path}")


# 🧪 Lokální test
if __name__ == "__main__":
    extractor = YearFoundedExtractor("export/csv/pdf_texts.csv")
    extractor.extract()
    extractor.save()

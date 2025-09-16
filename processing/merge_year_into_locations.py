# 📁 processing/merge_year_into_locations.py
# Spojí výstup z extract_year_founded s locations_from_X.csv podle souboru nebo URL

import pandas as pd
from pathlib import Path

class LocationYearMerger:
    def __init__(self, locations_csv, years_csv):
        self.locations_csv = Path(locations_csv)
        self.years_csv = Path(years_csv)
        self.output_path = Path("export/csv/locations_final_" + self.locations_csv.stem + ".csv")

    def merge(self):
        df_locs = pd.read_csv(self.locations_csv)
        df_years = pd.read_csv(self.years_csv)

        # Spojení podle 'file_or_url' vs 'file_name' nebo 'url'
        key = "file_name" if "file_name" in df_locs.columns else "url"
        df_locs[key] = df_locs[key].fillna("")
        df_years["file_or_url"] = df_years["file_or_url"].fillna("")

        merged = df_locs.merge(df_years[["file_or_url", "year_founded"]], left_on=key, right_on="file_or_url", how="left")

        merged["year_founded"] = merged["year_founded_y"].combine_first(merged["year_founded_x"])
        merged = merged.drop(columns=["file_or_url", "year_founded_x", "year_founded_y"], errors="ignore")

        merged.to_csv(self.output_path, index=False, encoding="utf-8")
        print(f"✅ Výsledné lokace s rokem uloženy do {self.output_path}")


# 🧪 Lokální test
if __name__ == "__main__":
    merger = LocationYearMerger(
        "export/csv/locations_from_sekty_tv_cleaned.csv",
        "export/csv/year_founded_from_pdf_texts.csv"
    )
    merger.merge()

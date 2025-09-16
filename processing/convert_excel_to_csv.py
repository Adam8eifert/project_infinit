# 📁 processing/convert_excel_to_csv.py
# Hromadný převod všech .xlsx souborů ze složky /data/xlsx do CSV

import pandas as pd
from pathlib import Path

class ExcelToCSVConverter:
    def __init__(self, input_dir="data/xlsx", output_dir="export/csv"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def convert_all(self):
        excel_files = list(self.input_dir.glob("*.xlsx"))
        if not excel_files:
            print("⚠️ Nebyly nalezeny žádné .xlsx soubory.")
            return

        for file in excel_files:
            try:
                df = pd.read_excel(file, engine="openpyxl")
                output_file = self.output_dir / (file.stem + ".csv")
                df.to_csv(output_file, index=False, encoding="utf-8")
                print(f"✅ Převod dokončen: {file.name} → {output_file.name}")
            except Exception as e:
                print(f"❌ Chyba při převodu {file.name}: {e}")


# 🧪 Lokální test
if __name__ == "__main__":
    converter = ExcelToCSVConverter()
    converter.convert_all()

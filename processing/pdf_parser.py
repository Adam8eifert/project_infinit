# 📁 processing/pdf_parser.py
# Načítání a extrakce textu z PDF souborů (akademické práce, dokumenty)

import fitz  # PyMuPDF
import os
import pandas as pd
from pathlib import Path
from datetime import datetime

class PDFExtractor:
    def __init__(self, pdf_dir="data/pdf"):
        self.pdf_dir = Path(pdf_dir)
        self.results = []
        self.output_path = Path("export/csv/pdf_texts.csv")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def extract_all(self):
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        for pdf_path in pdf_files:
            self.extract_from_file(pdf_path)

        df = pd.DataFrame(self.results)
        df.to_csv(self.output_path, index=False, encoding="utf-8")
        print(f"✅ Extrahováno {len(df)} stran z {len(pdf_files)} PDF → {self.output_path}")

    def extract_from_file(self, pdf_path):
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                text = doc.load_page(page_num).get_text().strip()
                if text:
                    self.results.append({
                        "file_name": pdf_path.name,
                        "page_num": page_num + 1,
                        "text": text,
                        "source_type": "PDF dokument",
                        "scraped_at": datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"❌ Chyba při čtení {pdf_path.name}: {e}")


# 🧪 Spuštění samostatně
if __name__ == "__main__":
    extractor = PDFExtractor()
    extractor.extract_all()

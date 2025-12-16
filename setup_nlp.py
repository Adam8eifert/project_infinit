"""
Setup script pro stažení potřebných NLP modelů
"""

import subprocess
import sys

print("Stahuji české modely pro spaCy...")
try:
    subprocess.run([sys.executable, "-m", "spacy", "download", "cs_core_news_md"], check=True)
    print("✅ spaCy model stažen")
except subprocess.CalledProcessError as e:
    print(f"❌ Chyba při stahování spaCy modelu: {e}")

print("NLP modely jsou připraveny!")
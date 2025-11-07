"""
Setup script pro stažení potřebných NLP modelů
"""

import stanza
print("Stahuji české modely pro Stanza...")
stanza.download('cs')
print("✅ Modely staženy")
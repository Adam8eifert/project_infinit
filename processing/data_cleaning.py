# 📁 processing/data_cleaning.py
# Zpracování CSV z exportu spiderů – lemmatizace, entita extrakce, fuzzy matching

import pandas as pd
from processing.nlp_analysis import CzechTextAnalyzer
from fuzzywuzzy import fuzz

class DataCleaner:
    def __init__(self, input_csv_path):
        self.df = pd.read_csv(input_csv_path)
        self.analyzer = CzechTextAnalyzer()

    def clean_and_extract(self):
        # Normalizuj názvy (lemmatizuj)
        self.df['canonical_lemma'] = self.df['canonical_name'].apply(self._lemmatize_first_word)

        # Extrahuj entity z textu (lokace, organizace)
        self.df['named_entities'] = self.df['raw_text'].apply(self.analyzer.extract_named_entities)

        # Proveď fuzzy matching (budoucí použití)
        self.df['fuzzy_match_score'] = self.df['canonical_name'].apply(
            lambda x: fuzz.token_set_ratio(x.lower(), "Testovací hnutí světla")
        )

        return self.df

    def _lemmatize_first_word(self, text):
        try:
            lemmas = self.analyzer.analyze(text)
            return lemmas[0]['lemma'] if lemmas else text
        except:
            return text

    def save_cleaned(self, output_path):
        self.df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"✅ Vyčištěný soubor uložen: {output_path}")


# 🧪 Testovací běh
if __name__ == "__main__":
    cleaner = DataCleaner("export/csv/sekty_tv.csv")
    df_cleaned = cleaner.clean_and_extract()
    cleaner.save_cleaned("export/csv/sekty_tv_cleaned.csv")

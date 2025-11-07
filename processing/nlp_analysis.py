# 📁 processing/nlp_analysis.py
# Lemmatizace, POS tagging, NER a základní sentiment pomocí Stanza a Transformers

import stanza
from transformers import pipeline

class CzechTextAnalyzer:
    def __init__(self):
        # Inicializace Stanza pipeline pro češtinu
        self.nlp = stanza.Pipeline(
            lang='cs', 
            processors='tokenize,mwt,pos,lemma,ner', 
            use_gpu=False
        )

        # Načtení sentiment pipeline (multilingual)
        self.sentiment_analyzer = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")

    def analyze(self, text: str):
        doc = self.nlp(text)
        result = []

        for sentence in doc.sentences:
            for word in sentence.words:
                result.append({
                    "text": word.text,
                    "lemma": word.lemma,
                    "pos": word.pos
                })
        return result

    def extract_named_entities(self, text: str):
        doc = self.nlp(text)
        entities = []

        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "type": ent.type
            })
        return entities

    def analyze_sentiment(self, text: str):
        try:
            result = self.sentiment_analyzer(text[:512])[0]  # zkrácení kvůli délce vstupu
            return result['label']  # např. '1 star', '5 stars'
        except Exception as e:
            return f"Chyba: {e}"



# 📁 processing/nlp_analysis.py
# NLP analysis using Hugging Face Transformers and spaCy
# Lemmatization, POS tagging, NER and basic sentiment processing

import spacy
from transformers import pipeline
import re
from typing import List, Dict, Any, Optional
from collections import Counter


class CzechTextAnalyzer:
    """
    NLP analyzer using spaCy for basic processing and Hugging Face for sentiment and NER.
    Optimized to use multilingual fallback models.
    """

    def __init__(self):
        # Load spaCy model
        self.spacy_available = False
        self.nlp = None
        
        # Priority list: Using the multilingual model you successfully installed
        models_to_try = ['xx_ent_wiki_sm', 'xx_sent_ud_sm', 'cs_core_news_sm']
        
        for model_name in models_to_try:
            try:
                self.nlp = spacy.load(model_name)
                self.spacy_available = True
                print(f"✅ Loaded spaCy model: {model_name}")
                break
            except Exception:
                continue

        if not self.spacy_available:
            print("⚠️ No spaCy model available, using basic fallback mode")

        # Load Hugging Face sentiment analysis pipeline
        # Using '# type: ignore' to suppress Pylance overloads issues
        try:
            self.sentiment_analyzer = pipeline(
                task="sentiment-analysis",
                model="nlptown/bert-base-multilingual-uncased-sentiment"
            ) # type: ignore
            self.sentiment_available = True
            print("✅ Sentiment analysis model loaded")
        except Exception as e:
            print(f"⚠️ Sentiment analysis not available: {e}")
            self.sentiment_analyzer = None
            self.sentiment_available = False

        # Load NER pipeline (WikiNeural works without authentication)
        try:
            self.ner_analyzer = pipeline(
                task="ner",
                model="Babelscape/wikineural-multilingual-ner",
                aggregation_strategy="simple"
            ) # type: ignore
            self.ner_available = True
            print("✅ NER model loaded (WikiNeural Multilingual)")
        except Exception as e:
            print(f"⚠️ NER pipeline not available: {e}")
            self.ner_analyzer = None
            self.ner_available = False

    def analyze(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyze text using spaCy for tokenization, POS tagging, and lemmatization.
        """
        if not text:
            return []

        if not self.spacy_available or self.nlp is None:
            # Fallback: basic tokenization if spaCy failed
            return [{'text': word, 'lemma': word.lower(), 'pos': 'UNK'}
                   for word in text.split()]

        doc = self.nlp(text)
        result = []

        for token in doc:
            result.append({
                'text': token.text,
                'lemma': token.lemma_,
                'pos': token.pos_,
                'tag': token.tag_,
                'dep': token.dep_,
                'is_stop': token.is_stop,
                'is_alpha': token.is_alpha
            })

        return result

    def extract_named_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities using Hugging Face NER model or spaCy fallback.
        """
        if not text:
            return []

        # Try Hugging Face NER first
        if self.ner_available and self.ner_analyzer is not None:
            try:
                # Truncate text to avoid model limits
                entities = self.ner_analyzer(text[:512])
                return [{
                    'text': str(e['word']),
                    'label': str(e['entity_group']),
                    'confidence': float(e['score']),
                    'start': int(e['start']),
                    'end': int(e['end'])
                } for e in entities]
            except Exception as e:
                print(f"⚠️ NER analysis failed: {e}")

        # Fallback to spaCy NER
        if self.spacy_available and self.nlp is not None:
            doc = self.nlp(text)
            return [{
                'text': ent.text,
                'label': ent.label_,
                'confidence': 0.8,
                'start': ent.start_char,
                'end': ent.end_char
            } for ent in doc.ents]

        return []

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment (1-5 stars) and return label and score.
        """
        if not text or not self.sentiment_available or self.sentiment_analyzer is None:
            return {'label': 'neutral', 'score': 0.5}

        try:
            # BERT model limit is 512 tokens
            result = self.sentiment_analyzer(text[:512])
            if result:
                # The model returns list like [{'label': '1 star', 'score': 0.99}]
                best = result[0]
                return {
                    'label': str(best['label']),
                    'score': float(best['score'])
                }
        except Exception as e:
            print(f"⚠️ Sentiment analysis failed: {e}")

        return {'label': 'neutral', 'score': 0.5}

    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract most frequent keywords (nouns, proper nouns).
        """
        if self.spacy_available and self.nlp is not None:
            doc = self.nlp(text)
            keywords = [t.lemma_.lower() for t in doc 
                       if t.pos_ in ['NOUN', 'PROPN'] and not t.is_stop and len(t.text) > 2]
            return [word for word, _ in Counter(keywords).most_common(top_n)]

        return [w.lower() for w in text.split() if len(w) > 4][:top_n]

    def preprocess_text(self, text: str) -> str:
        """
        Clean text and normalize whitespaces.
        """
        if not text: return ""
        text = re.sub(r'\s+', ' ', text.strip())
        return text
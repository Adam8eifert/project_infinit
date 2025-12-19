# 📁 processing/nlp_analysis.py
# NLP analysis using Hugging Face Transformers and spaCy
# Lemmatization, POS tagging, NER and basic sentiment

import spacy
from transformers import pipeline
import re
from typing import List, Dict, Any


class CzechTextAnalyzer:
    """
    NLP analyzer using spaCy for Czech language processing and Hugging Face for sentiment analysis.
    """

    def __init__(self):
        # Load Czech spaCy model
        self.spacy_available = False
        try:
            # Try different Czech models
            for model_name in ['cs_core_news_md', 'cs_core_news_sm', 'en_core_web_sm']:
                try:
                    self.nlp = spacy.load(model_name)
                    self.spacy_available = True
                    print(f"✅ Loaded spaCy model: {model_name}")
                    break
                except OSError:
                    continue

            if not self.spacy_available:
                print("⚠️ No spaCy model available, using fallback mode")
                self.nlp = None
        except ImportError:
            print("⚠️ spaCy not available, using fallback mode")
            self.nlp = None
            self.spacy_available = False

        # Load Hugging Face sentiment analysis pipeline (multilingual)
        try:
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="nlptown/bert-base-multilingual-uncased-sentiment",
                top_k=None  # Get all scores instead of deprecated return_all_scores
            )
            self.sentiment_available = True
            print("✅ Sentiment analysis model loaded")
        except Exception as e:
            print(f"⚠️ Sentiment analysis not available: {e}")
            self.sentiment_analyzer = None
            self.sentiment_available = False

        # Load NER pipeline for Czech
        try:
            self.ner_analyzer = pipeline(
                "ner",
                model="ufal/robeczech-ner",
                aggregation_strategy="simple"
            )
            self.ner_available = True
            print("✅ NER model loaded")
        except Exception as e:
            print(f"⚠️ NER pipeline not available: {e}")
            self.ner_analyzer = None
            self.ner_available = False

    def analyze(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyze text using spaCy for tokenization, POS tagging, and lemmatization.
        """
        if not self.spacy_available or self.nlp is None:
            # Fallback: basic tokenization
            return [{'text': word, 'lemma': word.lower(), 'pos': 'UNK', 'tag': 'UNK', 'dep': 'UNK', 'is_stop': False, 'is_alpha': word.isalpha()}
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
        Extract named entities using Hugging Face NER model for Czech.
        """
        if not self.ner_available or self.ner_analyzer is None:
            # Fallback: return empty list
            return []

        try:
            entities = self.ner_analyzer(text)
            result = []

            if entities and isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict) and all(key in entity for key in ['word', 'entity_group', 'score', 'start', 'end']):
                        result.append({
                            'text': entity['word'],
                            'label': entity['entity_group'],
                            'confidence': entity['score'],
                            'start': entity['start'],
                            'end': entity['end']
                        })

            return result
        except Exception as e:
                print(f"⚠️ NER analysis failed: {e}")

        # Fallback to spaCy NER or basic fallback
        if self.spacy_available and self.nlp is not None:
            doc = self.nlp(text)
            result = []
            for ent in doc.ents:
                result.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'confidence': 0.8,  # spaCy doesn't provide confidence
                    'start': ent.start_char,
                    'end': ent.end_char
                })
            return result
        else:
            # Basic fallback - no NER
            return []

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment using Hugging Face sentiment model.
        """
        if not self.sentiment_available or self.sentiment_analyzer is None:
            # Fallback sentiment
            return {'label': 'neutral', 'score': 0.5, 'confidence': 0.5}

        try:
            # Truncate text to first 512 characters for sentiment analysis
            truncated_text = text[:512]
            result = self.sentiment_analyzer(truncated_text)

            if result and isinstance(result, list) and len(result) > 0:
                # result is a list of sentiment predictions
                sentiments = result[0]  # First item in batch
                if isinstance(sentiments, list) and sentiments:
                    # Find the sentiment with highest score
                    best_sentiment = max(sentiments, key=lambda x: x.get('score', 0) if isinstance(x, dict) else 0)
                    if isinstance(best_sentiment, dict) and 'label' in best_sentiment and 'score' in best_sentiment:
                        return {
                            'label': best_sentiment['label'],
                            'score': best_sentiment['score'],
                            'confidence': best_sentiment['score']
                        }
        except Exception as e:
            print(f"⚠️ Sentiment analysis failed: {e}")

        # Fallback - neutral sentiment
        return {
            'label': 'NEUTRAL',
            'score': 0.5,
            'confidence': 0.5
        }

    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract keywords using spaCy (nouns, proper nouns, adjectives).
        """
        if self.spacy_available and self.nlp is not None:
            try:
                doc = self.nlp(text)
                keywords = []

                for token in doc:
                    if token.pos_ in ['NOUN', 'PROPN', 'ADJ'] and not token.is_stop and len(token.text) > 2:
                        keywords.append(token.lemma_.lower())

                # Return most frequent keywords
                from collections import Counter
                keyword_counts = Counter(keywords)
                return [word for word, _ in keyword_counts.most_common(top_n)]
            except Exception as e:
                print(f"⚠️ Keyword extraction failed: {e}")

        # Basic fallback - split by spaces and filter
        words = text.lower().split()
        keywords = [word for word in words if len(word) > 3 and word.isalpha()]
        from collections import Counter
        keyword_counts = Counter(keywords)
        return [word for word, _ in keyword_counts.most_common(top_n)]

    def get_text_stats(self, text: str) -> Dict[str, Any]:
        """
        Get basic text statistics.
        """
        if self.spacy_available and self.nlp is not None:
            try:
                doc = self.nlp(text)

                return {
                    'word_count': len([token for token in doc if token.is_alpha]),
                    'sentence_count': len(list(doc.sents)),
                    'avg_word_length': sum(len(token.text) for token in doc if token.is_alpha) / max(1, len([token for token in doc if token.is_alpha])),
                    'unique_words': len(set(token.lemma_.lower() for token in doc if token.is_alpha and not token.is_stop)),
                    'language': doc.lang_ if hasattr(doc, 'lang_') else 'cs'
                }
            except Exception as e:
                print(f"⚠️ Text stats calculation failed: {e}")

        # Basic fallback statistics
        words = [word for word in text.split() if word.isalpha()]
        sentences = text.split('.')

        return {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_word_length': sum(len(word) for word in words) / max(1, len(words)),
            'unique_words': len(set(word.lower() for word in words)),
            'language': 'cs'  # assumed Czech
        }

    def preprocess_text(self, text: str) -> str:
        """
        Basic text preprocessing: lowercase, remove extra whitespace, normalize.
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Basic normalization
        text = text.lower()

        return text



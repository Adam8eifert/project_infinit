# 📁 processing/nlp_analysis.py
# NLP analysis using Hugging Face Transformers and spaCy
# Lemmatization, POS tagging, NER and basic sentiment processing

import spacy
import transformers as _transformers
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
                break
            except Exception:
                continue

        # If no spaCy model is available we operate in a lightweight fallback mode.

        # Load Hugging Face sentiment analysis pipeline
        # Using '# type: ignore' to suppress Pylance overloads issues
        try:
            # Defer actual pipeline creation until first use to make it
            # easier to patch in tests (monkeypatching module attributes
            # before import could otherwise be brittle).
            self.sentiment_analyzer = None
            self.sentiment_available = True
            self.sentiment_tried = False
        except Exception as e:
            print(f"⚠️ Sentiment analysis not available: {e}")
            self.sentiment_analyzer = None
            self.sentiment_available = False

        # Load NER pipeline (WikiNeural works without authentication)
        try:
            self.ner_analyzer = _transformers.pipeline(
                task="ner",  # type: ignore
                model="Babelscape/wikineural-multilingual-ner",
                aggregation_strategy="simple"
            ) # type: ignore
            self.ner_available = True
        except Exception:
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

        # Some tests provide a mocked Doc that is not iterable but exposes
        # `_tokens` attribute. Handle both real spaCy Docs and such mocks.
        # If a mock Doc provides `_tokens`, prefer that (class __iter__ may
        # return an empty iterator in some test mocks).
        if hasattr(doc, '_tokens') and getattr(doc, '_tokens') is not None:
            iterator = iter(getattr(doc, '_tokens'))
        else:
            try:
                iterator = iter(doc)
            except TypeError:
                iterator = iter(getattr(doc, '_tokens', []))



        for token in iterator:
            # Multilingual model may not have lemma, use text as fallback
            lemma = getattr(token, 'lemma_', None) or getattr(token, 'lemma', None) or token.text.lower()
            if lemma == token.text:
                lemma = token.text.lower()

            result.append({
                'text': getattr(token, 'text', str(token)),
                'lemma': lemma,
                'pos': getattr(token, 'pos_', getattr(token, 'pos', 'X')),
                'tag': getattr(token, 'tag_', None),
                'dep': getattr(token, 'dep_', None),
                'is_stop': getattr(token, 'is_stop', False),
                'is_alpha': getattr(token, 'is_alpha', True)
            })

        return result

    def extract_named_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities grouped by type (movements, persons, locations).
        Returns dict with 'movements', 'persons', 'locations' keys.
        """
        if not text:
            return {'movements': [], 'persons': [], 'locations': []}

        result = {'movements': [], 'persons': [], 'locations': []}
        
        # Try Hugging Face NER first
        if self.ner_available and self.ner_analyzer is not None:
            try:
                entities = self.ner_analyzer(text[:512])
                for e in entities:
                    label = str(e.get('entity_group', '')).upper()
                    word = str(e.get('word', '')).strip()
                    
                    if label == 'PER':
                        result['persons'].append(word)
                    elif label == 'LOC':
                        result['locations'].append(word)
                    elif label == 'ORG':
                        result['movements'].append(word)
                
                return result
            except Exception as e:
                print(f"⚠️ NER analysis failed: {e}")

        # Fallback to spaCy NER
        if self.spacy_available and self.nlp is not None:
            doc = self.nlp(text)
            for ent in doc.ents:
                label = ent.label_.upper()
                if label == 'PERSON':
                    result['persons'].append(ent.text)
                elif label == 'GPE' or label == 'LOC':
                    result['locations'].append(ent.text)
                elif label == 'ORG':
                    result['movements'].append(ent.text)

        return result

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment and return dict with score (-1 to 1) and label.
        
        Returns:
            dict with keys:
            - 'score': float between -1 (negative) and 1 (positive)
            - 'label': 'positive' | 'neutral' | 'negative'
        """
        if not text or not self.sentiment_available:
            return {'score': 0.0, 'label': 'neutral'}

        try:
            # Initialize pipeline lazily
            if self.sentiment_analyzer is None and not getattr(self, 'sentiment_tried', False):
                try:
                    self.sentiment_analyzer = _transformers.pipeline(
                        task="sentiment-analysis",  # type: ignore
                        model="nlptown/bert-base-multilingual-uncased-sentiment"
                    ) # type: ignore
                except Exception:
                    self.sentiment_available = False
                    self.sentiment_analyzer = None
                finally:
                    self.sentiment_tried = True

            if not self.sentiment_analyzer:
                # Fallback heuristic
                return self._heuristic_sentiment(text)

            result = self.sentiment_analyzer(text[:512])
            if result:
                first = result[0]
                if isinstance(first, list):
                    best = first[0]
                else:
                    best = first
                
                label = str(best.get('label', 'NEUTRAL')).lower()
                score_value = float(best.get('score', 0.0))
                
                # Convert label to internal format and score to -1..1 range
                if 'positive' in label:
                    sentiment_label = 'positive'
                    sentiment_score = abs(score_value)
                elif 'negative' in label:
                    sentiment_label = 'negative'
                    sentiment_score = -abs(score_value)
                else:
                    sentiment_label = 'neutral'
                    sentiment_score = 0.0
                
                return {
                    'score': max(-1.0, min(1.0, sentiment_score)),
                    'label': sentiment_label
                }
        except Exception as e:
            print(f"⚠️ Sentiment analysis failed: {e}")

        return {'score': 0.0, 'label': 'neutral'}

    def _heuristic_sentiment(self, text: str) -> Dict[str, Any]:
        """Fallback sentiment analysis using keyword heuristics"""
        import unicodedata
        
        lower = (text or '').lower()
        lower_norm = ''.join(c for c in unicodedata.normalize('NFKD', lower) 
                            if not unicodedata.combining(c))
        
        positive_words = ['dobrý', 'dobry', 'pozitivní', 'pozitivni', 'dobrá', 'dobrych', 'skvělý', 'skvelý', 'geniální', 'genialni']
        negative_words = ['špatný', 'spatny', 'negativní', 'negativni', 'horší', 'horsi', 'hrozný', 'hrozny', 'zlý', 'zly']
        
        pos_count = sum(1 for word in positive_words if word in lower_norm)
        neg_count = sum(1 for word in negative_words if word in lower_norm)
        
        if pos_count > neg_count:
            return {'score': 0.5, 'label': 'positive'}
        elif neg_count > pos_count:
            return {'score': -0.5, 'label': 'negative'}
        else:
            return {'score': 0.0, 'label': 'neutral'}

    def calculate_risk_score(self, text: str) -> float:
        """
        Calculate risk score (0.0 to 1.0) based on text content.
        Higher score = higher risk.
        
        Based on:
        - Presence of extreme language
        - Mentions of harm, violence
        - NER confidence for organization mentions
        """
        if not text:
            return 0.0
        
        lower = text.lower()
        
        # High-risk keywords
        high_risk = ['násilí', 'navrh', 'sebevražda', 'vražda', 'zbraň', 'smrt', 'chaos', 'zavraždění']
        medium_risk = ['kontrola', 'manipulace', 'psychologický', 'psychologicka', 'kult', 'sekt']
        low_risk = ['hnutí', 'hnutim', 'komunita', 'organizace']
        
        high_count = sum(1 for word in high_risk if word in lower)
        med_count = sum(1 for word in medium_risk if word in lower)
        low_count = sum(1 for word in low_risk if word in lower)
        
        # Calculate score (0.0 to 1.0)
        total_words = len(text.split())
        risk_ratio = (high_count * 0.9 + med_count * 0.5 + low_count * 0.1) / max(total_words, 100)
        
        return max(0.0, min(1.0, risk_ratio * 2))  # Scale and cap

    def get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level enum"""
        if risk_score < 0.33:
            return 'low'
        elif risk_score < 0.66:
            return 'medium'
        else:
            return 'high'

    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract most frequent keywords (nouns, proper nouns, or non-stop alphabetic words).
        """
        if self.spacy_available and self.nlp is not None:
            doc = self.nlp(text)
            # Use both POS tags and simple heuristics (non-stop words, len > 2)
            keywords = []

            try:
                iterator = iter(doc)
            except TypeError:
                iterator = iter(getattr(doc, '_tokens', []))

            for t in iterator:
                is_stop = getattr(t, 'is_stop', False)
                text_val = getattr(t, 'text', str(t))
                pos_val = getattr(t, 'pos_', getattr(t, 'pos', None))
                is_alpha = getattr(t, 'is_alpha', True)

                # Include nouns, proper nouns, or any non-stop word longer than 2 chars
                if not is_stop and len(text_val) > 2 and (pos_val in ['NOUN', 'PROPN'] or is_alpha):
                    # Use lemma if available and different from text, otherwise use lowercase text
                    lemma_val = getattr(t, 'lemma_', None) or getattr(t, 'lemma', None) or text_val
                    word = lemma_val.lower() if (lemma_val and lemma_val != text_val) else text_val.lower()
                    keywords.append(word)
            
            # Return most common keywords
            if keywords:
                return [word for word, _ in Counter(keywords).most_common(top_n)]

        # Fallback: simple extraction
        return [w.lower() for w in text.split() if len(w) > 4 and w.isalpha()][:top_n]

    def preprocess_text(self, text: str) -> str:
        r"""
        Clean text: join hyphenated line-breaks, normalize whitespace, and lowercase.
        - remove hyphen + newline sequences that split words (r"-\n\s*")
        - collapse any whitespace sequence into single space
        - strip leading/trailing whitespace and lowercase
        """
        if not text:
            return ""
        # Remove hyphenation at line breaks (e.g., "slovo-\nnoveslovo" -> "slovonoveslovo")
        text = re.sub(r"-\n\s*", "", text)
        # Normalize all whitespace to single spaces
        text = re.sub(r"\s+", " ", text)
        return text.strip().lower()

    def normalize_person_name(self, name: str) -> str:
        """
        Normalize Czech person name by removing accents and extra spaces.
        Note: Czech declension handling is done via fuzzy matching in _is_same_person_name.
        """
        import unicodedata
        import re
        
        if not name:
            return ""
        
        # Normalize: lowercase, remove diacritics
        normalized = name.lower()
        
        # Remove Czech diacritics
        normalized = unicodedata.normalize("NFKD", normalized)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        
        # Remove non-alphanumeric except spaces
        normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
        
        # Collapse multiple spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()
        
        return normalized

    def get_text_stats(self, text: str) -> Dict[str, int]:
        """Return basic text statistics used in tests.

        Currently returns a dictionary with at least the 'word_count' key.
        Word count is computed by splitting on any unicode whitespace.
        """
        if not text:
            return {'word_count': 0}
        # Split on any whitespace sequence to count words
        return {'word_count': len(text.split())}
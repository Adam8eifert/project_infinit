import pytest
from unittest.mock import patch, MagicMock


def test_nlp_analysis_monkeypatched(monkeypatch):
    # Mock spaCy components
    class MockDoc:
        def __init__(self, text):
            self.text = text
            self.lang_ = 'cs'
            self.ents = []
            self.sents = [MockSent()]

    class MockSent:
        pass

    class MockToken:
        def __init__(self, text, lemma, pos, tag='tag', dep='dep', is_stop=False, is_alpha=True):
            self.text = text
            self.lemma_ = lemma
            self.pos_ = pos
            self.tag_ = tag
            self.dep_ = dep
            self.is_stop = is_stop
            self.is_alpha = is_alpha

    class MockNLP:
        def __init__(self, tokens):
            self.tokens = tokens

        def __call__(self, text):
            doc = MockDoc(text)
            doc.__iter__ = lambda: iter(self.tokens)
            return doc

    # Create mock tokens
    mock_tokens = [
        MockToken("Hnutí", "hnutí", "NOUN"),
        MockToken("Grálu", "grál", "PROPN")
    ]

    # Mock transformers pipeline
    def mock_sentiment_pipeline(task, model=None, return_all_scores=None):
        return lambda text: [[
            {'label': '3 stars', 'score': 0.8},
            {'label': '4 stars', 'score': 0.2}
        ]]

    def mock_ner_pipeline(task, model=None, aggregation_strategy=None):
        return lambda text: []

    # Patch the imports
    monkeypatch.setattr('spacy.load', lambda x: MockNLP(mock_tokens))
    monkeypatch.setattr('transformers.pipeline', mock_sentiment_pipeline)

    # Import after patching
    from processing.nlp_analysis import CzechTextAnalyzer

    analyzer = CzechTextAnalyzer()

    lemmas = analyzer.analyze('Hnutí Grálu')
    assert any(item['lemma'] == 'grál' for item in lemmas)

    entities = analyzer.extract_named_entities('Hnutí Grálu')
    assert isinstance(entities, list)

    sentiment = analyzer.analyze_sentiment('Dobrá zkušenost')
    assert sentiment == '3 stars'

    keywords = analyzer.extract_keywords('Hnutí Grálu je zajímavé')
    assert isinstance(keywords, list)

    stats = analyzer.get_text_stats('Test text')
    assert 'word_count' in stats

    preprocessed = analyzer.preprocess_text('  Test   TEXT  ')
    assert preprocessed == 'test   text'

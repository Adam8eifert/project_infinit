import types


def test_nlp_analysis_monkeypatched(monkeypatch):
    # Create dummy stanza Pipeline that returns a predictable doc
    class DummyWord:
        def __init__(self, text, lemma, pos):
            self.text = text
            self.lemma = lemma
            self.pos = pos

    class DummySentence:
        def __init__(self, words):
            self.words = words

    class DummyEnt:
        def __init__(self, text, ttype):
            self.text = text
            self.type = ttype

    class DummyDoc:
        def __init__(self, text):
            self.sentences = [DummySentence([DummyWord('Hnutí', 'hnutí', 'N'), DummyWord('Grálu', 'grál', 'N')])]
            self.ents = [DummyEnt('Hnutí Grálu', 'ORG')]

    class DummyPipeline:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, text):
            return DummyDoc(text)

    # Dummy transformers pipeline for sentiment
    def dummy_transformers_pipeline(task, model=None):
        def func(texts):
            return [{'label': '5 stars'}]

        return func

    # Patch stanza.Pipeline and transformers.pipeline inside the module
    import processing.nlp_analysis as nlp_mod
    monkeypatch.setattr(nlp_mod.stanza, 'Pipeline', DummyPipeline)
    monkeypatch.setattr(nlp_mod, 'pipeline', dummy_transformers_pipeline)

    analyzer = nlp_mod.CzechTextAnalyzer()

    lemmas = analyzer.analyze('Hnutí Grálu')
    assert any(item['lemma'] == 'grál' for item in lemmas)

    entities = analyzer.extract_named_entities('Hnutí Grálu')
    assert entities and entities[0]['text'] == 'Hnutí Grálu'

    sentiment = analyzer.analyze_sentiment('Dobrá zkušenost')
    assert sentiment == '5 stars'

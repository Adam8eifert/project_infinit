from scraping.keywords import contains_relevant_keywords, is_excluded_content


def test_contains_relevant_keywords_positive():
    text = "Tento článek popisuje kult a sekty v ČR"
    assert contains_relevant_keywords(text)


def test_contains_relevant_keywords_negative():
    text = "Toto je článek o fotbalu a sportu"
    assert not contains_relevant_keywords(text)


def test_is_excluded_content():
    # EXCLUDE terms include words like 'politika' (possibly prefixed with '-')
    assert is_excluded_content("Tento příspěvek se týká politiky a voleb")
    assert not is_excluded_content("Diskuse o náboženství a spiritualitě")

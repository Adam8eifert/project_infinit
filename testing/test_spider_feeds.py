from pathlib import Path

from extracting.medium_seznam_spider import MediumSeznamSpider
from extracting.google_spider import GoogleNewsRSSSpider
from extracting.csv_utils import get_output_csv_for_source


def test_medium_seznam_feeds_point_to_config():
    spider = MediumSeznamSpider()
    feeds = spider.custom_settings.get('FEEDS')
    assert feeds, 'FEEDS must be set'

    feed_path = next(iter(feeds.keys()))
    expected = str(get_output_csv_for_source('medium_seznam'))
    assert str(feed_path).endswith(expected)


def test_google_news_feeds_point_to_config():
    spider = GoogleNewsRSSSpider()
    feeds = spider.custom_settings.get('FEEDS')
    assert feeds, 'FEEDS must be set'

    feed_path = next(iter(feeds.keys()))
    expected = str(get_output_csv_for_source('google_news'))
    assert str(feed_path).endswith(expected)

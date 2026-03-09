import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set

import scrapy
from w3lib.html import remove_tags

from extracting.config_loader import get_config_loader
from extracting.csv_utils import append_row, get_output_csv_for_source
from extracting.spider_settings import ETHICAL_SCRAPING_SETTINGS


ARTICLE_URL_RE = re.compile(r"^https?://(?:www\.)?idnes\.cz/zpravy/.+\.A\d+_[^/?#]+", re.IGNORECASE)


class IDNESArchiveSpider(scrapy.Spider):
    name = "idnes_archive"
    SOURCE_KEY = "idnes_archive_sekty"

    custom_settings = {
        **ETHICAL_SCRAPING_SETTINGS,
        "ROBOTSTXT_OBEY": False,
        "COOKIES_ENABLED": True,
        "DOWNLOAD_DELAY": 2.5,
        "LOG_LEVEL": "INFO",
        "RETRY_TIMES": 4,
        "DOWNLOAD_TIMEOUT": 30,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_loader = get_config_loader()
        self.source_config = self.config_loader.get_source(self.SOURCE_KEY) or {}
        self.source_name = self.source_config.get("name", "iDNES.cz Archiv - Sekty, kulty, mesiáši")
        self.archive_url = self.source_config.get(
            "url",
            "https://www.idnes.cz/zpravy/archiv/sekty-kulty-mesiasi.K64268",
        )
        self.output_path = get_output_csv_for_source(self.SOURCE_KEY)
        self.max_pages = int(kwargs.get("max_pages", 0) or 0)
        self.dcmp_cookie = os.getenv("IDNES_DCMP_COOKIE", "google=1&mafra=1111&gemius=1")
        self.seen_urls: Set[str] = set()
        self.enabled = bool(self.source_config.get("enabled", True))

        Path("export/csv").mkdir(parents=True, exist_ok=True)
        self.logger.info(f"📰 Initializing iDNES archive spider (enabled={self.enabled})")

    def start_requests(self):
        if not self.enabled:
            self.logger.info("⏭️ iDNES archive source is disabled in sources_config.yaml")
            return

        yield scrapy.Request(
            url=self.archive_url,
            callback=self.parse_archive,
            cookies={"dCMP": self.dcmp_cookie},
            meta={"page_number": 1},
            dont_filter=True,
            errback=self.handle_error,
        )

    def parse_archive(self, response):
        cards = response.css("div.col-a > div.art")
        if not cards and response.css("a.contentwall_login"):
            self.logger.warning(
                "⚠️ iDNES page returned consent wall. Set IDNES_DCMP_COOKIE env var if needed."
            )
            return

        new_articles = 0
        for card in cards:
            href = card.css("a.art-link::attr(href)").get()
            if not href:
                continue

            url = response.urljoin(href)
            if not self._is_article_url(url):
                continue
            if url in self.seen_urls:
                continue

            self.seen_urls.add(url)
            new_articles += 1

            preview_title = (card.css("a.art-link h3::text").get() or "").strip()
            preview_summary = (card.css("p::text").get() or "").strip()
            preview_published = (card.css("span.time::attr(datetime)").get() or "").strip()

            yield scrapy.Request(
                url=url,
                callback=self.parse_article,
                cookies={"dCMP": self.dcmp_cookie},
                meta={
                    "preview_title": preview_title,
                    "preview_summary": preview_summary,
                    "preview_published": preview_published,
                },
                errback=self.handle_error,
            )

        page_number = int(response.meta.get("page_number", 1))
        self.logger.info(f"📄 Archive page {page_number}: queued {new_articles} articles")

        next_page = self._get_next_page_url(response)
        if next_page and (self.max_pages <= 0 or page_number < self.max_pages):
            yield scrapy.Request(
                url=next_page,
                callback=self.parse_archive,
                cookies={"dCMP": self.dcmp_cookie},
                meta={"page_number": page_number + 1},
                dont_filter=True,
                errback=self.handle_error,
            )

    def parse_article(self, response):
        title = self._extract_title(response, response.meta.get("preview_title", ""))
        opener = self._clean_text(response.css("div.opener[itemprop='description']::text").getall())
        body_nodes = response.css("div#art-text ::text, [itemprop='articleBody'] ::text").getall()
        body_text = self._clean_body(body_nodes)

        if self._looks_paywalled(body_text):
            body_text = ""

        if not body_text and opener:
            body_text = opener

        preview_summary = (response.meta.get("preview_summary") or "").strip()
        if len(body_text) < 80 and preview_summary:
            body_text = f"{opener} {preview_summary}".strip() if opener else preview_summary

        if len(body_text) < 40:
            return

        author = self._extract_author(response)
        published_at = (
            response.css("span.time-date::attr(content)").get()
            or response.xpath("//meta[@property='article:published_time']/@content").get()
            or response.meta.get("preview_published", "")
        )
        categories = (
            response.xpath("//meta[@name='keywords']/@content").get()
            or "sekty,kulty,mesiáši"
        )

        item = {
            "source_name": self.source_name,
            "source_type": "Web",
            "title": title,
            "url": response.url,
            "text": body_text,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "author": author,
            "published_at": published_at,
            "categories": categories,
        }

        append_row(self.output_path, item)
        yield item

    def _extract_title(self, response, fallback: str = "") -> str:
        title = (
            response.css("h1.arttit::text").get()
            or response.css("h1::text").get()
            or response.xpath("//meta[@property='og:title']/@content").get()
            or response.css("title::text").get()
            or fallback
            or ""
        )
        title = title.replace(" - iDNES.cz", "").strip()
        return title

    def _extract_author(self, response) -> str:
        author = (
            response.css(".authors a.name span[itemprop='name']::text").get()
            or response.css(".authors a.name span[itemprop='additionalName']::text").get()
            or response.css(".authors a.name::text").get()
            or response.xpath("//meta[@name='author']/@content").get()
            or "Unknown"
        )
        return remove_tags(str(author)).strip() or "Unknown"

    def _clean_text(self, values) -> str:
        parts = [remove_tags(str(value)).replace("\xa0", " ").strip() for value in values]
        parts = [part for part in parts if part]
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    def _clean_body(self, values) -> str:
        drop_fragments = {
            "Dočtěte tento exkluzivní článek",
            "s předplatným iDNES Premium",
            "Měsíční",
            "Roční",
            "Dvouleté",
            "Předplatit",
            "Ušetříte",
            "NEJOBLÍBENĚJŠÍ",
        }

        parts = []
        for raw in values:
            text = remove_tags(str(raw)).replace("\xa0", " ").strip()
            if not text:
                continue
            if any(fragment in text for fragment in drop_fragments):
                continue
            parts.append(text)

        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    def _looks_paywalled(self, text: str) -> bool:
        if not text:
            return True
        markers = [
            "Dočtěte tento exkluzivní článek",
            "s předplatným iDNES Premium",
            "Předplatit",
        ]
        return sum(1 for marker in markers if marker in text) >= 2

    def _is_article_url(self, url: str) -> bool:
        if not ARTICLE_URL_RE.match(url):
            return False
        if "/diskuse" in url:
            return False
        return True

    def _get_next_page_url(self, response) -> Optional[str]:
        candidates = response.css(
            "#navbox a[title='další']::attr(href), #navbox .nav-n4 a.ico-right::attr(href), #navbox .nav-n4 a::attr(href)"
        ).getall()

        for href in candidates:
            next_url = response.urljoin(href)
            if "sekty-kulty-mesiasi.K64268" in next_url and next_url != response.url:
                return next_url
        return None

    def handle_error(self, failure):
        request = failure.request
        self.logger.error(f"❌ iDNES request failed for {request.url}: {failure.value}")

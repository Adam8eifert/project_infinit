# 📁 extracting/configured_collectors.py
# Deterministic, config-driven collectors for sitemap, API and Wayback sources.

import json
import logging
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from extracting.config_loader import get_config_loader
from extracting.csv_utils import append_row, get_output_csv_for_source

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """Lightweight HTML text extractor for deterministic content capture."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip = False
        self.parts: List[str] = []
        self.title_parts: List[str] = []
        self._inside_title = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip = True
        if tag == "title":
            self._inside_title = True

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self._skip = False
        if tag == "title":
            self._inside_title = False

    def handle_data(self, data):
        if self._inside_title:
            self.title_parts.append(data)
        elif not self._skip and data.strip():
            self.parts.append(data)

    def get_text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()

    def get_title(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.title_parts)).strip()


class ConfiguredSourceCollector:
    """Collect content from configured sitemap/API/Wayback sources."""

    def __init__(self, config_loader=None):
        self.config_loader = config_loader or get_config_loader()
        self.user_agent = "ProjectInfinit/1.0 (+https://example.org)"

    def collect_all(self) -> Dict[str, int]:
        """Run all enabled config-driven acquisition sources."""
        summary: Dict[str, int] = {}
        for method in ("sitemap", "api", "wayback"):
            sources = self.config_loader.get_sources_by_acquisition(method)
            for source_key, source_config in sources.items():
                if not source_config.get("enabled", False):
                    continue
                logger.info("Collecting %s via %s", source_config.get("name", source_key), method)
                try:
                    count = self.collect_source(source_key, source_config)
                except Exception as exc:
                    logger.warning("Failed to collect %s: %s", source_key, exc)
                    count = 0
                summary[source_key] = count
        return summary

    def collect_source(self, source_key: str, source_config: Dict[str, Any]) -> int:
        method = self._get_method(source_config)
        if method == "sitemap":
            return self._collect_sitemap_source(source_key, source_config)
        if method == "api":
            return self._collect_api_source(source_key, source_config)
        if method == "wayback":
            return self._collect_wayback_source(source_key, source_config)
        raise ValueError(f"Unsupported acquisition method: {method}")

    def _get_method(self, source_config: Dict[str, Any]) -> str:
        acquisition = source_config.get("acquisition") or {}
        method = str(acquisition.get("method", "")).strip().lower()
        if method:
            return method
        source_type = str(source_config.get("type", "")).strip().lower()
        if source_type in {"sitemap", "api", "wayback"}:
            return source_type
        return ""

    def _collect_sitemap_source(self, source_key: str, source_config: Dict[str, Any]) -> int:
        acquisition = source_config.get("acquisition") or {}
        sitemap_url = str(acquisition.get("url") or source_config.get("url") or "").strip()
        if not sitemap_url:
            raise ValueError(f"No sitemap URL configured for {source_key}")

        urls = self._collect_sitemap_urls(sitemap_url)
        include_patterns = acquisition.get("include_patterns", []) or []
        if include_patterns:
            urls = [url for url in urls if any(re.search(pattern, url) for pattern in include_patterns)]

        written = 0
        seen_urls = set()
        for url in urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            try:
                page_html = self._fetch_text(url)
            except Exception as exc:
                logger.warning("Could not fetch %s for %s: %s", url, source_key, exc)
                continue
            title = self._extract_title(page_html)
            text = self._extract_text(page_html)
            item = {
                "source_name": source_config.get("name", source_key),
                "source_type": source_config.get("type", "sitemap"),
                "title": title or Path(url).name,
                "url": url,
                "text": text,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "author": "",
                "published_at": "",
                "categories": [],
            }
            append_row(get_output_csv_for_source(source_key), item)
            written += 1
        return written

    def _collect_api_source(self, source_key: str, source_config: Dict[str, Any]) -> int:
        acquisition = source_config.get("acquisition") or {}
        endpoint = str(acquisition.get("url") or source_config.get("url") or "").strip()
        if not endpoint:
            raise ValueError(f"No API endpoint configured for {source_key}")

        params = acquisition.get("params") or {}
        payload = self._fetch_json(endpoint, params=params)
        items = self._extract_api_items(payload, response_path=acquisition.get("response_path"))

        written = 0
        for item in items:
            title = self._coerce_text(item.get("title") or item.get("name") or item.get("headline") or "")
            url = self._coerce_text(item.get("url") or item.get("link") or item.get("permalink") or "")
            text = self._coerce_text(item.get("content") or item.get("description") or item.get("text") or item.get("snippet") or "")
            if not title and not text and not url:
                continue
            row = {
                "source_name": source_config.get("name", source_key),
                "source_type": source_config.get("type", "api"),
                "title": title or (url or source_key),
                "url": url,
                "text": text,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "author": self._coerce_text(item.get("author") or ""),
                "published_at": self._coerce_text(item.get("published") or item.get("date") or ""),
                "categories": item.get("categories") or [],
            }
            append_row(get_output_csv_for_source(source_key), row)
            written += 1
        return written

    def _collect_wayback_source(self, source_key: str, source_config: Dict[str, Any]) -> int:
        acquisition = source_config.get("acquisition") or {}
        target_url = str(acquisition.get("url") or source_config.get("url") or "").strip()
        if not target_url:
            raise ValueError(f"No target URL configured for {source_key}")

        start_year = int(acquisition.get("start_year") or 2000)
        end_year = int(acquisition.get("end_year") or datetime.now(timezone.utc).year)
        limit = int(acquisition.get("limit") or 10)
        written = 0
        seen = set()
        for year in range(start_year, end_year + 1):
            if written >= limit:
                break
            timestamp = f"{year}0101000000"
            availability_url = f"https://archive.org/wayback/available?url={target_url}&timestamp={timestamp}"
            data = self._fetch_json(availability_url)
            snapshot = data.get("archived_snapshots", {}).get("closest") if isinstance(data, dict) else None
            if not isinstance(snapshot, dict):
                continue
            snapshot_url = snapshot.get("url")
            if not snapshot_url or snapshot_url in seen:
                continue
            seen.add(snapshot_url)
            row = {
                "source_name": source_config.get("name", source_key),
                "source_type": source_config.get("type", "wayback"),
                "title": f"Wayback snapshot {year}",
                "url": snapshot_url,
                "text": f"Archived snapshot from {year} for {target_url}",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "author": "",
                "published_at": str(year),
                "categories": [],
            }
            append_row(get_output_csv_for_source(source_key), row)
            written += 1
        return written

    def _extract_api_items(self, payload: Any, response_path: Optional[str] = None) -> List[Dict[str, Any]]:
        if response_path:
            node = self._resolve_response_path(payload, response_path)
            if isinstance(node, list):
                return [self._normalize_api_item(item) for item in node if isinstance(item, dict)]
            if isinstance(node, dict):
                return [self._normalize_api_item(node)]
            return []

        if isinstance(payload, list):
            return [self._normalize_api_item(item) for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("items", "results", "data", "entries"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [self._normalize_api_item(item) for item in value if isinstance(item, dict)]
            return [self._normalize_api_item(payload)]
        return []

    def _normalize_api_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(item)
        if "content" not in normalized:
            normalized["content"] = (
                normalized.get("snippet")
                or normalized.get("description")
                or normalized.get("text")
                or ""
            )
        return normalized

    def _resolve_response_path(self, payload: Any, response_path: str) -> Any:
        current = payload
        for part in [segment for segment in response_path.split('.') if segment]:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                except ValueError:
                    return None
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            else:
                return None
        return current

    def _collect_sitemap_urls(self, sitemap_url: str, seen: Optional[set] = None) -> List[str]:
        if seen is None:
            seen = set()
        if sitemap_url in seen:
            return []
        seen.add(sitemap_url)

        try:
            xml_payload = self._fetch_text(sitemap_url)
        except Exception as exc:
            logger.warning("Could not fetch sitemap %s: %s", sitemap_url, exc)
            return []

        try:
            root = ET.fromstring(xml_payload)
        except ET.ParseError:
            return []

        urls: List[str] = []
        root_tag = self._local_name(root.tag)
        for element in root.iter():
            if self._local_name(element.tag) == "loc" and element.text and element.text.strip():
                loc = element.text.strip()
                if root_tag == "sitemapindex":
                    urls.extend(self._collect_sitemap_urls(loc, seen))
                else:
                    urls.append(loc)
        return urls

    def _parse_sitemap_urls(self, xml_payload: str) -> List[str]:
        try:
            root = ET.fromstring(xml_payload)
        except ET.ParseError:
            return []

        urls = []
        for element in root.iter():
            if self._local_name(element.tag) == "loc" and element.text and element.text.strip():
                urls.append(element.text.strip())
        return urls

    def _local_name(self, tag: str) -> str:
        return tag.split("}", 1)[-1] if isinstance(tag, str) else ""

    def _fetch_json(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 15) -> Dict[str, Any]:
        final_url = url
        if params:
            final_url = f"{url}?{urlencode(params)}" if "?" not in url else f"{url}&{urlencode(params)}"
        text = self._fetch_text(final_url, timeout=timeout)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _fetch_text(self, url: str, timeout: int = 15) -> str:
        request = Request(url, headers={"User-Agent": self.user_agent})
        with urlopen(request, timeout=timeout) as response:
            content = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return content.decode(charset, errors="ignore")

    def _extract_title(self, html: str) -> str:
        parser = HTMLTextExtractor()
        parser.feed(html)
        return parser.get_title() or parser.get_text()[:120]

    def _extract_text(self, html: str) -> str:
        parser = HTMLTextExtractor()
        parser.feed(html)
        return parser.get_text()

    def _coerce_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return str(value)


def run_configured_collectors() -> Dict[str, int]:
    """Entry point used by the pipeline and the CLI."""
    collector = ConfiguredSourceCollector()
    summary = collector.collect_all()
    logger.info("Configured collectors completed: %s", summary)
    return summary


if __name__ == "__main__":
    run_configured_collectors()

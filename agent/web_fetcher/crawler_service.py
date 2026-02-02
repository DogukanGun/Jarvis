"""Crawler service for the web_fetcher API. Uses Crawlee PlaywrightCrawler with in-memory storage per request."""

from __future__ import annotations

import asyncio
from typing import Any

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from crawlee.storage_clients import MemoryStorageClient

# Limits
MAX_PAGES_GLOBAL_CAP = 500
DEFAULT_MAX_PAGES_DISCOVERY = 200
DEFAULT_MAX_PAGES_CONTENTS = 50
DEFAULT_MAX_CHARS_PER_PAGE = 50_000


def _truncate(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "... [truncated]"


async def fetch_page(url: str, *, max_chars: int = DEFAULT_MAX_CHARS_PER_PAGE) -> dict[str, Any]:
    """Fetch a single page and return url, title, and main text content."""
    storage_client = MemoryStorageClient()
    result: dict[str, Any] = {"url": url, "title": "", "content": ""}

    crawler = PlaywrightCrawler(
        storage_client=storage_client,
        headless=True,
        max_requests_per_crawl=1,
        max_request_retries=2,
    )

    @crawler.router.default_handler
    async def handler(context: PlaywrightCrawlingContext) -> None:
        result["url"] = context.request.url
        result["title"] = await context.page.title() or ""
        raw = await context.page.evaluate("() => document.body?.innerText ?? ''")
        result["content"] = _truncate(str(raw or ""), max_chars)

    await crawler.run([url])
    return result


async def list_site_pages(
    url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES_DISCOVERY,
    same_domain_only: bool = True,
) -> list[str]:
    """Discover all page URLs reachable from the seed URL. Returns list of URLs only."""
    max_pages = min(max_pages, MAX_PAGES_GLOBAL_CAP)
    storage_client = MemoryStorageClient()
    visited: list[str] = []

    crawler = PlaywrightCrawler(
        storage_client=storage_client,
        headless=True,
        max_requests_per_crawl=max_pages,
        max_request_retries=2,
    )

    @crawler.router.default_handler
    async def handler(context: PlaywrightCrawlingContext) -> None:
        visited.append(context.request.url)
        strategy = "same-domain" if same_domain_only else "all"
        await context.enqueue_links(strategy=strategy)

    await crawler.run([url])
    return visited


async def fetch_site_contents(
    url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES_CONTENTS,
    max_chars_per_page: int = DEFAULT_MAX_CHARS_PER_PAGE,
    same_domain_only: bool = True,
) -> list[dict[str, Any]]:
    """Crawl the site from the seed URL and return url, title, content for each page."""
    max_pages = min(max_pages, MAX_PAGES_GLOBAL_CAP)
    storage_client = MemoryStorageClient()

    crawler = PlaywrightCrawler(
        storage_client=storage_client,
        headless=True,
        max_requests_per_crawl=max_pages,
        max_request_retries=2,
    )

    @crawler.router.default_handler
    async def handler(context: PlaywrightCrawlingContext) -> None:
        title = await context.page.title() or ""
        raw = await context.page.evaluate("() => document.body?.innerText ?? ''")
        content = _truncate(str(raw or ""), max_chars_per_page)
        await context.push_data(
            {"url": context.request.url, "title": title, "content": content}
        )
        strategy = "same-domain" if same_domain_only else "all"
        await context.enqueue_links(strategy=strategy)

    await crawler.run([url])
    data = await crawler.get_data()
    return list(data.items)

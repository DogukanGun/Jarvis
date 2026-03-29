"""Crawler service for the web_fetcher API. Uses Playwright directly (no Crawlee)."""

from __future__ import annotations

from collections import deque
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

# Limits
MAX_PAGES_GLOBAL_CAP = 500
DEFAULT_MAX_PAGES_DISCOVERY = 200
DEFAULT_MAX_PAGES_CONTENTS = 50
DEFAULT_MAX_CHARS_PER_PAGE = 50_000


def _truncate(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "... [truncated]"


def _same_domain(base: str, link: str) -> bool:
    try:
        return urlparse(base).netloc == urlparse(link).netloc
    except Exception:
        return False


async def fetch_page(url: str, *, max_chars: int = DEFAULT_MAX_CHARS_PER_PAGE) -> dict[str, Any]:
    """Fetch a single page and return url, title, and main text content."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            final_url = page.url
            title = await page.title() or ""
            raw = await page.evaluate("() => document.body?.innerText ?? ''")
            content = _truncate(str(raw or ""), max_chars)
            return {"url": final_url, "title": title, "content": content}
        finally:
            await browser.close()


async def list_site_pages(
    url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES_DISCOVERY,
    same_domain_only: bool = True,
) -> list[str]:
    """Discover all page URLs reachable from the seed URL. Returns list of URLs only."""
    max_pages = min(max_pages, MAX_PAGES_GLOBAL_CAP)
    visited: list[str] = []
    seen: set[str] = set()
    queue: deque[str] = deque([url])
    seen.add(url)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            while queue and len(visited) < max_pages:
                current = queue.popleft()
                try:
                    page = await browser.new_page()
                    await page.goto(current, wait_until="domcontentloaded", timeout=20000)
                    visited.append(page.url)
                    # Collect links
                    hrefs = await page.eval_on_selector_all(
                        "a[href]", "els => els.map(e => e.href)"
                    )
                    await page.close()
                    for href in hrefs:
                        resolved = urljoin(current, href).split("#")[0]
                        if resolved not in seen:
                            if not same_domain_only or _same_domain(url, resolved):
                                seen.add(resolved)
                                queue.append(resolved)
                except Exception:
                    pass
        finally:
            await browser.close()

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
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    queue: deque[str] = deque([url])
    seen.add(url)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            while queue and len(results) < max_pages:
                current = queue.popleft()
                try:
                    page = await browser.new_page()
                    await page.goto(current, wait_until="domcontentloaded", timeout=20000)
                    final_url = page.url
                    title = await page.title() or ""
                    raw = await page.evaluate("() => document.body?.innerText ?? ''")
                    content = _truncate(str(raw or ""), max_chars_per_page)
                    results.append({"url": final_url, "title": title, "content": content})
                    hrefs = await page.eval_on_selector_all(
                        "a[href]", "els => els.map(e => e.href)"
                    )
                    await page.close()
                    for href in hrefs:
                        resolved = urljoin(current, href).split("#")[0]
                        if resolved not in seen:
                            if not same_domain_only or _same_domain(url, resolved):
                                seen.add(resolved)
                                queue.append(resolved)
                except Exception:
                    pass
        finally:
            await browser.close()

    return results

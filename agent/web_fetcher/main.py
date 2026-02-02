"""
Web Fetcher API for AI agent tools.

Run via Docker (installs requirements + playwright chromium in image):
  docker build -t web_fetcher .
  docker run -p 8000:8000 web_fetcher

Endpoints:
  POST /page          - Fetch one page's content (url, title, content)
  POST /site/pages    - List all page URLs reachable from a seed URL
  POST /site/contents - Fetch url, title, content for each page of a site
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from crawler_service import (
    fetch_page as svc_fetch_page,
    fetch_site_contents,
    list_site_pages,
)


# --- Request / Response models ---


class PageRequest(BaseModel):
    """Request body for POST /page."""

    url: HttpUrl
    max_chars: int | None = Field(default=50_000, ge=100, le=500_000)


class PageResponse(BaseModel):
    """Response for POST /page."""

    url: str
    title: str
    content: str


class SitePagesRequest(BaseModel):
    """Request body for POST /site/pages."""

    url: HttpUrl
    max_pages: int | None = Field(default=200, ge=1, le=500)
    same_domain_only: bool = True


class SitePagesResponse(BaseModel):
    """Response for POST /site/pages."""

    urls: list[str]


class SiteContentsRequest(BaseModel):
    """Request body for POST /site/contents."""

    url: HttpUrl
    max_pages: int | None = Field(default=50, ge=1, le=500)
    max_chars_per_page: int | None = Field(default=50_000, ge=100, le=500_000)
    same_domain_only: bool = True


class PageItem(BaseModel):
    """One page in POST /site/contents response."""

    url: str
    title: str
    content: str


class SiteContentsResponse(BaseModel):
    """Response for POST /site/contents."""

    pages: list[PageItem]


# --- App and routes ---

app = FastAPI(
    title="Web Fetcher API",
    description="Fetch page contents and discover site URLs for AI agent tools.",
    version="0.1.0",
)


@app.get("/")
def root() -> dict[str, str]:
    """Liveness/readiness."""
    return {"status": "ok", "service": "web_fetcher"}


@app.get("/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "healthy"}


def _err_detail(e: Exception) -> str:
    s = str(e).strip()
    return s if s else f"{type(e).__name__}"


@app.post("/page", response_model=PageResponse)
async def page(body: PageRequest) -> PageResponse:
    """Fetch one page: returns url, title, and main text content."""
    max_chars = body.max_chars or 50_000
    try:
        out = await svc_fetch_page(str(body.url), max_chars=max_chars)
        return PageResponse(url=out["url"], title=out["title"], content=out["content"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=_err_detail(e)) from e


@app.post("/site/pages", response_model=SitePagesResponse)
async def site_pages(body: SitePagesRequest) -> SitePagesResponse:
    """List all page URLs reachable from the seed URL (discovery only)."""
    try:
        urls = await list_site_pages(
            str(body.url),
            max_pages=body.max_pages or 200,
            same_domain_only=body.same_domain_only,
        )
        return SitePagesResponse(urls=urls)
    except Exception as e:
        raise HTTPException(status_code=500, detail=_err_detail(e)) from e


@app.post("/site/contents", response_model=SiteContentsResponse)
async def site_contents(body: SiteContentsRequest) -> SiteContentsResponse:
    """Fetch url, title, and content for each page of the site."""
    try:
        items = await fetch_site_contents(
            str(body.url),
            max_pages=body.max_pages or 50,
            max_chars_per_page=body.max_chars_per_page or 50_000,
            same_domain_only=body.same_domain_only,
        )
        pages = [
            PageItem(url=it["url"], title=it["title"], content=it["content"])
            for it in items
        ]
        return SiteContentsResponse(pages=pages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=_err_detail(e)) from e

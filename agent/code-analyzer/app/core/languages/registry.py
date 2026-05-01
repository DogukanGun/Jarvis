"""Registry mapping file extensions to language providers.

Providers are loaded lazily so missing tree-sitter packages don't crash startup.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from .base import LanguageProvider

logger = logging.getLogger(__name__)

_PROVIDER_CACHE: Dict[str, Optional[LanguageProvider]] = {}


def _try_load_python() -> Optional[LanguageProvider]:
    try:
        from .python_lang import PythonProvider
        return PythonProvider()
    except Exception as e:
        logger.debug("Python tree-sitter unavailable: %s", e)
        return None


def _try_load_typescript() -> Optional[LanguageProvider]:
    try:
        from .typescript_lang import TypeScriptProvider
        return TypeScriptProvider(tsx=False)
    except Exception as e:
        logger.debug("TypeScript tree-sitter unavailable: %s", e)
        return None


def _try_load_javascript() -> Optional[LanguageProvider]:
    try:
        from .typescript_lang import JavaScriptProvider
        return JavaScriptProvider()
    except Exception as e:
        logger.debug("JavaScript tree-sitter unavailable: %s", e)
        return None


def _try_load_go() -> Optional[LanguageProvider]:
    try:
        from .go_lang import GoProvider
        return GoProvider()
    except Exception as e:
        logger.debug("Go tree-sitter unavailable: %s", e)
        return None


_LOADERS = {
    ".py": _try_load_python,
    ".ts": _try_load_typescript,
    ".tsx": _try_load_typescript,
    ".js": _try_load_javascript,
    ".jsx": _try_load_javascript,
    ".mjs": _try_load_javascript,
    ".cjs": _try_load_javascript,
    ".go": _try_load_go,
}


def get_provider(file_path: str | Path) -> Optional[LanguageProvider]:
    ext = Path(file_path).suffix.lower()
    if ext not in _LOADERS:
        return None
    if ext not in _PROVIDER_CACHE:
        _PROVIDER_CACHE[ext] = _LOADERS[ext]()
    return _PROVIDER_CACHE[ext]


def supported_extensions() -> list[str]:
    return list(_LOADERS.keys())

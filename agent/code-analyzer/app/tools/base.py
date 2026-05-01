from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    code = "code"


class AuthLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

    _order_map: dict  # type: ignore[assignment]

    @staticmethod
    def _rank(level: AuthLevel) -> int:
        return {"low": 0, "medium": 1, "high": 2, "critical": 3}[level.value]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, AuthLevel):
            return NotImplemented
        return self._rank(self) < self._rank(other)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, AuthLevel):
            return NotImplemented
        return self._rank(self) <= self._rank(other)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, AuthLevel):
            return NotImplemented
        return self._rank(self) > self._rank(other)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, AuthLevel):
            return NotImplemented
        return self._rank(self) >= self._rank(other)


class ToolParameter(BaseModel):
    name: str
    type: str = Field(..., description="Parameter type: string, integer, boolean, or file_path")
    required: bool = True
    default: Optional[Any] = None
    description: str = ""
    choices: Optional[List[str]] = None


class ToolMetadata(BaseModel):
    name: str
    display_name: str
    category: ToolCategory
    description: str
    capabilities: List[str]
    auth_level: AuthLevel
    parameters: List[ToolParameter]
    binary_path: Optional[str] = None
    is_long_running: bool = False
    estimated_duration: str = "seconds"
    output_format: str = "text"


class ToolResult(BaseModel):
    tool_name: str = ""
    success: bool
    exit_code: Optional[int] = None
    raw_output: str = ""
    structured_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0
    warnings: List[str] = Field(default_factory=list)


class BaseTool(ABC):
    @abstractmethod
    def metadata(self) -> ToolMetadata: ...

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolResult: ...

    @abstractmethod
    def parse_output(self, raw: str) -> Dict[str, Any]: ...

    def check_available(self) -> bool:
        binary = self.metadata().binary_path
        if binary is None:
            return True
        return shutil.which(binary) is not None

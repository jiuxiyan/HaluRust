"""Global configuration for HaluRust."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class HaluRustConfig:
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str | None = None
    max_iterations: int = 5
    temperature: float = 0.3
    workspace_dir: Path = field(default_factory=lambda: Path("/tmp/halurust_workspace"))
    miri_timeout: int = 120

    def validate(self) -> None:
        if not self.api_key:
            raise ValueError("API key is required. Set OPENAI_API_KEY env var or pass api_key.")

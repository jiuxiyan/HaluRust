"""Global configuration for HaluRust."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class HaluRustConfig:
    # --- LLM settings ---
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str | None = None
    temperature: float = 0.3

    # --- Iteration limits ---
    max_iterations: int = 5
    compile_fix_retries: int = 2  # inner loop: cargo check retry limit

    # --- Multi-candidate (beam search) ---
    num_candidates: int = 3
    candidate_temperatures: list[float] = field(
        default_factory=lambda: [0.2, 0.5, 0.8]
    )

    # --- Critic scoring ---
    score_threshold: float = 0.4  # below this → SCORE_DROPPED
    score_weights: dict[str, float] = field(
        default_factory=lambda: {
            "static": 0.2,
            "semantic": 0.4,
            "minimal_change": 0.4,
        }
    )

    # --- Feature toggles ---
    enable_clippy: bool = True
    enable_semantic_check: bool = True
    enable_reflection: bool = True
    enable_hallucination: bool = True
    enable_test_generation: bool = False  # opt-in: auto-generate tests
    enable_experience_accumulation: bool = True

    # --- Paths & timeouts ---
    workspace_dir: Path = field(default_factory=lambda: Path("/tmp/halurust_workspace"))
    miri_timeout: int = 120
    clippy_timeout: int = 60
    compile_timeout: int = 60

    def validate(self) -> None:
        if not self.api_key:
            raise ValueError("API key is required. Set OPENAI_API_KEY env var or pass api_key.")
        if len(self.candidate_temperatures) < self.num_candidates:
            temps = self.candidate_temperatures
            while len(temps) < self.num_candidates:
                temps.append(0.5)
            self.candidate_temperatures = temps

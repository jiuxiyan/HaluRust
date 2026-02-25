"""Unified LLM client wrapper."""

from __future__ import annotations

from openai import OpenAI

from .config import HaluRustConfig


class LLMClient:
    def __init__(self, config: HaluRustConfig):
        kwargs = {"api_key": config.api_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self._client = OpenAI(**kwargs)
        self._model = config.model
        self._temperature = config.temperature

    def chat(self, system: str, user: str, temperature: float | None = None) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature or self._temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""

    def chat_with_history(
        self, system: str, messages: list[dict], temperature: float | None = None
    ) -> str:
        full = [{"role": "system", "content": system}] + messages
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature or self._temperature,
            messages=full,
        )
        return resp.choices[0].message.content or ""

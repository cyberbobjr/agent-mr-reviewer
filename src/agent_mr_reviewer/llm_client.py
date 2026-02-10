from __future__ import annotations

from typing import Any, Dict, List
import requests


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        self.session.headers.update({"Content-Type": "application/json"})

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 1500) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        url = f"{self.base_url}/v1/chat/completions"
        response = self.session.post(url, json=payload, timeout=self.timeout)
        if not response.ok:
            raise RuntimeError(
                f"LLM API error {response.status_code}: {response.text}"
            )
        data = response.json()
        return data["choices"][0]["message"]["content"]

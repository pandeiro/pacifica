"""LLM extraction client for wildlife scrapers.

Thin async wrapper around an OpenAI-compatible chat completions API.
Defaults to local Ollama. Falls back to regex heuristics on failure.

See doc/ref/llm_prompts.md for prompt engineering findings.
"""

import json
import os
import re
from typing import Callable

import httpx

PROFILES = {
    "default": {
        "system": "Return only valid JSON.",
        "user_template": 'Extract wildlife sightings. Return JSON with "sightings" array containing objects with "species" (string) and "count" (integer) fields.\n\n{text}',
        "temperature": 0.0,
    },
    "acs-la": {
        "system": "Return only valid JSON.",
        "user_template": 'Extract wildlife sightings from this ACS-LA Gray Whale Census report. Return JSON with "sightings" array. Each object has: "species" (string), "count" (integer), "location_hint" (string, optional), "behavior" (string, optional). Include zero counts if explicitly stated.\n\n{text}',
        "temperature": 0.0,
    },
    "dive-conditions": {
        "system": "Return only valid JSON. Do not nest objects.",
        "user_template": 'Extract from dive report. Find visibility (viz, vis, visibility) and swell/surf heights in feet. Return EXACTLY this JSON format with no nesting: {{"visibility": "number or range like 10-15", "swell": "number or range like 3-5"}}. Use null if not found. Do NOT return nested objects.\n\n{text}',
        "temperature": 0.0,
    },
}


class LLMClient:
    """Async wrapper around OpenAI-compatible chat completions API.

    Connects to Ollama running on the Docker host at host.docker.internal:11434.
    """

    def __init__(self, model: str | None = None):
        self.base_url = "http://host.docker.internal:11434"
        self.model = model or os.getenv("LLM_MODEL", "llama3.2:3b")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "LLMClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def extract(
        self,
        raw_text: str,
        profile: str = "default",
        fallback_fn: Callable[[str], dict] | None = None,
    ) -> dict:
        """Extract structured data from raw text using LLM.

        Args:
            raw_text: The unstructured text to extract from.
            profile: Named extraction profile (must exist in PROFILES).
            fallback_fn: Optional function to call if LLM fails.

        Returns:
            Extracted data as dict, or empty dict on failure
            (calls fallback_fn if provided).

        Raises:
            KeyError: If profile does not exist in PROFILES.

        Note:
            See doc/ref/llm_prompts.md for prompt engineering findings.
            All profiles must be predefined in PROFILES dict.
        """
        if profile not in PROFILES:
            raise KeyError(
                f"Unknown extraction profile: {profile!r}. "
                f"Available profiles: {list(PROFILES.keys())}"
            )

        config = PROFILES[profile]
        client = await self._get_client()

        system = config["system"]
        user = config["user_template"].format(text=raw_text)
        temperature = config.get("temperature", 0.0)

        try:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                },
            )
            response.raise_for_status()
            data = response.json()

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            content = content.strip()

            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
            if json_match:
                content = json_match.group(1).strip()
            elif content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)

            try:
                return json.loads(content.strip())
            except json.JSONDecodeError as e:
                print(f"[LLMClient] JSON parse error (profile={profile}): {e}")
                print(f"[LLMClient] Raw LLM response: {content[:500]}...")
                raise
        except Exception as e:
            print(f"[LLMClient] Extraction failed (profile={profile}): {e}")
            if fallback_fn is not None:
                try:
                    return fallback_fn(raw_text)
                except Exception as fallback_error:
                    print(f"[LLMClient] Fallback also failed: {fallback_error}")
            return {}

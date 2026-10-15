from abc import ABC, abstractmethod
from typing import Dict, Any, List
import requests


class LLMProvider(ABC):
    """Abstract Base Class for LLM Generation Providers."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response text given system instructions and user prompt."""
        pass


class DeterministicMockLLMProvider(LLMProvider):
    """Deterministic Mock LLM for automated testing and offline development."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if "<document_context></document_context>" in user_prompt or "NO_CONTEXT" in user_prompt:
            return "The requested information could not be found in the available documents."

        if "<chunk" in user_prompt:
            import re
            chunks = re.findall(r'<chunk[^>]*>(.*?)</chunk>', user_prompt, re.DOTALL)
            if chunks:
                excerpt = chunks[0].strip().replace("\n", " ")
                excerpt = re.sub(r" +", " ", excerpt)[:400]
                return f"Based on the provided documents:\n\n{excerpt}"

        return "The requested information could not be found in the available documents."


class GoogleGeminiLLMProvider(LLMProvider):
    """Google Gemini LLM generation provider with automatic model fallback."""

    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite", temperature: float = 0.0):
        if not api_key:
            raise ValueError("Google Gemini LLM Provider requires an API key.")
        self.api_key = api_key
        self.model = model.replace("models/", "")
        self.temperature = temperature

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # Candidate models to try in order if the preferred model is experiencing high demand (503) or rate limits (429)
        candidates = [self.model, "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
        seen = set()
        ordered_candidates = [m for m in candidates if not (m in seen or seen.add(m))]

        last_error = None
        for candidate_model in ordered_candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate_model}:generateContent?key={self.api_key}"
            payload = {
                "system_instruction": {
                    "parts": [{"text": system_prompt}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": 2048,
                }
            }
            try:
                response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    try:
                        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    except (KeyError, IndexError):
                        raise RuntimeError(f"Unexpected response structure from Gemini API: {data}")

                # If experiencing high demand (503) or rate limit (429), try next candidate
                if response.status_code in (503, 429):
                    last_error = f"Model {candidate_model} returned {response.status_code}: {response.text}"
                    continue

                # Any other error is likely non-transient
                raise RuntimeError(f"Gemini API error ({response.status_code}): {response.text}")

            except (requests.RequestException, RuntimeError) as e:
                last_error = str(e)
                continue

        raise RuntimeError(f"All Gemini model candidates failed. Last error: {last_error}")


class OpenAILLMProvider(LLMProvider):
    """OpenAI LLM generation provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.0):
        if not api_key:
            raise ValueError("OpenAI LLM Provider requires an API key.")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"OpenAI API error ({response.status_code}): {response.text}")

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected response structure from OpenAI API: {data}")


def get_llm_provider(provider_name: str, api_key: str = "", model_name: str = "", temperature: float = 0.0) -> LLMProvider:
    """Factory creating configured LLM provider."""
    provider = (provider_name or "mock").lower()
    if provider == "gemini":
        if not api_key:
            raise ValueError("LLM_PROVIDER is 'gemini' but LLM_API_KEY is not set.")
        return GoogleGeminiLLMProvider(api_key=api_key, model=model_name or "gemini-1.5-flash", temperature=temperature)
    elif provider == "openai":
        if not api_key:
            raise ValueError("LLM_PROVIDER is 'openai' but LLM_API_KEY is not set.")
        return OpenAILLMProvider(api_key=api_key, model=model_name or "gpt-4o-mini", temperature=temperature)
    elif provider in ("mock", "test"):
        return DeterministicMockLLMProvider()
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER '{provider_name}'. Supported: gemini, openai, mock.")

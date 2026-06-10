import httpx
from ..config import settings


class LMStudioClient:
    """Client to communicate with LM Studio API."""

    def __init__(self):
        self.base_url = settings.lm_studio_url
        self.timeout = 60.0

    async def check_connection(self) -> dict:
        """Check if LM Studio is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/models")
                if response.status_code == 200:
                    return {"connected": True, "models": response.json()}
                return {"connected": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    async def generate_completion(self, prompt: str, max_tokens: int = 1024) -> str:
        """Generate a text completion using LM Studio."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"LM Studio generation failed: {e}")

    async def list_models(self) -> list:
        """List available models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/models")
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
        except Exception as e:
            return []


lm_studio_client = LMStudioClient()

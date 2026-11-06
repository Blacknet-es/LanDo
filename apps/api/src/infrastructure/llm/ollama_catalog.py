import httpx

from src.application.settings.list_ollama_models import (
    OllamaCatalogInvalidResponse,
    OllamaCatalogUnavailable,
    OllamaModel,
)


class HttpxOllamaModelCatalog:
    async def list_models(self, base_url: str) -> list[OllamaModel]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/api/tags")
        except httpx.RequestError as exc:
            raise OllamaCatalogUnavailable(
                f"Unable to reach local Ollama at {base_url}: {exc}"
            ) from exc

        if response.status_code != 200:
            raise OllamaCatalogInvalidResponse(
                f"Ollama returned HTTP {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise OllamaCatalogInvalidResponse("Ollama returned invalid JSON") from exc

        models = data.get("models") if isinstance(data, dict) else None
        if not isinstance(models, list):
            raise OllamaCatalogInvalidResponse("Ollama response does not contain a models list")

        result = []
        for item in models:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise OllamaCatalogInvalidResponse("Ollama returned an invalid model entry")
            result.append(
                OllamaModel(
                    name=item["name"],
                    size=item.get("size"),
                    modified_at=item.get("modified_at"),
                )
            )
        return result

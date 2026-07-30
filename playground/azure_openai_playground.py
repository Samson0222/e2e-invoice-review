"""Run the Azure OpenAI surface against a sample prompt and inspect the output.

From the playground folder:

    uv run --project ../backend python azure_openai_playground.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings  # noqa: E402
from app.services.azure_openai_service import AzureOpenAIService  # noqa: E402

SAMPLE_PROMPT = "What is the capital of France?"


def main() -> None:
    service = AzureOpenAIService(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )
    result = service.create_response(SAMPLE_PROMPT)
    print(result.output[0].content[0].text)


if __name__ == "__main__":
    main()

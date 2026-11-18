import argparse

import httpx

from backend.app.config import Settings
from backend.app.services.llm import REQUEST_TIMEOUT, GroqProvider, LlmError

TEST_PROMPT = "請用一句話介紹你自己。"


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test prompt to Groq.")
    parser.add_argument("--model")
    args = parser.parse_args()

    settings = Settings()
    key = settings.groq_api_key
    try:
        with httpx.Client() as client:
            provider = GroqProvider(
                client, key.get_secret_value() if key else "", args.model or settings.groq_model
            )
            reply = provider.complete(
                [{"role": "user", "content": TEST_PROMPT}], [], timeout=REQUEST_TIMEOUT
            )
    except LlmError as exc:
        raise SystemExit(str(exc)) from None

    if not reply.content or not reply.content.strip():
        raise SystemExit("Groq 沒有回傳文字。")
    print(reply.content)


if __name__ == "__main__":
    main()

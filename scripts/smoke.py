"""Быстрая проверка, что приложение отдаёт API и собранный Mini App."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ("/healthz", "/"):
            response = await client.get(path)
            print(path, response.status_code, response.headers.get("content-type"), len(response.content))
            assert response.status_code == 200, path


if __name__ == "__main__":
    asyncio.run(main())

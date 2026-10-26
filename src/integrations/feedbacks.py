from asyncio import Lock

from aiofiles import open

from src.settings import FEEDBACKS


class Feedback:
    _lock = Lock()

    @classmethod
    async def save(cls, text: str) -> None:
        FEEDBACKS.parent.mkdir(parents=True, exist_ok=True)

        async with cls._lock:
            async with open(FEEDBACKS, "a", encoding="utf-8") as file:
                await file.write(f"{text}\n\n")

from contextlib import nullcontext
from contextvars import ContextVar
from time import perf_counter_ns

from aiohttp import ClientResponse, ClientSession
from aiohttp.typedefs import StrOrURL
from aiolimiter import AsyncLimiter
from yarl import URL

from src.settings import logger


class Injection:
    _limiter = ContextVar[AsyncLimiter | None]("_limiter", default=None)

    @classmethod
    def set(cls, limiter: AsyncLimiter | None) -> None:
        cls._limiter.set(limiter)

    @classmethod
    def get(cls) -> AsyncLimiter | None:
        return cls._limiter.get()

    @classmethod
    def reset(cls):
        cls._limiter.set(None)


_request = ClientSession._request


class Limiter:
    _2RPS = {
        "POST /messages",
        "PUT /messages",
        "DELETE /messages",
        "POST /answers",
    }

    NOT_IN = {
        "POST /uploadImage",
        "POST /max/upload.do",
        "POST /max/v2/oauth",
        "POST /v2/chat/completions",
    }

    total = AsyncLimiter(30, 1)

    @staticmethod
    async def request(self, method: str, str_or_url: StrOrURL, **kwargs) -> ClientResponse:
        t1 = t2 = t3 = perf_counter_ns()
        route = f"{method} {URL(str_or_url).path}"
        status = None

        limiter = Injection.get()

        user_limiter = limiter if limiter and route in Limiter._2RPS else nullcontext()
        total_limiter = nullcontext() if route in Limiter.NOT_IN else Limiter.total

        try:
            async with user_limiter:
                t2 = perf_counter_ns()
                async with total_limiter:
                    t3 = perf_counter_ns()
                    response = await _request(self, method, str_or_url, **kwargs)
                    status = response.status
                    return response
        finally:
            t4 = perf_counter_ns()
            logger.info(
                "%s | limiter=%s %s | request=%s | status=%s",
                route,
                (t2 - t1) // 1_000_000,
                (t3 - t2) // 1_000_000,
                (t4 - t3) // 1_000_000,
                status,
            )

    @staticmethod
    def activate() -> None:
        ClientSession._request = Limiter.request

from asyncio import Lock
from collections import deque
from collections.abc import Callable
from typing import Any, Protocol

from aiolimiter import AsyncLimiter
from maxapi.context import MemoryContext

from src.settings import ADMINS


class AnyContext(Protocol):
    @property
    def data(self) -> dict[str, Any]: ...


class Field:
    __slots__ = ("name", "default", "factory")

    def __init__(self, default: Any = None, factory: Callable[[], Any] | None = None) -> None:
        self.default = default
        self.factory = factory

    def __set_name__(self, _, name: str) -> None:
        self.name = name

    def __get__(self, instance: AnyContext | None, _) -> Any:
        if instance is None:
            return self
        if self.name not in instance.data:
            instance.data[self.name] = self.default if self.factory is None else self.factory()
        return instance.data[self.name]

    def __set__(self, instance: AnyContext, value: Any) -> None:
        instance.data[self.name] = value


class Context(MemoryContext):
    full_name = Field()

    branch = Field()
    step = Field(default=0)

    message_id = Field()

    group_id = Field()
    group = Field()

    student_id = Field()
    student = Field()

    test_id = Field()
    test = Field()

    texts = Field(factory=deque)
    options = Field(factory=deque)
    answers = Field(factory=list)

    def __init__(self, chat_id: int | None, user_id: int | None, **kwargs) -> None:
        super().__init__(chat_id, user_id, **kwargs)
        self.lock = Lock()
        self.limiter = AsyncLimiter(2, 1)

    @property
    def data(self) -> dict[str, Any]:
        return self._context

    @property
    def user(self) -> str:
        return f"{self.user_id} {self.full_name}"

    @property
    def is_admin(self) -> bool:
        return self.user_id in ADMINS

    @property
    def state(self) -> str | None:
        return self.branch and f"{self.branch.__name__}{self.step}"

    def next_state(self) -> None:
        self.step += 1
        self._state = self.branch.get_state(self.step)

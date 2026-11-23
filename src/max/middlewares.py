from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from maxapi.enums import ChatType
from maxapi.types import MessageCallback, MessageCreated

from src.max.contexts import Context
from src.max.limiters import Injection
from src.max.states import Admin, User
from src.messages.buttons import Payload
from src.settings import logger


type Branch = type[Admin] | type[User]
type MessageCreatedDecorator = Callable[[MessageCreatedWrapper], MessageCreatedWrapper]
type MessageCreatedWrapper = Callable[[MessageCreated, Context], Awaitable[None]]

type MessageCallbackWrapper = Callable[[MessageCallback, Context, Payload], Awaitable[None]]


@asynccontextmanager
async def transactor(context: Context) -> AsyncGenerator[None, None]:
    context.next_state()
    Injection.set(context.limiter)
    try:
        yield
    except Exception:
        await context.clear()
        raise
    finally:
        Injection.reset()


def branch_lock(branch: Branch) -> MessageCreatedDecorator:
    def decorator(handler: MessageCreatedWrapper) -> MessageCreatedWrapper:
        async def wrapper(event: MessageCreated, context: Context) -> None:
            if event.message.sender is None:
                return None
            if event.message.sender.is_bot:
                return None
            if event.message.recipient.chat_type != ChatType.DIALOG:
                return None

            async with context.lock:
                if context.step:
                    return None

                context.full_name = event.message.sender.full_name
                context.branch = branch

                logger.info("%s | %s", context.user, context.stage)

                async with transactor(context):
                    return await handler(event, context)

        return wrapper

    return decorator


def callback_lock(handler: MessageCallbackWrapper) -> MessageCallbackWrapper:
    async def wrapper(event: MessageCallback, context: Context, payload: Payload) -> None:
        if event.message is None:
            return None

        async with context.lock:
            if payload.step != context.step:
                logger.info("%s | %s | debounce", context.user, context.stage)
                return None

            context.full_name = event.callback.user.full_name

            logger.info("%s | %s", context.user, context.stage)

            async with transactor(context):
                return await handler(event, context, payload)

    return wrapper

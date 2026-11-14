from asyncio import run
from datetime import datetime
from random import choice, randint, sample

from src.constants.statements import UserStatement
from src.constants.texts import GigaChatText, UserText
from src.db.queries.rows import get_rows
from src.integrations.feedbacks import Feedback
from src.integrations.gigachat import GigaChat
from src.max.contexts import Context


async def check_prompt() -> None:
    tests = await get_rows(UserStatement.GET_TESTS)
    test = choice(tests)

    context = Context(None, None)
    context.test = test.name

    tasks = await get_rows(UserStatement.GET_TASKS, test.id)

    answers = [f"{task.id}-{randint(1, 4)}" for task in sample(tasks, 30)]
    points = sum(a.endswith("1") for a in answers)

    mistakes = await get_rows(UserStatement.GET_MISTAKES, answers)

    feedback = await GigaChat.ask(context, mistakes, GigaChatText.PROMPT)

    text = UserText.RESULT.format(
        context.group,
        context.student,
        context.test,
        datetime.now(),
        points,
        feedback,
    )

    await Feedback.save(text)


async def main() -> None:
    try:
        await check_prompt()
    finally:
        await GigaChat.close()


if __name__ == "__main__":
    run(main())

from asyncio import run
from datetime import datetime
from random import choice, randint, sample

from constants.texts import UserText
from integrations.feedbacks import Feedback
from src.constants.statements import UserStatement
from src.db.queries.rows import get_rows
from src.integrations.gigachat import GigaChat


async def check_prompt() -> None:
    tests = await get_rows(UserStatement.GET_TESTS)

    test = choice(tests)

    tasks = await get_rows(UserStatement.GET_TASKS, test.id)

    answers = [f"{task.id}-{randint(1, 4)}" for task in sample(tasks, 30)]

    summary = await get_rows(UserStatement.GET_SUMMARY, answers)

    feedback = await GigaChat.ask("None", summary)

    text = UserText.RESULT.format(
        "None",
        "None",
        test.name,
        datetime.now().strftime("%H:%M %d.%m.%Y"),
        sum(a.endswith("1") for a in answers),
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

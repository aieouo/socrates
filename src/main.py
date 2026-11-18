from asyncio import run
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from multiprocessing import get_context
from os import cpu_count
from random import choice

from maxapi import Bot, Dispatcher
from maxapi.filters.command import Command, CommandStart
from maxapi.types import InputMediaBuffer, MessageCallback, MessageCreated

from src.constants.permutations import PERMUTATIONS
from src.constants.progress_bars import PROGRESS_BARS
from src.constants.statements import AdminStatement, UserStatement
from src.constants.texts import AdminText, CommonText, UserText
from src.db.queries.results import add_result
from src.db.queries.rows import get_rows
from src.integrations.feedbacks import Feedback
from src.integrations.gigachat import GigaChat
from src.max.contexts import Context
from src.max.limiters import Limiter
from src.max.middlewares import branch_lock, callback_lock
from src.max.states import Admin, User
from src.messages.attachments import AttachmentFactory
from src.messages.buttons import Payload
from src.messages.images import ImageFactory
from src.messages.texts import TextFactory
from src.settings import TOKEN, logger


Limiter.activate()
bot = Bot(TOKEN, auto_requests=False, after_input_media_delay=1.0)
dp = Dispatcher(storage=Context)


@dp.message_created(None, Command("admin"))
@branch_lock(Admin)
async def admin_selects_group(event: MessageCreated, context: Context) -> None:
    logger.info("%s | is_admin=%s", context.user, context.is_admin)

    if not context.is_admin:
        return

    groups = await get_rows(AdminStatement.GET_GROUPS)
    attachments = AttachmentFactory.from_rows(context.step, groups)

    message = await event.message.answer(AdminText.SELECT_GROUP, attachments)
    context.message_id = message and message.message.body and message.message.body.mid


@dp.message_callback(Admin.State1, Payload.filter())
@callback_lock
async def admin_selects_test(event: MessageCallback, context: Context, payload: Payload) -> None:
    context.group_id, context.group = payload.index, payload.value

    tests = await get_rows(AdminStatement.GET_TESTS, context.group_id)
    attachments = AttachmentFactory.from_rows(context.step, tests)

    await event.edit(AdminText.SELECT_TEST, attachments)


@dp.message_callback(Admin.State2, Payload.filter())
@callback_lock
async def admin_confirms_selection(event: MessageCallback, context: Context, payload: Payload) -> None:
    context.test_id, context.test = payload.index, payload.value

    text = AdminText.CONFIRM.format(context.group, context.test)

    attachments = AttachmentFactory.for_confirmation(context.step)

    await event.edit(text, attachments)


@dp.message_callback(Admin.State3, Payload.filter())
@callback_lock
async def admin_gets_results(event: MessageCallback, context: Context, payload: Payload) -> None:
    if payload.index:
        await event.edit(CommonText.STOP, [])
        await clear(context)
        return

    await event.delete()

    results = await get_rows(AdminStatement.GET_RESULTS, context.group_id, context.test_id)

    texts = [f"Группа: {context.group}", f"Тест: {context.test}\n"]
    for r in results:
        if r.user_id:
            texts.append(f"{r.name}: {r.points} из 30")
            texts.append(f"{r.user_id} {r.full_name}")
            texts.append(f"{r.finished_at.strftime('%Y-%m-%d %H:%M')}")

            mistakes = " ".join(a for a in r.answers.split() if not a.endswith("1"))
            mistakes = mistakes + "\n" if mistakes else ""
            texts.append(mistakes)
        else:
            texts.append(f"{r.name}\n")

    text = "\n".join(texts)
    attachments = [InputMediaBuffer(text.encode("utf-8-sig"), "results.txt")]

    await event.send(context.group, attachments)

    await clear(context)


@dp.message_created(None, CommandStart())
@branch_lock(User)
async def user_selects_group(event: MessageCreated, context: Context) -> None:
    groups = await get_rows(UserStatement.GET_GROUPS)
    attachments = AttachmentFactory.from_rows(context.step, groups)

    message = await event.message.answer(UserText.SELECT_GROUP, attachments)
    context.message_id = message and message.message.body and message.message.body.mid


@dp.message_callback(User.State1, Payload.filter())
@callback_lock
async def user_selects_student(event: MessageCallback, context: Context, payload: Payload) -> None:
    context.group_id, context.group = payload.index, payload.value

    students = await get_rows(UserStatement.GET_STUDENTS, context.group_id)
    attachments = AttachmentFactory.from_rows(context.step, students)

    await event.edit(UserText.SELECT_STUDENT, attachments)


@dp.message_callback(User.State2, Payload.filter())
@callback_lock
async def user_selects_test(event: MessageCallback, context: Context, payload: Payload) -> None:
    context.student_id, context.student = payload.index, payload.value

    tests = await get_rows(UserStatement.GET_TESTS)
    attachments = AttachmentFactory.from_rows(context.step, tests)

    await event.edit(UserText.SELECT_TEST, attachments)


@dp.message_callback(User.State3, Payload.filter())
@callback_lock
async def user_confirms_selection(event: MessageCallback, context: Context, payload: Payload) -> None:
    context.test_id, context.test = payload.index, payload.value

    text = UserText.CONFIRM.format(context.group, context.student, context.test)

    attachments = AttachmentFactory.for_confirmation(context.step)

    await event.edit(text, attachments)


@dp.message_callback(User.State4, Payload.filter())
@callback_lock
async def user_gets_first_question(event: MessageCallback, context: Context, payload: Payload) -> None:
    if payload.index:
        await event.edit(CommonText.STOP, [])
        await clear(context)
        return

    tasks = await get_rows(UserStatement.GET_TASKS, context.test_id)

    for progress_bar, task in zip(PROGRESS_BARS, tasks):
        order = (task.option1, task.option2, task.option3, task.option4)
        to0from, to1from, to2from, to3from = choice(PERMUTATIONS)
        context.texts.append(
            TextFactory.for_task(
                progress_bar,
                task.question,
                order[to0from],
                order[to1from],
                order[to2from],
                order[to3from],
            )
        )
        context.options.append(
            (
                f"{task.id}-{to0from + 1}",
                f"{task.id}-{to1from + 1}",
                f"{task.id}-{to2from + 1}",
                f"{task.id}-{to3from + 1}",
            )
        )

    text = context.texts.popleft()

    attachments = await AttachmentFactory.for_task(context.step, text)

    await event.edit(CommonText.PLACEHOLDER, attachments)


@dp.message_callback(User.State5, Payload.filter())
@callback_lock
async def user_gets_next_question(event: MessageCallback, context: Context, payload: Payload) -> None:
    await event.edit(CommonText.PROCESSING, [])

    context.answers.append(context.options.popleft()[payload.index])

    if not context.texts:
        finished_at = datetime.now()
        answers = sorted(context.answers, key=lambda a: (len(a), a))
        points = sum(a.endswith("1") for a in answers)

        mistakes = await get_rows(UserStatement.GET_MISTAKES, answers)

        feedback = await GigaChat.ask(context.test, mistakes) if mistakes else ""

        await add_result(
            event.callback.user.user_id,
            event.callback.user.full_name,
            context.group_id,
            context.student_id,
            context.test_id,
            finished_at,
            " ".join(answers),
            points,
        )

        text = UserText.RESULT.format(
            context.group,
            context.student,
            context.test,
            finished_at.strftime("%Y-%m-%d %H:%M"),
            points,
            feedback,
        )

        await event.edit(text, [])

        await Feedback.save(text)

        await clear(context)
        return

    text = context.texts.popleft()

    attachments = await AttachmentFactory.for_task(context.step, text)

    await event.edit(CommonText.PLACEHOLDER, attachments)


@dp.message_created(Command("stop"))
async def stop(_, context: Context) -> None:
    if context.message_id is not None:
        await bot.edit_message(context.message_id, CommonText.STOP, [])

    await clear(context)


async def clear(context: Context) -> None:
    logger.info("%s | %s | clear", context.user, context.state)
    await context.clear()


async def main():
    try:
        with ProcessPoolExecutor(cpu_count(), get_context("fork")) as executor:
            ImageFactory.EXECUTOR = executor
            await dp.start_polling(bot, skip_updates=True)
    finally:
        await GigaChat.close()
        await bot.close_session()


if __name__ == "__main__":
    run(main())

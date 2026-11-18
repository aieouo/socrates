from datetime import datetime
from time import perf_counter_ns

from src.constants.statements import UserStatement
from src.settings import ASYNC_ENGINE, logger


async def add_result(
    user_id: int,
    full_name: str,
    group_id: int,
    student_id: int,
    test_id: int,
    finished_at: datetime,
    answers: str,
    points: int,
) -> None:
    t1 = perf_counter_ns()

    checked_out = ASYNC_ENGINE.pool.checkedout()
    async with ASYNC_ENGINE.begin() as async_connection:
        t2 = perf_counter_ns()

        await async_connection.exec_driver_sql(
            UserStatement.ADD_RESULT,
            (
                user_id,
                full_name,
                group_id,
                student_id,
                test_id,
                finished_at,
                answers,
                points,
            ),
        )

        t3 = perf_counter_ns()

        logger.info(
            "checkedout=%s | connect=%s | query=%s",
            checked_out,
            (t2 - t1) // 1_000_000,
            (t3 - t2) // 1_000_000,
        )

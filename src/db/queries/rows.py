from time import perf_counter_ns

from sqlalchemy import Row

from src.settings import ASYNC_ENGINE, logger


async def get_rows(statement: str, *args) -> list[Row]:
    t1 = perf_counter_ns()

    checked_out = ASYNC_ENGINE.pool.checkedout()
    async with ASYNC_ENGINE.connect() as async_connection:
        t2 = perf_counter_ns()

        result = await async_connection.exec_driver_sql(statement, args)
        rows = result.all()

        t3 = perf_counter_ns()

        logger.info(
            "checkedout=%s | connect=%s | query=%s | len=%s",
            checked_out,
            (t2 - t1) // 1_000_000,
            (t3 - t2) // 1_000_000,
            len(rows),
        )

    return rows

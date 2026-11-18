from asyncio import run, to_thread
from json import dumps

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.db.models import Test
from src.settings import ASYNC_SESSION, Paths


def _create(name: str, data: dict[int, dict[str, str]]) -> None:
    with open(Paths.TEST_DIR / name, "w", encoding="utf-8") as file:
        file.write(dumps(data, ensure_ascii=False, indent=2))


async def backup_tests() -> None:
    Paths.TEST_DIR.mkdir(parents=True, exist_ok=True)

    async with ASYNC_SESSION() as session:
        stmt = select(Test).options(selectinload(Test.questions)).order_by(Test.id)
        result = await session.scalars(stmt)

        for row in result:
            data = {
                task.id: {
                    "0": task.question,
                    "1": task.option1,
                    "2": task.option2,
                    "3": task.option3,
                    "4": task.option4,
                }
                for task in sorted(row.questions, key=lambda t: t.id)
            }

            await to_thread(_create, f"{row.id:02}_{row.name}.json", data)


if __name__ == "__main__":
    run(backup_tests())

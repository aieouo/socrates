from asyncio import run
from json import load

from sqlalchemy import select

from src.db.models import Task, Test
from src.settings import ASYNC_SESSION, Paths


async def add_tests() -> None:
    async with ASYNC_SESSION.begin() as session:
        for path in sorted(Paths.TEST_DIR.glob("*.json"), key=lambda p: p.stem):
            _, name = path.stem.split("_", 1)

            stmt = select(Test).where(Test.name == name)
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if row is None:
                test = Test(name=name)
                session.add(test)
                await session.flush()

                with open(path, encoding="utf-8") as file:
                    tasks = load(file)

                for _, task in tasks.items():
                    session.add(
                        Task(
                            question=task["0"],
                            option1=task["1"],
                            option2=task["2"],
                            option3=task["3"],
                            option4=task["4"],
                            test_id=test.id,
                        )
                    )


if __name__ == "__main__":
    run(add_tests())

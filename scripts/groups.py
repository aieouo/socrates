from asyncio import run
from json import dumps

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.db.models import Group, Student
from src.settings import ASYNC_SESSION, Paths


class GroupScript:
    @classmethod
    async def all(cls) -> None:
        async with ASYNC_SESSION() as session:
            stmt = select(Group).order_by(Group.name)
            result = await session.scalars(stmt)

            for row in result:
                print(row.id, row.name)

    @classmethod
    async def backup(cls) -> None:
        Paths.GROUPS.parent.mkdir(exist_ok=True)

        async with ASYNC_SESSION() as session:
            stmt = select(Group).options(selectinload(Group.students)).order_by(Group.name)
            result = await session.scalars(stmt)

            s = {row.name: [student.name for student in row.students] for row in result}

        with open(Paths.GROUPS, "w", encoding="utf-8") as file:
            file.write(dumps(s, ensure_ascii=False, indent=2))

    @classmethod
    async def create(cls, new_groups: dict[str, list[str]]) -> None:
        async with ASYNC_SESSION.begin() as session:
            for new_group, new_students in new_groups.items():
                stmt = select(Group).where(Group.name == new_group)
                result = await session.execute(stmt)
                group = result.scalar_one_or_none()

                if group is None:
                    group = Group(name=new_group)
                    session.add(group)

                for new_student in new_students:
                    stmt = select(Student).where(Student.name == new_student, Student.group == group)
                    result = await session.execute(stmt)
                    student = result.scalar_one_or_none()

                    if student is None:
                        student = Student(name=new_student, group=group)
                        session.add(student)

    @classmethod
    async def delete(cls, group: str) -> None:
        async with ASYNC_SESSION.begin() as session:
            stmt = select(Group).where(Group.name == group)
            row = await session.scalar(stmt)

            if row:
                await session.delete(row)


async def main() -> None:
    await GroupScript.all()


if __name__ == "__main__":
    run(main())

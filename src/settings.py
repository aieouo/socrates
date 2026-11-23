from logging import INFO, basicConfig, getLogger
from os import getenv
from pathlib import Path

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


class Paths:
    BASE_DIR = Path(__file__).resolve().parent.parent

    MAXAPI_DIR = BASE_DIR / ".venv" / "Lib" / "site-packages" / "maxapi"

    TEST_DIR = BASE_DIR / "backups" / "tests"
    GROUPS = BASE_DIR / "backups" / "groups.json"

    SECRET_DIR = Path(getenv("SECRET_DIR") or BASE_DIR / "secrets")

    FONT = BASE_DIR / "src" / "assets" / "consola.ttf"
    CERTIFICATE = BASE_DIR / "src" / "assets" / "Russian_Trusted_Root_CA.cer"


def read_secret(secret: str) -> str:
    with open(Paths.SECRET_DIR / secret, encoding="utf-8") as file:
        return file.read().strip()


ASYNC_ENGINE = create_async_engine(
    URL.create(
        "postgresql+asyncpg",
        "postgres",
        read_secret("db_password"),
        getenv("db_host", "localhost"),
        5432,
        "postgres",
    ),
    max_overflow=30,
    pool_pre_ping=True,
    pool_size=10,
    pool_recycle=3600,
)

ASYNC_SESSION = async_sessionmaker(ASYNC_ENGINE)

TOKEN = read_secret("bot_token")

ADMINS = {int(user_id) for user_id in read_secret("bot_admins").split(",")}

CHAT_ID = int(read_secret("bot_chat_id"))

AUTHORIZATION_KEY = read_secret("gigachat_token")

basicConfig(format="%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=INFO)

logger = getLogger()

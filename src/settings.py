from logging import INFO, basicConfig, getLogger
from os import getenv
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


class Paths:
    BASE_DIR = Path(__file__).resolve().parent.parent

    MAXAPI_DIR = BASE_DIR / ".venv" / "Lib" / "site-packages" / "maxapi"

    TEST_DIR = BASE_DIR / "backups" / "tests"
    FEEDBACKS = BASE_DIR / "backups" / "feedbacks.txt"

    SECRET_DIR = Path(getenv("SECRETS") or BASE_DIR / "secrets")

    FONT = BASE_DIR / "src" / "assets" / "consola.ttf"
    CERTIFICATE = BASE_DIR / "src" / "assets" / "Russian_Trusted_Root_CA.cer"


def read_secret(secret: str) -> str:
    with open(Paths.SECRET_DIR / secret, encoding="utf-8") as file:
        return file.read().strip()


DB_PASS = read_secret("db_password")
DB_HOST = getenv("DB_HOST", "localhost")

DSN = f"postgresql+asyncpg://postgres:{DB_PASS}@{DB_HOST}:5432/postgres"

ASYNC_ENGINE = create_async_engine(
    DSN,
    pool_size=20,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

ASYNC_SESSION = async_sessionmaker(ASYNC_ENGINE)

TOKEN = read_secret("bot_token")

ADMINS = {int(user_id) for user_id in read_secret("bot_admins").split(",")}

AUTHORIZATION_KEY = read_secret("gigachat_token")

basicConfig(format="%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=INFO)

logger = getLogger()

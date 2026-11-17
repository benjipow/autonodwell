import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/autonodwell_test")
os.environ["AUTH_MODE"] = "dev"
os.environ["CRM_PROVIDER"] = "none"
os.environ["ADMIN_EMAILS"] = "boss@example.com"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")  # tests always run against the real migrations
    from app.db import SessionLocal
    from app.seed import seed_reference

    with SessionLocal() as db:
        seed_reference(db)
    yield


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def auth(uid: str, email: str | None = None) -> dict:
    return {"Authorization": f"Bearer dev:{uid}:{email or ''}"}

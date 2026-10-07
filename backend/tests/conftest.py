import os

# Must be set before the app (and its Settings) is imported.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ["USE_STUB_ENGINES"] = "true"
os.environ["SEED_ON_STARTUP"] = "false"
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401,E402
from app.core.rate_limit import reset_rate_limits  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.seed import seed_models  # noqa: E402
from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    with Session() as db:
        seed_models(db)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    reset_rate_limits()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register_and_login(client, email="a@example.com", password="password123", name="Alice") -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password, "full_name": name})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def auth(client):
    return register_and_login(client)


@pytest.fixture()
def auth2(client):
    return register_and_login(client, "b@example.com", "password123", "Bob")

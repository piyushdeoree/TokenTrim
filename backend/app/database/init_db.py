"""Quick-start helper: create all tables directly (no Alembic) and seed sample models.

    python -m app.database.init_db

Use Alembic migrations for anything beyond local development.
"""
import app.models  # noqa: F401
from app.database.base import Base
from app.database.seed import seed_models
from app.database.session import SessionLocal, engine

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_models(db)
    print("Tables created and sample models seeded.")

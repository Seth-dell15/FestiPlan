import os
import tempfile

import pytest

# La base de test doit être configurée avant d'importer l'application.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["FESTIPLAN_DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.adapters.secondary.database import models  # noqa: E402, F401  enregistre les tables dans Base.metadata
from app.adapters.secondary.database.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def prepare():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        os.unlink(_tmp.name)
    except OSError:
        pass


@pytest.fixture
def client():
    db = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()
    with TestClient(app) as c:
        yield c

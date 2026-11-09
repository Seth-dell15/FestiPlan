import os
import tempfile

import pytest

# La base de test doit être configurée avant le premier import de l'application.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["FESTIPLAN_DATABASE_URL"] = f"sqlite:///{_tmp.name}"


@pytest.fixture(scope="session")
def prepare():
    # Imports locaux : les tests du domaine et des cas d'usage ne chargent ni FastAPI ni SQLAlchemy.
    from app.adapters.secondary.database import models  # noqa: F401  enregistre les tables dans Base.metadata
    from app.adapters.secondary.database.session import Base, engine

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        os.unlink(_tmp.name)
    except OSError:
        pass


@pytest.fixture
def client(prepare):
    from fastapi.testclient import TestClient

    from app.adapters.secondary.database.session import Base, SessionLocal
    from app.main import app

    db = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()
    with TestClient(app) as c:
        yield c

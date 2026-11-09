from datetime import datetime
import pytest
from app.config import settings


@pytest.fixture
def setup_festival_and_concert(client):
    """Prépare un festival, un artiste, une scène et un concert pour les tests d'intégration."""
    # 1. Festival
    r_fest = client.post(
        "/festivals",
        json={
            "name": "Hellforge Operations Edition",
            "location": "Clisson",
            "start_date": "2027-06-18T10:00:00",
            "end_date": "2027-06-20T23:59:00",
        },
    )
    assert r_fest.status_code == 201
    fest_id = r_fest.json()["id"]

    # 2. Artiste
    r_art = client.post(
        "/artists",
        json={"name": "Blackened Core", "genre": "Death Metal", "required_equipment": []},
    )
    art_id = r_art.json()["id"]

    # 3. Scène
    r_stage = client.post(
        "/stages",
        json={
            "festival_id": fest_id,
            "name": "Temple",
            "capacity": 20000,
            "available_equipment": [],
        },
    )
    stage_id = r_stage.json()["id"]

    # 4. Concert
    r_concert = client.post(
        "/concerts",
        json={
            "festival_id": fest_id,
            "artist_id": art_id,
            "stage_id": stage_id,
            "start_time": "2027-06-18T15:00:00",
            "end_time": "2027-06-18T16:00:00",
        },
    )
    assert r_concert.status_code == 201
    concert_id = r_concert.json()["id"]

    return {
        "festival_id": fest_id,
        "artist_id": art_id,
        "stage_id": stage_id,
        "concert_id": concert_id,
    }


# =====================================================================
# Tests Intégration : Incidents (R10)
# =====================================================================

def test_api_create_incident_nominal(client, setup_festival_and_concert):
    cid = setup_festival_and_concert["concert_id"]
    r = client.post(
        "/incidents",
        json={
            "concert_id": cid,
            "description": "Panne de retour son sur scène gauche",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["concert_id"] == cid
    assert data["description"] == "Panne de retour son sur scène gauche"
    assert data["resolved"] is False
    assert "id" in data


def test_api_create_incident_unknown_concert_returns_404(client):
    r = client.post(
        "/incidents",
        json={
            "concert_id": 99999,
            "description": "Incident sur un concert fantôme",
        },
    )
    assert r.status_code == 404
    assert "introuvable" in r.json()["detail"].lower()


def test_api_create_incident_empty_description_refused_r10(client, setup_festival_and_concert):
    cid = setup_festival_and_concert["concert_id"]
    # Pydantic min_length=3 ou validation domaine R10
    r = client.post(
        "/incidents",
        json={
            "concert_id": cid,
            "description": "  ",
        },
    )
    assert r.status_code in (400, 422)


def test_api_list_and_resolve_incident(client, setup_festival_and_concert):
    cid = setup_festival_and_concert["concert_id"]
    r_create = client.post(
        "/incidents",
        json={
            "concert_id": cid,
            "description": "Éclairage projecteur éteint",
        },
    )
    incident_id = r_create.json()["id"]

    # 1. Lister les incidents
    r_list = client.get(f"/incidents?concert_id={cid}")
    assert r_list.status_code == 200
    incidents = r_list.json()
    assert any(i["id"] == incident_id for i in incidents)

    # 2. Résoudre l'incident
    r_resolve = client.patch(f"/incidents/{incident_id}/resolve")
    assert r_resolve.status_code == 200
    assert r_resolve.json()["resolved"] is True

    # 3. Tenter de résoudre à nouveau (erreur 400)
    r_resolve_again = client.patch(f"/incidents/{incident_id}/resolve")
    assert r_resolve_again.status_code == 400


# =====================================================================
# Tests Intégration : Publication du Festival (R8 & Défaut 2)
# =====================================================================

def test_api_publish_festival_nominal_success(client, setup_festival_and_concert):
    fid = setup_festival_and_concert["festival_id"]
    r = client.post(f"/festivals/{fid}/publish")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == fid
    assert data["status"] == "published"


def test_api_publish_already_published_festival_returns_400(client, setup_festival_and_concert):
    fid = setup_festival_and_concert["festival_id"]
    r1 = client.post(f"/festivals/{fid}/publish")
    assert r1.status_code == 200

    r2 = client.post(f"/festivals/{fid}/publish")
    assert r2.status_code == 400
    assert "déjà publié" in r2.json()["detail"].lower()


def test_api_publish_with_schedule_conflict_refused_r8(client, setup_festival_and_concert):
    """Vérifie la règle R8 : un festival avec des concerts en conflit ne peut pas être publié."""
    fid = setup_festival_and_concert["festival_id"]
    stage_id = setup_festival_and_concert["stage_id"]

    # Créer un deuxième artiste
    r_art2 = client.post(
        "/artists",
        json={"name": "Ghost Choir", "genre": "Gothic Metal", "required_equipment": []},
    )
    art2_id = r_art2.json()["id"]

    # Créer un second concert SUR LA MÊME SCÈNE AU MÊME CRÉNEAU (15h - 16h)
    # L'endpoint POST standard sans notre UseCase de déplacement permettrait une insertion ou via DB
    from app.models import Concert as ConcertOrm
    from app.database import SessionLocal
    db = SessionLocal()
    conflicting_concert = ConcertOrm(
        festival_id=fid,
        artist_id=art2_id,
        stage_id=stage_id,
        start_time=datetime(2027, 6, 18, 15, 0),
        end_time=datetime(2027, 6, 18, 16, 0),
        status="scheduled",
    )
    db.add(conflicting_concert)
    db.commit()
    db.close()

    # Tenter de publier le festival : doit être rejeté selon la règle R8
    r_pub = client.post(f"/festivals/{fid}/publish")
    assert r_pub.status_code == 400
    assert "conflit" in r_pub.json()["detail"].lower()


def test_api_publish_notification_failure_does_not_crash(client, setup_festival_and_concert, monkeypatch):
    """Résolution Défaut 2 : une panne de notification ne doit pas faire crash (500) la publication."""
    fid = setup_festival_and_concert["festival_id"]
    monkeypatch.setattr(settings, "fail_notifications", True)

    r = client.post(f"/festivals/{fid}/publish")
    assert r.status_code == 200
    assert r.json()["status"] == "published"

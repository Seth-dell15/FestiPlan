from datetime import datetime
import pytest
from app.config import settings


@pytest.fixture
def setup_festival_data(client):
    """Initialise un festival, deux artistes et deux scènes dans la base SQLite."""
    # 1. Créer le festival
    r_fest = client.post(
        "/festivals",
        json={
            "name": "Hellforge Open Air 2027",
            "location": "Clisson",
            "start_date": "2027-06-18T10:00:00",
            "end_date": "2027-06-20T23:59:00",
        },
    )
    assert r_fest.status_code == 201
    fest_id = r_fest.json()["id"]

    # 2. Créer Artiste 1 & 2
    r_a1 = client.post(
        "/artists",
        json={"name": "Iron Vow", "genre": "Heavy Metal", "required_equipment": ["large_rigging"]},
    )
    r_a2 = client.post(
        "/artists",
        json={"name": "Crimson Engine", "genre": "Thrash Metal", "required_equipment": []},
    )
    a1_id = r_a1.json()["id"]
    a2_id = r_a2.json()["id"]

    # 3. Créer Scène 1 (Mainstage) & Scène 2 (Warzone)
    r_s1 = client.post(
        "/stages",
        json={
            "festival_id": fest_id,
            "name": "Mainstage",
            "capacity": 50000,
            "available_equipment": ["large_rigging", "special_lighting"],
        },
    )
    r_s2 = client.post(
        "/stages",
        json={
            "festival_id": fest_id,
            "name": "Warzone",
            "capacity": 15000,
            "available_equipment": ["special_lighting"],
        },
    )
    s1_id = r_s1.json()["id"]
    s2_id = r_s2.json()["id"]

    return {
        "festival_id": fest_id,
        "artist_1_id": a1_id,
        "artist_2_id": a2_id,
        "stage_1_id": s1_id,
        "stage_2_id": s2_id,
    }


def test_integration_create_and_reschedule_concert(client, setup_festival_data):
    data = setup_festival_data

    # Création d'un concert via HTTP POST
    res_create = client.post(
        "/concerts",
        json={
            "festival_id": data["festival_id"],
            "artist_id": data["artist_1_id"],
            "stage_id": data["stage_1_id"],
            "start_time": "2027-06-18T18:00:00",
            "end_time": "2027-06-18T19:00:00",
        },
    )
    assert res_create.status_code == 201
    concert = res_create.json()
    concert_id = concert["id"]
    assert concert["status"] == "scheduled"

    # Déplacement valide via HTTP PATCH
    res_reschedule = client.patch(
        f"/concerts/{concert_id}/reschedule",
        json={
            "start_time": "2027-06-18T20:00:00",
            "end_time": "2027-06-18T21:00:00",
        },
    )
    assert res_reschedule.status_code == 200
    updated = res_reschedule.json()
    assert updated["start_time"] == "2027-06-18T20:00:00"

    # Vérification par GET
    res_get = client.get(f"/concerts/{concert_id}")
    assert res_get.status_code == 200
    assert res_get.json()["start_time"] == "2027-06-18T20:00:00"


def test_integration_defect_1_stage_overlap_rejected(client, setup_festival_data):
    data = setup_festival_data

    # Concert A sur Mainstage : 18h - 19h
    r_a = client.post(
        "/concerts",
        json={
            "festival_id": data["festival_id"],
            "artist_id": data["artist_1_id"],
            "stage_id": data["stage_1_id"],
            "start_time": "2027-06-18T18:00:00",
            "end_time": "2027-06-18T19:00:00",
        },
    )
    # Concert B sur Mainstage : 21h - 22h
    r_b = client.post(
        "/concerts",
        json={
            "festival_id": data["festival_id"],
            "artist_id": data["artist_2_id"],
            "stage_id": data["stage_1_id"],
            "start_time": "2027-06-18T21:00:00",
            "end_time": "2027-06-18T22:00:00",
        },
    )
    concert_b_id = r_b.json()["id"]

    # Tentative de déplacer Concert B pour chevaucher Concert A (18h30 - 19h30)
    res_conflict = client.patch(
        f"/concerts/{concert_b_id}/reschedule",
        json={
            "start_time": "2027-06-18T18:30:00",
            "end_time": "2027-06-18T19:30:00",
        },
    )
    assert res_conflict.status_code == 400
    assert "Conflit de scène" in res_conflict.json()["detail"]


def test_integration_defect_1_artist_overlap_rejected(client, setup_festival_data):
    data = setup_festival_data

    # Concert 1 : Artiste 1 sur Mainstage de 18h à 19h
    client.post(
        "/concerts",
        json={
            "festival_id": data["festival_id"],
            "artist_id": data["artist_1_id"],
            "stage_id": data["stage_1_id"],
            "start_time": "2027-06-18T18:00:00",
            "end_time": "2027-06-18T19:00:00",
        },
    )

    # Concert 2 : Même Artiste 1 sur Warzone de 21h à 22h
    r2 = client.post(
        "/concerts",
        json={
            "festival_id": data["festival_id"],
            "artist_id": data["artist_1_id"],
            "stage_id": data["stage_2_id"],
            "start_time": "2027-06-18T21:00:00",
            "end_time": "2027-06-18T22:00:00",
        },
    )
    concert_2_id = r2.json()["id"]

    # Déplacer Concert 2 sur 18h15 - 19h15 (chevauchement avec Concert 1 sur l'autre scène)
    res_conflict = client.patch(
        f"/concerts/{concert_2_id}/reschedule",
        json={
            "start_time": "2027-06-18T18:15:00",
            "end_time": "2027-06-18T19:15:00",
        },
    )
    assert res_conflict.status_code == 400
    assert "Conflit d'artiste" in res_conflict.json()["detail"]


def test_integration_defect_2_notification_failure_does_not_crash_http(client, setup_festival_data, monkeypatch):
    """Défaut 2 : Une panne du service d'email ne doit pas provoquer un code 500 post-commit."""
    data = setup_festival_data

    # Création d'un concert
    r = client.post(
        "/concerts",
        json={
            "festival_id": data["festival_id"],
            "artist_id": data["artist_1_id"],
            "stage_id": data["stage_1_id"],
            "start_time": "2027-06-18T18:00:00",
            "end_time": "2027-06-18T19:00:00",
        },
    )
    concert_id = r.json()["id"]

    # Simuler la panne de notification (configuration FESTIPLAN_FAIL_NOTIFICATIONS=True)
    monkeypatch.setattr(settings, "fail_notifications", True)

    # Déplacer le concert
    res = client.patch(
        f"/concerts/{concert_id}/reschedule",
        json={
            "start_time": "2027-06-18T20:00:00",
            "end_time": "2027-06-18T21:00:00",
        },
    )

    # Dans le legacy, l'API renvoyait 500 Internal Server Error.
    # Dans notre architecture hexagonale, la persistance a réussi et l'API renvoie 200 OK.
    assert res.status_code == 200
    assert res.json()["start_time"] == "2027-06-18T20:00:00"

    # Vérification que le concert a bien été mis à jour en base de données
    persisted = client.get(f"/concerts/{concert_id}").json()
    assert persisted["start_time"] == "2027-06-18T20:00:00"


def test_integration_defect_3_published_festival_locked(client, setup_festival_data):
    """Défaut 3 : Un festival publié ne doit pas accepter de modification ordinaire."""
    data = setup_festival_data

    r = client.post(
        "/concerts",
        json={
            "festival_id": data["festival_id"],
            "artist_id": data["artist_1_id"],
            "stage_id": data["stage_1_id"],
            "start_time": "2027-06-18T18:00:00",
            "end_time": "2027-06-18T19:00:00",
        },
    )
    concert_id = r.json()["id"]

    # Publication du festival
    pub_res = client.post(f"/festivals/{data['festival_id']}/publish")
    assert pub_res.status_code == 200

    # Tentative de déplacement après publication
    res = client.patch(
        f"/concerts/{concert_id}/reschedule",
        json={
            "start_time": "2027-06-18T20:00:00",
            "end_time": "2027-06-18T21:00:00",
        },
    )
    assert res.status_code == 400
    assert "déjà été publié" in res.json()["detail"]


def test_integration_cancel_concert(client, setup_festival_data):
    data = setup_festival_data

    r = client.post(
        "/concerts",
        json={
            "festival_id": data["festival_id"],
            "artist_id": data["artist_1_id"],
            "stage_id": data["stage_1_id"],
            "start_time": "2027-06-18T18:00:00",
            "end_time": "2027-06-18T19:00:00",
        },
    )
    concert_id = r.json()["id"]

    # Annulation
    res_cancel = client.post(f"/concerts/{concert_id}/cancel")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "cancelled"

    # Vérification via GET
    assert client.get(f"/concerts/{concert_id}").json()["status"] == "cancelled"

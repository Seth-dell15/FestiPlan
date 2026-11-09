"""Tests de non-régression du pôle Planification (Dev 1).

Chaque test reproduit un comportement défectueux constaté sur la branche
feat/security-hardening avant correction :

- R4 : un concert pouvait référencer un artiste, une scène ou un festival inexistant (201)
- R4 : la scène pouvait appartenir à un autre festival (201)
- R5 : un artiste pouvait être programmé sur une scène sans ses équipements (201)
- Déplacer un concert annulé provoquait une erreur 500
- Une date avec fuseau horaire ("...Z") provoquait une erreur 500
- R7 : un concert pouvait être annulé alors que le festival était publié (200)
- Annuler deux fois le même concert était accepté silencieusement (200)
- Défaut 2 : la réponse HTTP ne signalait pas l'échec de la notification
"""
import pytest
from app.config import settings


@pytest.fixture
def data(client):
    def post(url, payload):
        r = client.post(url, json=payload)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    fest = post("/festivals", {
        "name": "Hellforge Open Air",
        "location": "Clisson",
        "start_date": "2027-06-18T10:00:00",
        "end_date": "2027-06-20T23:59:00",
    })
    other_fest = post("/festivals", {
        "name": "Autre Festival",
        "location": "Nantes",
        "start_date": "2027-07-01T10:00:00",
        "end_date": "2027-07-03T23:59:00",
    })
    rigging_artist = post("/artists", {"name": "Iron Vow", "genre": "Heavy", "required_equipment": ["large_rigging"]})
    simple_artist = post("/artists", {"name": "Concrete Reign", "genre": "Hardcore", "required_equipment": []})
    mainstage = post("/stages", {"festival_id": fest, "name": "Mainstage", "capacity": 50000,
                                 "available_equipment": ["large_rigging", "special_lighting"]})
    warzone = post("/stages", {"festival_id": fest, "name": "Warzone", "capacity": 15000,
                               "available_equipment": ["special_lighting"]})
    foreign_stage = post("/stages", {"festival_id": other_fest, "name": "Ailleurs", "capacity": 1000,
                                     "available_equipment": []})
    return {
        "fest": fest, "rigging_artist": rigging_artist, "simple_artist": simple_artist,
        "mainstage": mainstage, "warzone": warzone, "foreign_stage": foreign_stage,
    }


def concert(data, **overrides):
    payload = {
        "festival_id": data["fest"],
        "artist_id": data["simple_artist"],
        "stage_id": data["warzone"],
        "start_time": "2027-06-19T10:00:00",
        "end_time": "2027-06-19T11:00:00",
    }
    payload.update(overrides)
    return payload


# --- R4 : références existantes et cohérentes --------------------------------

@pytest.mark.parametrize("field", ["artist_id", "stage_id", "festival_id"])
def test_r4_unknown_reference_is_rejected(client, data, field):
    r = client.post("/concerts", json=concert(data, **{field: 9999}))
    assert r.status_code == 404
    assert client.get(f"/concerts?festival_id={data['fest']}").json() == []


def test_r4_stage_of_another_festival_is_rejected(client, data):
    r = client.post("/concerts", json=concert(data, stage_id=data["foreign_stage"]))
    assert r.status_code == 400
    assert "appartient" in r.json()["detail"]


# --- R5 : équipements ------------------------------------------------------

def test_r5_stage_without_required_equipment_is_rejected(client, data):
    r = client.post("/concerts", json=concert(data, artist_id=data["rigging_artist"], stage_id=data["warzone"]))
    assert r.status_code == 400
    assert "large_rigging" in r.json()["detail"]


def test_r5_stage_with_required_equipment_is_accepted(client, data):
    r = client.post("/concerts", json=concert(data, artist_id=data["rigging_artist"], stage_id=data["mainstage"]))
    assert r.status_code == 201


# --- Concert annulé --------------------------------------------------------

def test_rescheduling_a_cancelled_concert_returns_409_not_500(client, data):
    cid = client.post("/concerts", json=concert(data)).json()["id"]
    assert client.post(f"/concerts/{cid}/cancel").status_code == 200

    r = client.patch(f"/concerts/{cid}/reschedule",
                     json={"start_time": "2027-06-19T12:00:00", "end_time": "2027-06-19T13:00:00"})
    assert r.status_code == 409
    assert "annulé" in r.json()["detail"]


def test_cancelling_twice_is_rejected(client, data):
    cid = client.post("/concerts", json=concert(data)).json()["id"]
    assert client.post(f"/concerts/{cid}/cancel").status_code == 200
    assert client.post(f"/concerts/{cid}/cancel").status_code == 409


# --- Fuseau horaire ----------------------------------------------------------

def test_timezone_aware_dates_do_not_crash(client, data):
    r = client.post("/concerts", json=concert(data, start_time="2027-06-19T10:00:00Z", end_time="2027-06-19T11:00:00Z"))
    assert r.status_code == 201
    assert r.json()["start_time"] == "2027-06-19T10:00:00"


def test_timezone_aware_dates_are_still_checked_against_festival_period(client, data):
    # 2027-06-18T09:30:00+00:00 est avant l'ouverture (10:00) du festival
    r = client.post("/concerts", json=concert(data, start_time="2027-06-18T09:30:00Z", end_time="2027-06-18T10:30:00Z"))
    assert r.status_code == 400


# --- R7 : festival publié ----------------------------------------------------

def test_r7_cancel_is_rejected_once_festival_is_published(client, data):
    cid = client.post("/concerts", json=concert(data)).json()["id"]
    assert client.post(f"/festivals/{data['fest']}/publish").status_code == 200

    r = client.post(f"/concerts/{cid}/cancel")
    assert r.status_code == 409
    assert client.get(f"/concerts/{cid}").json()["status"] == "scheduled"


# --- Défaut 2 : la réponse signale l'échec de la notification ----------------

def test_reschedule_response_reports_notification_status(client, data):
    cid = client.post("/concerts", json=concert(data)).json()["id"]
    body = {"start_time": "2027-06-19T12:00:00", "end_time": "2027-06-19T13:00:00"}

    ok = client.patch(f"/concerts/{cid}/reschedule", json=body)
    assert ok.status_code == 200
    assert ok.json()["notification_sent"] is True

    settings.fail_notifications = True
    try:
        body = {"start_time": "2027-06-19T14:00:00", "end_time": "2027-06-19T15:00:00"}
        failed = client.patch(f"/concerts/{cid}/reschedule", json=body)
    finally:
        settings.fail_notifications = False
    assert failed.status_code == 200
    assert failed.json()["notification_sent"] is False
    # la modification est bien persistée malgré l'échec de notification
    assert client.get(f"/concerts/{cid}").json()["start_time"] == "2027-06-19T14:00:00"

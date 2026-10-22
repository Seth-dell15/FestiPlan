FESTIVAL = {
    "name": "Hellforge Open Air",
    "location": "Clisson-sur-Rivière",
    "start_date": "2027-06-18T10:00:00",
    "end_date": "2027-06-20T23:59:00",
}


def create_festival(client):
    return client.post("/festivals", json=FESTIVAL).json()["id"]


def test_create_then_list_artists(client):
    created = client.post(
        "/artists", json={"name": "Iron Vow", "genre": "Heavy metal", "required_equipment": ["pyro", "double_kick"]}
    )

    assert created.status_code == 201
    assert created.json()["required_equipment"] == ["double_kick", "pyro"]
    assert [artist["name"] for artist in client.get("/artists").json()] == ["Iron Vow"]


def test_create_stage_in_existing_festival(client):
    festival_id = create_festival(client)

    response = client.post(
        "/stages",
        json={"festival_id": festival_id, "name": "Valley", "capacity": 8000, "available_equipment": ["special_lighting"]},
    )

    assert response.status_code == 201
    assert response.json()["available_equipment"] == ["special_lighting"]


def test_create_stage_in_unknown_festival_returns_400(client):
    response = client.post("/stages", json={"festival_id": 999, "name": "Valley", "capacity": 8000})

    assert response.status_code == 400
    assert "introuvable" in response.json()["detail"]


def test_list_stages_of_a_festival(client):
    festival_id = create_festival(client)
    other_id = create_festival(client)
    client.post("/stages", json={"festival_id": festival_id, "name": "Valley", "capacity": 8000})
    client.post("/stages", json={"festival_id": other_id, "name": "Altar", "capacity": 5000})

    stages = client.get("/stages", params={"festival_id": festival_id}).json()

    assert [stage["name"] for stage in stages] == ["Valley"]


def test_create_list_and_get_festival(client):
    created = client.post("/festivals", json=FESTIVAL)

    assert created.status_code == 201
    assert created.json()["status"] == "preparation"
    festival_id = created.json()["id"]
    assert [festival["id"] for festival in client.get("/festivals").json()] == [festival_id]
    assert client.get(f"/festivals/{festival_id}").json()["name"] == "Hellforge Open Air"


def test_get_unknown_festival_returns_404(client):
    assert client.get("/festivals/999").status_code == 404


def test_publish_route_still_works_on_a_new_festival(client):
    festival_id = create_festival(client)

    response = client.post(f"/festivals/{festival_id}/publish")

    assert response.status_code == 200
    assert client.get(f"/festivals/{festival_id}").json()["status"] == "published"

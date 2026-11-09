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
        json={
            "festival_id": festival_id,
            "name": "Valley",
            "capacity": 8000,
            "available_equipment": ["special_lighting"],
        },
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


def program_concert(client, festival_id, artist_id):
    stage = client.post("/stages", json={"festival_id": festival_id, "name": "Valley", "capacity": 8000}).json()
    response = client.post("/concerts", json={
        "festival_id": festival_id,
        "artist_id": artist_id,
        "stage_id": stage["id"],
        "start_time": "2027-06-18T18:00:00",
        "end_time": "2027-06-18T19:00:00",
    })
    assert response.status_code == 201, response.text


def test_publish_route_still_works_on_a_new_festival(client):
    festival_id = create_festival(client)
    artist = client.post("/artists", json={"name": "Iron Vow", "genre": "Heavy metal"}).json()
    program_concert(client, festival_id, artist["id"])

    response = client.post(f"/festivals/{festival_id}/publish")

    assert response.status_code == 200
    assert response.json()["notification_sent"] is True
    assert client.get(f"/festivals/{festival_id}").json()["status"] == "published"


def test_publishing_an_empty_schedule_returns_400(client):
    festival_id = create_festival(client)

    response = client.post(f"/festivals/{festival_id}/publish")

    assert response.status_code == 400
    assert client.get(f"/festivals/{festival_id}").json()["status"] == "preparation"


def test_festival_with_mixed_timezone_dates_does_not_crash(client):
    payload = {**FESTIVAL, "start_date": "2027-06-18T10:00:00Z", "end_date": "2027-06-20T23:00:00"}

    response = client.post("/festivals", json=payload)

    assert response.status_code == 201
    assert response.json()["start_date"] == "2027-06-18T10:00:00"


def test_festival_with_mixed_timezone_dates_is_still_validated(client):
    payload = {**FESTIVAL, "start_date": "2027-06-20T10:00:00+02:00", "end_date": "2027-06-18T10:00:00"}

    assert client.post("/festivals", json=payload).status_code == 400


SCRIPT = "<script>alert(1)</script>"


def test_festival_text_fields_are_sanitized(client):
    payload = {**FESTIVAL, "name": f"{SCRIPT}Hellforge", "location": f"{SCRIPT}Clisson"}

    body = client.post("/festivals", json=payload).json()

    assert (body["name"], body["location"]) == ("Hellforge", "Clisson")


def test_artist_text_fields_are_sanitized(client):
    body = client.post("/artists", json={"name": f"{SCRIPT}Iron Vow", "genre": f"{SCRIPT}Heavy metal"}).json()

    assert (body["name"], body["genre"]) == ("Iron Vow", "Heavy metal")


def test_stage_name_is_sanitized(client):
    festival_id = create_festival(client)

    body = client.post("/stages", json={"festival_id": festival_id, "name": f"{SCRIPT}Valley", "capacity": 8000}).json()

    assert body["name"] == "Valley"


def test_punctuation_in_names_survives_creation_and_publication(client):
    payload = {**FESTIVAL, "name": "Rock & Metal", "location": "L'Isle-d'Abeau"}

    festival = client.post("/festivals", json=payload).json()
    artist = client.post("/artists", json={"name": "Guns N' Roses", "genre": "Hard & Heavy"}).json()
    program_concert(client, festival["id"], artist["id"])
    published = client.post(f"/festivals/{festival['id']}/publish").json()

    assert (festival["name"], festival["location"]) == ("Rock & Metal", "L'Isle-d'Abeau")
    assert (artist["name"], artist["genre"]) == ("Guns N' Roses", "Hard & Heavy")
    assert published["name"] == "Rock & Metal"
    assert published["status"] == "published"

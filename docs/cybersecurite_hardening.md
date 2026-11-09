# Dossier d'Ingénierie Cybersécurité & Hardening — FestiPlan

**Projet :** FestiPlan — API de Gestion de Festival  
**Contexte :** Renforcement de la sécurité applicative (Sécurité en Profondeur dans l'Architecture Hexagonale)  
**Pôles contributeurs :** Initialement conçu par Développeur 3 (Opérations), puis étendu et généralisé par Développeur 2 (Logistique) et Développeur 1 (Planification)  
**Référence des menaces :** OWASP Top 10 API Security Risks  

---

## 1. Pourquoi la Cybersécurité dans FestiPlan ?

Bien que le sujet académique initial se concentre sur l'architecture hexagonale et DDD, **une application d'entreprise ne peut pas dissocier qualité architecturale et sécurité**.

Dans l'état initial (legacy), plusieurs faiblesses techniques laissaient entrevoir des risques majeurs :
1. **Absence totale d'en-têtes HTTP de sécurité :** Vulnérabilité au Clickjacking (`X-Frame-Options` absent) et au MIME-type sniffing (`X-Content-Type-Options` absent).
2. **Risque de Stored XSS (Cross-Site Scripting) :** Aucune neutralisation des balises `<script>` ou handlers d'événements JavaScript (`onerror=`, `onload=`) dans les champs textuels libres (descriptions d'incidents, noms d'artistes, noms et lieux de festivals, noms de scènes).
3. **Risque de fuite d'informations (Information Disclosure) :** En cas d'exception non gérée (erreur 500), le serveur renvoyait une stack trace complète exposant les chemins système de la machine hôte (`C:\Users\...`), les requêtes SQL et la structure interne de la base de données SQLite.
4. **Risque de déni de service par saturation (DoS applicatif) :** Absence de garde-fous sur la taille maximale de certains flux de données.
5. **Robustesse temporelle et fuseaux horaires :** Risque de plantage serveur 500 sur des dates comportant un fuseau horaire ISO (`Z`).

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
        P["Pydantic Schemas (Tous les pôles)<br><i>Typage strict, bornage des longueurs (max_length)</i>"]
        S["InputSanitizer<br><i>Éradication des &lt;script&gt; et échappement HTML systématique</i>"]
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

### Organisation des Composants de Sécurité
* **`app/adapters/primary/security/security_headers.py`** : Middleware injectant automatiquement les en-têtes HTTP de sécurité recommandés par l'OWASP sur toutes les réponses de l'application.
* **`app/adapters/primary/security/sanitizer.py`** : Composant `InputSanitizer` éliminant les balises exécutables `<script>` et convertissant les caractères réservés (`<`, `>`, `"`, `'`, `&`) en entités HTML inoffensives.
* **`app/adapters/primary/security/error_handler.py`** : Gestionnaire global d'exceptions captant tout crash imprévu, consignant l'erreur en log privé et masquant totalement la stack trace au client HTTP.

---

## 3. Généralisation de la Sécurité sur l'Ensemble des Pôles

Initialement amorcée sur le pôle Opérations, la démarche de sécurisation a été **généralisée à tous les modules** du projet lors des consolidations de code :

### 3.1 Pôle Opérations (Développeur 3)
* Assainissement systématique des descriptions d'incidents via `IncidentCreate`.
* Mise en place du middleware de protection contre le Clickjacking et le Sniffing MIME.
* Découplage de la notification pour éviter les faux codes HTTP 500 post-persistance.

### 3.2 Pôle Logistique & Référentiel (Développeur 2)
* **Généralisation d'`InputSanitizer`** à l'ensemble des schémas d'entrée du référentiel :
  - `app/adapters/primary/api/schemas/festival_schemas.py` : assainissement des champs `name` et `location`.
  - `app/adapters/primary/api/schemas/artist_schemas.py` : assainissement des champs `name` et `genre`.
  - `app/adapters/primary/api/schemas/stage_schemas.py` : assainissement du champ `name`.
* **Tests d'intégration XSS dédiés** dans `tests/integration/test_logistics_api.py` :
  - `test_festival_text_fields_are_sanitized`
  - `test_artist_text_fields_are_sanitized`
  - `test_stage_name_is_sanitized`

### 3.3 Pôle Planification (Développeur 1)
* **Robustesse temporelle et normalisation UTC :** Prise en charge des dates avec timezone UTC sans plantage serveur (`timezone_aware_dates_do_not_crash`).
* **Statuts HTTP sécurisés et cohérents :** Rejet d'une tentative de déplacement d'un concert annulé avec un code **HTTP 409 Conflict** propre (au lieu d'un crash 500 interne).
* **Validation stricte des références :** Rejet immédiat de toute tentative d'injection d'identifiants orphelins (festival, scène, artiste).

---

## 4. Détail des Risques Traités & Solutions Apportées

### 4.1 Protection contre les Injections SQL (OWASP A03 — Injection)
* **Menace :** Injection de fragments SQL (`' OR 1=1 --`, `UNION SELECT`, `DROP TABLE festivals;--`) visant à altérer ou exfiltrer la base.
* **Remédiation :**
  1. *Au niveau des DTOs :* Typage strict `int` des identifiants dans les routes et DTOs (rejet immédiat avec code **HTTP 422**).
  2. *Au niveau des Repositories :* Aucune concaténation de chaînes SQL brutes. SQLAlchemy utilise exclusivement des requêtes paramétrées avec échappement natif des variables.
* **Preuve par les tests :** Injection de `' OR '1'='1` et `DROP TABLE` dans les paramètres et les corps JSON. Les requêtes sont traitées comme du texte littéral inoffensif sans jamais altérer la structure de la base.

---

### 4.2 Protection contre les Injections XSS (Cross-Site Scripting)
* **Menace :** Injection de scripts malveillants (`<script>alert(1)</script>`, `<img src=x onerror=... />`) stockés en base puis réaffichés dans le navigateur d'un organisateur ou festivalier.
* **Remédiation :**
  * Le composant `InputSanitizer.clean_text()` est branché via des `@field_validator` sur tous les DTOs textuels (`IncidentCreate`, `FestivalCreateSchema`, `ArtistCreateSchema`, `StageCreateSchema`).
  * Les balises `<script>` sont éradiquées et les caractères spéciaux convertis en entités HTML (`&lt;`, `&gt;`).
* **Preuve par les tests :** 4 tests automatisés dédiés valident que l'injection de scripts sur les incidents, festivals, artistes et scènes est systématiquement neutralisée.

---

### 4.3 Prévention des Fuites d'Informations (OWASP A05 — Information Disclosure)
* **Menace :** En cas d'erreur inattendue (panne SQLite, bug, indisponibilité système), renvoi de la stack trace complète dévoilant l'arborescence des disques de la machine hôte (`C:\Users\...`), les requêtes SQL internes et la configuration.
* **Remédiation :**
  * Le gestionnaire `global_security_exception_handler` capture les exceptions inattendues.
  * L'erreur est logguée avec son contexte côté serveur uniquement.
  * Le client HTTP reçoit une réponse **HTTP 500** anonymisée : `{"detail": "Une erreur interne est survenue. Veuillez contacter l'administrateur."}`.
* **Preuve par les tests :** `test_unhandled_exception_does_not_leak_system_paths` valide l'absence absolue de tout chemin de fichier système dans la réponse retournée au client.

---

### 4.4 En-têtes HTTP de Sécurité (OWASP Security Headers)
* **Menace :** Clickjacking, écoute de trafic et attaques MIME Sniffing.
* **Remédiation :**
  * Le middleware `SecurityHeadersMiddleware` injecte sur **toutes les réponses HTTP** :
    * `X-Content-Type-Options: nosniff` (bloque le sniffing de type MIME)
    * `X-Frame-Options: DENY` (protection anti-clickjacking)
    * `X-XSS-Protection: 1; mode=block`
    * `Referrer-Policy: strict-origin-when-cross-origin`
    * `Permissions-Policy: geolocation=(), microphone=(), camera=()`
    * `Content-Security-Policy: default-src 'self'; ...` (configuré pour autoriser l'affichage propre de Swagger UI tout en protégeant l'application).
* **Preuve par les tests :** `test_security_headers_present_on_endpoints` contrôle la présence effective de ces en-têtes sur l'ensemble des endpoints.

---

### 4.5 Protection Anti-DoS par Dépassement de Capacité
* **Menace :** Saturation mémoire ou disque par soumission de payloads textuels massifs (plusieurs dizaines de mégaoctets).
* **Remédiation :**
  * Bornage strict `max_length=2000` sur les descriptions d'incidents et `max_length=120` sur les noms et villes.
* **Preuve par les tests :** `test_oversized_payload_rejected` valide le rejet immédiat avec code **HTTP 422** en cas de dépassement.

---

## 5. Bilan de la Couverture de Sécurité

La sécurité du projet est validée par **13 tests automatisés directs** intégrés aux **169 tests globaux** :

| # | Test | Fichier | Objectif de sécurité | Résultat |
| :---: | :--- | :--- | :--- | :---: |
| 1 | `test_security_headers_present_on_endpoints` | `tests/security/` | Présence des en-têtes OWASP (`nosniff`, `DENY`, CSP). | **PASSED** |
| 2 | `test_sqli_in_query_parameters_fails_safe[1 OR 1=1]` | `tests/security/` | Typage strict anti-SQLi dans les query params. | **PASSED** |
| 3 | `test_sqli_in_query_parameters_fails_safe[1' OR '1'='1]` | `tests/security/` | Typage strict anti-SQLi dans les query params. | **PASSED** |
| 4 | `test_sqli_in_query_parameters_fails_safe[DROP TABLE]` | `tests/security/` | Typage strict anti-SQLi dans les query params. | **PASSED** |
| 5 | `test_sqli_in_query_parameters_fails_safe[UNION SELECT]` | `tests/security/` | Typage strict anti-SQLi dans les query params. | **PASSED** |
| 6 | `test_sqli_payload_in_text_body_is_safely_parameterized` | `tests/security/` | Paramétrage sécurisé des champs textuels SQL. | **PASSED** |
| 7 | `test_input_sanitizer_unit` | `tests/security/` | Test unitaire de neutralisation des balises HTML et scripts. | **PASSED** |
| 8 | `test_xss_injection_in_incident_description_is_sanitized` | `tests/security/` | Élimination des scripts XSS dans les incidents (Dev 3). | **PASSED** |
| 9 | `test_oversized_payload_rejected` | `tests/security/` | Rejet HTTP 422 des charges surdimensionnées (Anti-DoS). | **PASSED** |
| 10 | `test_unhandled_exception_does_not_leak_system_paths` | `tests/security/` | Masquage des chemins système et stack traces lors d'un crash 500. | **PASSED** |
| 11 | `test_festival_text_fields_are_sanitized` | `tests/integration/` | Assainissement XSS des champs festivals (Dev 2). | **PASSED** |
| 12 | `test_artist_text_fields_are_sanitized` | `tests/integration/` | Assainissement XSS des champs artistes (Dev 2). | **PASSED** |
| 13 | `test_stage_name_is_sanitized` | `tests/integration/` | Assainissement XSS des champs scènes (Dev 2). | **PASSED** |

---

## 6. Synthèse

Le durcissement de sécurité n'est plus limité au seul périmètre initial du Développeur 3 : il s'agit désormais d'une **démarche globale et transversale**, intégrée dans tous les schémas d'entrée des trois développeurs, protégée par l'architecture hexagonale et vérifiée en continu par les 169 tests automatisés du projet.

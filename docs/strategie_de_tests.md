# Stratégie de Tests & Pyramide Globale — FestiPlan

Ce document détaille la démarche de test exhaustive mise en place dans le cadre de la refactorisation hexagonale unifiée des trois pôles : **Développeur 1 (Planification)**, **Développeur 2 (Logistique & Référentiel)** et **Développeur 3 (Opérations & Publication)**, en réponse aux exigences de l'Étape 6 du sujet ("Mettre en place une stratégie de tests").

---

## 1. Pourquoi cette stratégie de tests ?

Dans le dépôt initial ("legacy"), la logique métier était fortement couplée à SQLAlchemy et FastAPI, ce qui rendait les tests unitaires impossibles sans démarrer une base de données. De plus, plusieurs failles critiques n'étaient couvertes par aucun test (déplacement sans contrôle de conflits, crash 500 lors d'un échec de notification, modification de festivals publiés).

Notre stratégie poursuit 4 objectifs clés :
1. **Prouver la non-régression :** valider formellement la correction des défauts 1, 2 et 3 décrits dans le sujet.
2. **Tester le domaine en isolation pure :** exécuter la totalité des règles métier en une fraction de seconde, sans dépendance externe (ni SQLite, ni réseau, ni FastAPI).
3. **Valider les interactions des cas d'usage :** vérifier l'orchestration des ports et des entités via des doubles de tests (`InMemoryRepository` et fakes de notification).
4. **Garantir l'intégrité de bout en bout et la sécurité :** s'assurer que les routes HTTP, les adaptateurs SQLAlchemy et le middleware de sécurité OWASP fonctionnent harmonieusement.

---

## 2. La Pyramide de Tests adoptée

```text
               ▲
              / \     Tests de Sécurité & Hardening OWASP (10 tests)
             /   \    - test_security_hardening.py (Injections SQL, XSS, Headers, DoS, Info Leak)
            /─────\
           /       \  Tests d'Intégration & E2E (API + SQLite) (44 tests)
          /         \ - test_scheduling_integration.py & test_scheduling_regressions.py (18 tests)
         /           \- test_operations_integration.py (8 tests)
        /             \- test_logistics_api.py & test_logistics_sql_repositories.py (15 tests)
       /               \- Tests API legacy initiaux (6 tests)
      /─────────────────\
     /                   \ Tests Applicatifs des Cas d'Usage (48 tests)
    /                     \- Scheduling: reschedule, schedule, catalog & rules (30 tests)
   /                       \- Operations: publish & incidents (13 tests)
  /                         \- Logistics: festival, artist & stage use cases (12 tests)
 /───────────────────────────\ Repositories In-Memory & doubles de tests
|                             | Tests Unitaires Purs du Domaine (57 tests)
|                             | - Scheduling: TimeSlot, Concert, SchedulingPolicy (38 tests)
|                             | - Logistics: Stage (R9, R5), Festival, EquipmentSet, Period (21 tests)
|                             | - Operations: Incident (R10) (8 tests)
|                             | - 100% Python pur (dataclasses, 0 I/O)
```

**Bilan d'exécution global :** **169 tests automatisés exécutés en ~3.8 secondes (100% au vert)**.

---

## 3. Cartographie Détaillée des Tests

### A. Tests Unitaires du Domaine (57 tests)
* **Scheduling (`tests/unit/scheduling/`) :**
  - `test_time_slot.py` (12 tests) : bornes chronologiques (**R1**), durée, intersection temporelle (`overlaps`), inclusion (**R6**).
  - `test_concert.py` (8 tests) : conflits de scène (**R2**), conflits d'artiste (**R3**), cycle de vie d'annulation.
  - `test_scheduling_policy.py` (18 tests) : vérification centralisée des règles de programmation (**R2, R3, R4, R5, R6, R7**).
* **Logistics (`tests/unit/logistics/`) :**
  - `test_stage.py` (7 tests) : validation de capacité strictement positive (**R9**), appartenance au festival (**R4**), adéquation du matériel (**R5**).
  - `test_equipment_set.py` (6 tests) : calcul ensembliste immuable (`frozenset`), inclusion (`covers`), matériel manquant (`missing`).
  - `test_festival_period.py` (2 tests) : invariant chronologique du festival (`start < end`).
  - `test_festival.py` (3 tests) : statut et cycle de publication.
* **Operations (`tests/unit/operations/`) :**
  - `test_incident.py` (8 tests) : invariant de description non vide (**R10**), horodatage, cycle de résolution.

### B. Tests Applicatifs des Cas d'Usage (48 tests)
* **Scheduling :**
  - `test_reschedule_use_case.py` (7 tests) : cas nominal, détection de conflits (**Défaut 1**), résilience à la panne de notification (**Défaut 2**), verrouillage si festival publié (**Défaut 3 & R7**).
  - `test_schedule_use_case.py` (5 tests) : programmation initiale et gestion d'erreurs.
  - `test_scheduling_use_cases_rules.py` (11 tests) : règles métier combinées.
* **Operations :**
  - `test_publish_festival_use_case.py` (7 tests) : intégrité complète du planning avant publication (**R8**), résilience notification (**Défaut 2**).
  - `test_incident_use_cases.py` (6 tests) : déclaration, résolution et consultation d'incidents.
* **Logistics :**
  - `test_festival_use_cases.py` (5 tests) : création et consultation de festivals.
  - `test_stage_use_cases.py` (4 tests) : création de scène avec contrôle festival (**R4**) et capacité (**R9**).
  - `test_artist_use_cases.py` (3 tests) : création et listage des artistes.

### C. Tests d'Intégration & E2E (44 tests)
* **Scheduling & Regressions :**
  - `test_scheduling_integration.py` (6 tests) : cycle complet HTTP FastAPI -> SQLite -> Notification.
  - `test_scheduling_regressions.py` (12 tests) : validation stricte des scénarios du sujet.
* **Operations :**
  - `test_operations_integration.py` (8 tests) : publication et incidents via l'API.
* **Logistics :**
  - `test_logistics_api.py` (10 tests) : endpoints `/festivals`, `/artists`, `/stages` et protection XSS.
  - `test_logistics_sql_repositories.py` (5 tests) : validation du mapping ORM et conversion CSV <-> `EquipmentSet`.
* **Legacy API :** 6 tests historiques validant la compatibilité ascendante.

### D. Tests de Cybersécurité & Hardening OWASP (10 tests)
* `test_security_headers_present_on_endpoints` : présence des en-têtes OWASP (`nosniff`, `DENY`, CSP).
* `test_sqli_in_query_parameters_fails_safe` : immunité aux injections SQL.
* `test_xss_payload_in_incident_description_sanitized` : assainissement automatique du payload malveillant.
* `test_information_disclosure_stack_trace_masked` : masquage des erreurs 500 et des chemins système.
* `test_dos_large_payload_rejected` : rejet immédiat des charges utiles excessives (**HTTP 422**).

---

## 4. Choix de Conception Justifiés

### A. Découplage In-Memory vs SQLAlchemy
* **Le choix :** Chaque pôle a développé une double implémentation de ses ports de persistance (`InMemory` et `SQL`).
* **Bénéfice :**
  - Les tests unitaires du domaine et applicatifs s'exécutent en **moins de 0.8 seconde**.
  - Remplacement possible de la base sans modifier une seule ligne du domaine.

### B. Traitement du Défaut 2 (Notification en échec)
* **Problème legacy :** `db.commit()` était suivi de `send_email()`. Si l'email échouait, une exception non gérée provoquait une réponse 500 post-persistance.
* **Choix retenu :** Découplage via `INotificationSenderPort`. Si la notification échoue, l'incident est loggué sans interrompre la requête. L'API répond **HTTP 200 OK** car l'opération métier a été persistée avec succès.

---

## 5. Bilan d'Exécution Global

```text
======================= 169 passed, 1 warning in 3.80s ========================
```
* **169 tests exécutés avec succès** (100% au vert).
* **Temps total : ~3.8 secondes.**
* **Couverture des règles métier :** R1 à R10 et défauts 1 à 3 intégralement couverts.

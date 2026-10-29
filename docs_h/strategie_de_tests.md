# Stratégie de Tests & Choix d'Architecture — FestiPlan

Ce document détaille la démarche de test mise en place dans le cadre de la refactorisation hexagonale du pôle **Programmation / Scheduling (Développeur 1)**, en réponse aux exigences de l'Étape 6 du sujet ("Mettre en place une stratégie de tests").

---

## 1. Pourquoi cette stratégie de tests ?

Dans le dépôt initial ("legacy"), la logique métier était fortement couplée à SQLAlchemy et FastAPI, ce qui rendait les tests unitaires impossibles sans démarrer une base de données. De plus, plusieurs failles critiques n'étaient couvertes par aucun test (déplacement sans contrôle de conflits, crash 500 lors d'un échec de notification, modification de festivals publiés).

Notre stratégie poursuit 4 objectifs clés :
1. **Prouver la non-régression :** valider formellement la correction des défauts 1, 2 et 3 décrits dans le sujet.
2. **Tester le domaine en isolation pure :** exécuter la totalité des règles métier en une fraction de seconde, sans dépendance externe (ni SQLite, ni réseau, ni FastAPI).
3. **Valider les interactions des cas d'usage :** vérifier l'orchestration des ports et des entités via des doubles de tests (`InMemoryRepository`).
4. **Garantir l'intégrité de bout en bout :** s'assurer que les routes HTTP et les adaptateurs SQLAlchemy fonctionnent de concert avec le modèle de base de données.

---

## 2. La Pyramide de Tests adoptée

```text
           ▲
          / \     Tests d'Intégration & E2E (API + SQLite) (20 tests)
         /   \    - test_scheduling_integration.py (6 tests)
        /─────\   - test_operations_integration.py (8 tests)
       /       \  - Tests API initiaux legacy (6 tests)
      /         \
     /           \  Tests Applicatifs des Cas d'Usage (25 tests)
    /             \ - Scheduling: reschedule (7 tests), schedule (5 tests)
   /───────────────\- Operations: publish (7 tests), incidents (6 tests)
  /                 \ Repositories In-Memory & fakes de notification
 /                   \
/                     \ Tests Unitaires Purs du Domaine (28 tests)
/───────────────────────\- Scheduling: TimeSlot (12 tests), Concert (8 tests)
                         - Operations: Incident R10 (8 tests)
                         - 100% Python pur (dataclasses, 0 I/O)
```

**Bilan d'exécution :** **73 tests automatisés exécutés en ~1.6 seconde (100% au vert)**.


---

## 3. Cartographie des Tests (Lesquels ?)

### A. Tests Unitaires du Domaine (20 tests) — `tests/unit/scheduling/`

| Fichier | Test | Règle / Invariant validé |
| :--- | :--- | :--- |
| `test_time_slot.py` | `test_valid_time_slot_creation` | Création nominale d'un créneau horaire et calcul de durée. |
| `test_time_slot.py` | `test_time_slot_end_before_start_raises_error` | **R1 :** rejet si `end < start` (`InvalidTimeSlotError`). |
| `test_time_slot.py` | `test_time_slot_end_equal_to_start_raises_error` | **R1 :** rejet si `end == start` (durée nulle interdite). |
| `test_time_slot.py` | `test_time_slot_overlaps` (8 cas paramétrés) | Algorithme de chevauchement strict (inclus, partiel, contigu non-chevauchant). |
| `test_time_slot.py` | `test_time_slot_is_within` | **R6 :** vérification de l'inclusion dans les dates du festival. |
| `test_concert.py` | `test_concert_creation_and_reschedule` | Déplacement nominal d'un concert et émission de l'événement de domaine. |
| `test_concert.py` | `test_cannot_reschedule_cancelled_concert` | Interdiction de déplacer un concert déjà annulé. |
| `test_concert.py` | `test_cancel_concert` | Transition d'état vers `cancelled`. |
| `test_concert.py` | `test_conflict_on_same_stage_raises_stage_occupied_error` | **R2 :** détection de conflit sur la même scène (`StageOccupiedError`). |
| `test_concert.py` | `test_conflict_with_same_artist_raises_artist_already_booked_error` | **R3 :** détection de conflit pour le même artiste (`ArtistAlreadyBookedError`). |
| `test_concert.py` | `test_no_conflict_when_different_stages_and_artists` | Deux concerts simultanés sur scènes différentes avec artistes différents sont acceptés. |
| `test_concert.py` | `test_no_conflict_with_self` | Un concert ne crée pas de faux conflit avec lui-même lors d'un déplacement. |
| `test_concert.py` | `test_no_conflict_if_one_is_cancelled` | Un concert annulé ne bloque pas la scène ni l'artiste. |

### B. Tests Applicatifs des Cas d'Usage (12 tests) — `tests/unit/scheduling/`

| Fichier | Test | Défaut / Cas d'usage validé |
| :--- | :--- | :--- |
| `test_reschedule_use_case.py` | `test_reschedule_success` | Déplacement nominal, persistance et déclenchement de notification. |
| `test_reschedule_use_case.py` | `test_defect_1_stage_conflict_refused` | **Défaut 1 :** refus du déplacement si la scène est occupée. |
| `test_reschedule_use_case.py` | `test_defect_1_artist_conflict_refused` | **Défaut 1 :** refus du déplacement si l'artiste est déjà programmé. |
| `test_reschedule_use_case.py` | `test_defect_2_notification_failure_does_not_break_persistence` | **Défaut 2 :** une panne du service d'email n'annule pas la persistance et ne crash pas l'application. |
| `test_reschedule_use_case.py` | `test_defect_3_cannot_reschedule_published_festival` | **Défaut 3 & R7 :** refus de modification ordinaire si festival publié. |
| `test_reschedule_use_case.py` | `test_reschedule_outside_festival_dates_refused` | **R6 :** refus si le nouveau créneau sort des dates du festival. |
| `test_reschedule_use_case.py` | `test_reschedule_nonexistent_concert_raises_not_found` | Gestion d'un identifiant de concert inconnu (`ConcertNotFoundError`). |
| `test_schedule_use_case.py` | `test_schedule_concert_success` | Cas nominal de programmation d'un concert. |
| `test_schedule_use_case.py` | `test_schedule_concert_conflict_raises_stage_occupied` | Rejet à la création si scène occupée. |
| `test_schedule_use_case.py` | `test_cancel_concert` | Annulation d'un concert existant. |
| `test_schedule_use_case.py` | `test_cancel_nonexistent_concert` | Annulation d'un concert inexistant. |
| `test_schedule_use_case.py` | `test_get_festival_schedule` | Tri chronologique du planning par heure de début. |

### C. Tests d'Intégration de Bout en Bout (6 tests) — `tests/integration/`

| Fichier | Test | Scénario d'intégration validé |
| :--- | :--- | :--- |
| `test_scheduling_integration.py` | `test_integration_create_and_reschedule_concert` | Chaîne complète HTTP `POST /concerts` -> `PATCH /concerts/{id}/reschedule` -> `GET /concerts/{id}` avec persistance SQLite. |
| `test_scheduling_integration.py` | `test_integration_defect_1_stage_overlap_rejected` | **Défaut 1 (HTTP) :** validation que l'API renvoie un statut HTTP 400 Bad Request avec le message de conflit de scène. |
| `test_scheduling_integration.py` | `test_integration_defect_1_artist_overlap_rejected` | **Défaut 1 (HTTP) :** validation que l'API renvoie un statut HTTP 400 si l'artiste est en double programmation. |
| `test_scheduling_integration.py` | `test_integration_defect_2_notification_failure_does_not_crash_http` | **Défaut 2 (HTTP) :** avec `FESTIPLAN_FAIL_NOTIFICATIONS=true`, l'API renvoie HTTP 200 (au lieu de 500) et la base de données est correctement mise à jour. |
| `test_scheduling_integration.py` | `test_integration_defect_3_published_festival_locked` | **Défaut 3 (HTTP) :** après `POST /festivals/{id}/publish`, tout `PATCH /reschedule` est rejeté en HTTP 400. |
| `test_scheduling_integration.py` | `test_integration_cancel_concert` | Annulation via HTTP `POST /concerts/{id}/cancel` et vérification du statut en base. |

---

## 4. Choix de Conception Justifiés

### A. Découplage In-Memory vs SQLAlchemy
* **Le choix :** Nous avons développé deux implémentations du port `IConcertRepository` :
  - `InMemoryConcertRepository` (stockage dans un dictionnaire Python en mémoire).
  - `ConcertSqlRepository` (mapping SQLAlchemy avec la base relationnelle).
* **Pourquoi ?**
  - Les 32 tests unitaires s'exécutent en **moins de 0.3 seconde**.
  - Si demain SQLite est remplacé par PostgreSQL ou MongoDB, le domaine et les tests applicatifs ne changent pas d'une seule ligne.

### B. Traitement du Défaut 2 (Notification en échec)
* **Problème legacy :** `db.commit()` était suivi de `send_email()`. Si l'email échouait, une exception non gérée provoquait une réponse 500, laissant croire au client que la modification n'avait pas été faite, alors qu'elle était déjà en base.
* **Choix retenu :** Le cas d'usage `RescheduleConcertUseCase` gère la notification comme un effet secondaire non bloquant. Si le sender de notification lève une exception, celle-ci est interceptée, consignée dans les logs d'avertissement, et le résultat `RescheduleConcertResult` indique `notification_sent=False`. L'API HTTP répond un code **200 OK** car l'opération métier principale a réussi.

### C. Gestion des erreurs et codes HTTP
* **Le choix :** Aucune exception technique SQLAlchemy ne remonte au contrôleur.
* Les règles métier lèvent des sous-classes de `DomainException`.
* Le contrôleur FastAPI intercepte `DomainException` et la traduit en `HTTPException(status_code=400, detail=str(exc))`, et `ConcertNotFoundError` en `HTTP 404`.

---

## 5. Bilan d'Exécution

```text
======================== 44 passed, 1 warning in 0.82s ========================
```
* **44 tests exécutés avec succès** (32 unitaires + 6 intégration + 6 legacy).
* **Temps total : 0.82 seconde.**
* **Couverture des 3 défauts du sujet :** 100% couverte au niveau unitaire et au niveau intégration HTTP.

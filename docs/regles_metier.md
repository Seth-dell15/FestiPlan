# Matrice de Traçabilité des Règles Métier & Défauts — FestiPlan

Ce document récapitule l'état d'implémentation exhaustif des 10 règles métier (**R1 à R10**) et des 3 défauts initiaux du sujet suite à la collaboration et la consolidation des trois pôles : **Développeur 1 (Planification)**, **Développeur 2 (Logistique & Référentiel)** et **Développeur 3 (Opérations & Publication)**.

---

## 1. Tableau Synthétique des Règles Métier (Sujet p. 6)

| Réf. | Règle Métier | Responsable | Statut | Emplacement dans le code | Tests associés |
| :---: | :--- | :---: | :---: | :--- | :--- |
| **R1** | L'heure de fin d'un concert doit être strictement postérieure à son heure de début. | **Dev 1** | **Validé** | `app.domain.value_objects.TimeSlot` | `tests/unit/scheduling/test_time_slot.py` |
| **R2** | Deux concerts ne peuvent pas se chevaucher sur une même scène. | **Dev 1** | **Validé** | `Concert.check_conflict_with` & `SchedulingPolicy.ensure_no_conflict` | `test_concert.py`, `test_reschedule_use_case.py` |
| **R3** | Un artiste ne peut pas jouer dans deux concerts qui se chevauchent, même sur des scènes différentes. | **Dev 1** | **Validé** | `Concert.check_conflict_with` & `SchedulingPolicy.ensure_no_conflict` | `test_concert.py`, `test_reschedule_use_case.py` |
| **R4** | Un concert doit référencer un festival, un artiste et une scène existants. La scène doit appartenir au festival. | **Dev 1 & 2** | **Validé** | `Stage.belongs_to`, `CreateStageUseCase`, `SchedulingPolicy.ensure_stage_can_host` | `test_stage.py`, `test_stage_use_cases.py`, `test_scheduling_use_cases_rules.py` |
| **R5** | Les équipements requis par un artiste doivent être disponibles sur la scène choisie. | **Dev 2** | **Validé** | `Stage.can_host`, `Stage.ensure_can_host`, `EquipmentSet.covers`, `SchedulingPolicy` | `test_stage.py`, `test_equipment_set.py`, `test_scheduling_use_cases_rules.py` |
| **R6** | Un concert doit se dérouler entièrement dans la période du festival. | **Dev 1 & 2** | **Validé** | `TimeSlot.is_within`, `FestivalPeriod`, `SchedulingPolicy.ensure_within_festival` | `test_time_slot.py`, `test_festival_period.py`, `test_reschedule_use_case.py` |
| **R7** | Un planning publié ne doit pas pouvoir être modifié par une opération ordinaire. | **Dev 1** | **Validé** | `SchedulingPolicy.ensure_festival_is_modifiable`, `RescheduleConcertUseCase` | `test_reschedule_use_case.py`, `test_defect_3` |
| **R8** | Un planning ne peut être publié que si ses concerts respectent les règles de programmation. | **Dev 3** | **Validé** | `PublishFestivalUseCase` | `test_publish_festival_use_case.py`, `test_operations_integration.py` |
| **R9** | La capacité d'une scène doit être strictement positive. | **Dev 2** | **Validé** | `Stage.__post_init__` (`InvalidCapacityError`) | `test_stage.py` (`test_stage_capacity_must_be_positive`), `test_logistics_api.py` |
| **R10** | Un incident doit être associé à un concert existant et posséder une description non vide. | **Dev 3** | **Validé** | Entité `Incident` & `DeclareIncidentUseCase` | `test_incident.py`, `test_incident_use_cases.py`, `test_operations_integration.py` |

---

## 2. Détail des Règles Résolues (Pôle Développeur 1 — Planification & Programmation)

### R1 — Chronologie du créneau horaire
* **Invariant garanti :** `TimeSlot.end > TimeSlot.start`.
* **Comportement :** L'Objet-Valeur `TimeSlot` vérifie cet invariant dès l'instanciation (`__post_init__`). Toute tentative de créer un créneau avec `end <= start` lève immédiatement une exception de domaine `InvalidTimeSlotError`.
* **Fichiers :**
  - Code : `app/domain/value_objects/time_slot.py`
  - Exception : `app/domain/exceptions/scheduling_exceptions.py`
  - Tests : `test_time_slot_end_before_start_raises_error`, `test_time_slot_end_equal_to_start_raises_error`

---

### R2 — Non-chevauchement sur une même scène
* **Règle :** Deux concerts programmés sur la même scène et non annulés ne peuvent pas avoir de créneaux qui se recoupent.
* **Comportement :** La méthode `Concert.check_conflict_with` évalue `self.time_slot.overlaps(other.time_slot)`. Si les scènes sont identiques, l'exception `StageOccupiedError` est levée.
* **Fichiers :**
  - Code : `app/domain/models/concert.py`, `app/domain/services/scheduling_policy.py`, `app/application/use_cases/scheduling/reschedule_concert.py`
  - Tests : `test_conflict_on_same_stage_raises_stage_occupied_error`, `test_defect_1_stage_conflict_refused`

---

### R3 — Disponibilité de l'artiste
* **Règle :** Un artiste ne peut pas être sur scène pour deux concerts distincts au même moment.
* **Comportement :** Même si les scènes sont différentes, si `self.artist_id == other.artist_id` et que les créneaux se chevauchent, l'exception `ArtistAlreadyBookedError` est levée.
* **Fichiers :**
  - Code : `app/domain/models/concert.py`, `app/domain/services/scheduling_policy.py`
  - Tests : `test_conflict_with_same_artist_raises_artist_already_booked_error`, `test_defect_1_artist_conflict_refused`

---

### R6 — Respect de la période du festival
* **Règle :** `festival.start_date <= concert.start_time` et `concert.end_time <= festival.end_date`.
* **Comportement :** `TimeSlot.is_within(start_limit, end_limit)` valide l'inclusion complète. Si le créneau déborde, `RescheduleConcertUseCase` et `ScheduleConcertUseCase` lèvent `ConcertOutsideFestivalError`.
* **Fichiers :**
  - Code : `app/domain/value_objects/time_slot.py`, `app/domain/services/scheduling_policy.py`
  - Tests : `test_time_slot_is_within`, `test_reschedule_outside_festival_dates_refused`

---

### R7 — Verrouillage du planning publié
* **Règle :** Une fois le festival publié (`status == "published"`), aucune modification ordinaire du planning n'est permise.
* **Comportement :** Le cas d'usage consulte le statut via le port `IFestivalQueryPort`. Si `is_published == True`, l'exception `CannotModifyPublishedFestivalError` est déclenchée.
* **Fichiers :**
  - Code : `app/application/use_cases/scheduling/reschedule_concert.py`, `app/domain/services/scheduling_policy.py`
  - Tests : `test_defect_3_cannot_reschedule_published_festival`

---

## 3. Détail des Règles Résolues (Pôle Développeur 2 — Référentiel & Logistique)

### R4 — Appartenance de la scène au festival
* **Règle :** Une scène doit obligatoirement être rattachée à un festival existant et valide.
* **Comportement :** `CreateStageUseCase` vérifie l'existence du festival via `IFestivalRepository` (**HTTP 404** si absent). La méthode métier `Stage.belongs_to(festival_id)` permet de valider l'appartenance lors de la planification d'un concert (`SchedulingPolicy.ensure_stage_can_host`).
* **Fichiers :**
  - Entité : `app/domain/models/stage.py`
  - Cas d'usage : `app/application/use_cases/logistics/create_stage.py`
  - Tests : `test_stage_use_cases.py`, `test_scheduling_use_cases_rules.py`

---

### R5 — Adéquation des équipements requis par l'artiste
* **Règle :** Les équipements requis par un artiste doivent être disponibles sur la scène choisie.
* **Comportement :** L'Objet-Valeur `EquipmentSet` compare les ensembles via `covers()` et `missing()`. L'entité `Stage` fournit `can_host(artist)` et `ensure_can_host(artist)` qui lève `EquipmentMismatchError` en cas de matériel manquant. La politique de programmation `SchedulingPolicy.ensure_stage_can_host` utilise cette validation avant toute réservation.
* **Fichiers :**
  - Value Object : `app/domain/value_objects/equipment_set.py`
  - Entité : `app/domain/models/stage.py`
  - Exception : `app/domain/exceptions/logistics_exceptions.py`
  - Tests : `test_stage.py` (`test_stage_can_host_artist`, `test_stage_ensure_can_host_raises_when_missing_equipment`), `test_equipment_set.py`

---

### R9 — Capacité d'une scène strictement positive
* **Règle :** La capacité d'accueil d'une scène doit être un entier strictement supérieur à 0.
* **Comportement :** L'entité `Stage` applique cet invariant directement dans son constructeur (`__post_init__`). Toute instanciation avec une capacité $\le 0$ déclenche immédiatement `InvalidCapacityError` (**HTTP 400**), protégeant le cœur de domaine même hors contexte HTTP.
* **Fichiers :**
  - Entité : `app/domain/models/stage.py`
  - Exception : `app/domain/exceptions/logistics_exceptions.py`
  - Tests : `test_stage.py` (`test_stage_capacity_must_be_positive`), `test_stage_use_cases.py`, `test_logistics_api.py`

---

## 4. Détail des Règles Résolues (Pôle Développeur 3 — Opérations & Publication)

### R8 — Validation de l'intégrité avant publication
* **Règle :** Un planning ne peut être publié que si ses concerts respectent l'ensemble des règles de programmation.
* **Comportement :** `PublishFestivalUseCase` passe en revue tous les concerts actifs du festival :
  - Il vérifie l'absence de chevauchement sur une même scène (**R2**) et l'absence de conflit d'artiste (**R3**).
  - Il vérifie que chaque concert se déroule strictement dans la période du festival (**R6**).
  - En cas de conflit, `CannotPublishInvalidScheduleError` est levée et la publication est refusée (**HTTP 400**).
* **Fichiers :**
  - Cas d'usage : `app/application/use_cases/operations/publish_festival.py`
  - Port : `app/domain/ports/repositories/festival_repository_port.py` (`IFestivalCommandPort`)
  - Tests : `test_publish_with_stage_conflict_raises_r8_error`, `test_publish_with_artist_conflict_raises_r8_error`, `test_api_publish_with_schedule_conflict_refused_r8`

---

### R10 — Invariants de signalement d'incident
* **Règle :** Un incident doit être rattaché à un concert existant et comporter une description non vide.
* **Comportement :** L'entité `Incident` applique cette règle dès son instanciation (`__post_init__`). Une description vide ou composée uniquement d'espaces lève `IncidentInvalidDescriptionError` (**HTTP 400**). Le cas d'usage `DeclareIncidentUseCase` vérifie l'existence du concert via `IConcertRepository` (**HTTP 404** si absent).
* **Fichiers :**
  - Entité : `app/domain/models/incident.py`
  - Cas d'usage : `app/application/use_cases/operations/declare_incident.py`, `resolve_incident.py`, `list_incidents.py`
  - Port & Repo : `app/domain/ports/repositories/incident_repository_port.py`, `IncidentSqlRepository`
  - Tests : `test_empty_description_raises_r10_error`, `test_api_create_incident_nominal`, `test_api_list_and_resolve_incident`

---

## 5. État de Résolution des 3 Défauts Initiaux du Sujet

| Défaut Initial | Problématique Legacy | Solution Hexagonale / DDD | Statut |
| :--- | :--- | :--- | :---: |
| **Défaut 1 — Chevauchement lors du déplacement** | `reschedule_concert` ne vérifiait aucun conflit ni disponibilité. | Orchestration de `candidate_concert.check_conflict_with(other)` sur tous les concerts actifs dans `RescheduleConcertUseCase` et `SchedulingPolicy`. | **Résolu & Testé** |
| **Défaut 2 — Panne notification après commit (Erreur 500)** | Commit SQL direct suivi d'un appel mail bloquant menant à 500 post-persistance. | Découplage via `INotificationSenderPort` dans `RescheduleConcertUseCase` et `PublishFestivalUseCase`. L'échec d'envoi est intercepté et consigné sans corrompre ni faire échouer l'opération métier persistée. | **Résolu & Testé** |
| **Défaut 3 — Déplacement sur festival publié** | Aucun contrôle d'état lors du déplacement. | Vérification de `is_published` via `IFestivalQueryPort` bloquant toute altération ordinaire. | **Résolu & Testé** |

---

## 6. Synthèse Globale

Toutes les exigences métier initiales sont désormais couvertes :
* **10/10 règles métier (R1 à R10)** validées, vérifiées dans le cœur de domaine DDD et testées en isolation pure.
* **3/3 défauts legacy** éradiqués et garantis par des tests de non-régression.
* **169 tests automatisés** exécutés avec succès sur l'ensemble de la pyramide de tests.

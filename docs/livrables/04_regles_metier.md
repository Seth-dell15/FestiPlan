# Traçabilité des règles métier — FestiPlan

Ce document indique où chaque règle du sujet est garantie et quels tests la protègent.

## Sommaire

- R1 : fin strictement après le début
- R2 : pas de chevauchement sur une scène
- R3 : pas de chevauchement pour un artiste
- R4 : références existantes et scène du festival
- R5 : équipements disponibles
- R6 : concert dans la période du festival
- R7 : planning publié protégé
- R8 : publication d'un planning valide
- R9 : capacité et durées positives
- R10 : incident valide
- Défauts 1 à 3

### R1 : fin strictement après le début

- **Où** : `TimeSlot.__post_init__`
- **Refus** : `InvalidTimeSlotError`, HTTP 400
- **Tests** : `test_time_slot_end_before_start_raises_error`, `test_time_slot_end_equal_to_start_raises_error`

### R2 : pas de chevauchement sur une scène

- **Où** : `Concert.check_conflict_with`, appelée par `scheduling_policy.ensure_no_conflict`
- **Refus** : `StageOccupiedError`, HTTP 409
- **Tests** : `test_conflict_on_same_stage_raises_stage_occupied_error`, `test_defect_1_stage_conflict_refused`, `test_integration_defect_1_stage_overlap_rejected`

### R3 : pas de chevauchement pour un artiste

- **Où** : `Concert.check_conflict_with`, avec les concerts du festival et ceux de l'artiste
- **Refus** : `ArtistAlreadyBookedError`, HTTP 409
- **Portée** : la règle s'applique aussi entre festivals
- **Tests** : `test_conflict_with_same_artist_raises_artist_already_booked_error`, `test_defect_1_artist_conflict_refused`, `test_r3_artist_cannot_play_in_two_festivals_at_the_same_time`

### R4 : références existantes et scène du festival

- **Où** : existence vérifiée par `ScheduleConcertUseCase`, appartenance par `scheduling_policy.ensure_stage_can_host` et `Stage.belongs_to`
- **Refus** : HTTP 404 pour une référence absente, HTTP 400 pour une scène d'un autre festival
- **Tests** : `test_belongs_to_its_festival_only`, `test_r4_stage_of_another_festival_is_rejected`, `test_r4_unknown_reference_is_rejected`

### R5 : équipements disponibles

- **Où** : `Stage.ensure_can_host` et `EquipmentSet.missing`
- **Refus** : `EquipmentMismatchError`, HTTP 400
- **Tests** : `test_cannot_host_artist_when_equipment_is_missing`, `test_r5_missing_equipment_is_listed`, `test_r5_stage_without_required_equipment_is_rejected`

### R6 : concert dans la période du festival

- **Où** : `scheduling_policy.ensure_within_festival` et `TimeSlot.is_within`
- **Refus** : `ConcertOutsideFestivalError`, HTTP 400
- **Tests** : `test_time_slot_is_within`, `test_r6_slot_outside_festival_is_rejected`, `test_reschedule_outside_festival_dates_refused`

### R7 : planning publié protégé

- **Où** : `scheduling_policy.ensure_festival_is_modifiable`, appelée pour programmer, déplacer et annuler
- **Refus** : `CannotModifyPublishedFestivalError`, HTTP 409
- **Procédure explicite** : `Festival.unpublish()` et `POST /festivals/{id}/unpublish`
- **Tests** : `test_r7_published_festival_is_locked`, `test_defect_3_cannot_reschedule_published_festival`, `test_r7_cancel_is_rejected_once_festival_is_published`, `test_api_unpublish_allows_modification_then_republication`

### R8 : publication d'un planning valide

- **Où** : `scheduling_policy.ensure_publishable`, appelée par `PublishFestivalUseCase` avant `Festival.publish()`
- **Contrôles** : planning non vide, R2 à R6, et R3 entre festivals
- **Refus** : `CannotPublishInvalidScheduleError`, HTTP 400
- **Tests** : `test_empty_schedule_is_not_publishable`, `test_conflict_inside_the_festival_is_not_publishable`, `test_artist_booked_in_another_festival_is_not_publishable`, `test_api_publish_with_schedule_conflict_refused_r8`

### R9 : capacité et durées positives

- **Où** : `Stage.__post_init__` pour la capacité, `TimeSlot` pour la durée d'un concert
- **Refus** : `InvalidCapacityError`, HTTP 400
- **Tests** : `test_capacity_must_be_strictly_positive`, `test_time_slot_end_equal_to_start_raises_error`

### R10 : incident valide

- **Où** : `Incident.__post_init__` pour la description, `DeclareIncidentUseCase` pour l'existence du concert
- **Refus** : HTTP 422 si Pydantic rejette le format, HTTP 400 pour le domaine, HTTP 404 si le concert est absent
- **Tests** : `test_empty_description_raises_r10_error`, `test_invalid_concert_id_raises_error`, `test_api_create_incident_nominal`

### Défauts 1 à 3

- **Défaut 1** : déplacement soumis à R2, R3, R6 et R7
- **Défaut 2** : réponse 200 avec `notification_sent: false` si la notification échoue
- **Défaut 3** : refus 409 après publication, dépublication explicite pour rouvrir le planning
- **Preuve** : voir [05_reproduction_defauts.md](05_reproduction_defauts.md)

# Stratégie de tests — FestiPlan

La suite vérifie d'abord les règles métier sans technologie, puis l'orchestration avec des doubles de test, et enfin l'assemblage réel avec HTTP et SQLite.

Résultat au moment de la rédaction : **257 tests passent**, avec `python -m pytest`.

## Répartition

| Niveau | Tests | Dépendances |
|---|---:|---|
| Domaine | 92 | Python seul |
| Cas d'usage | 63 | Doubles de test |
| Sens des dépendances | 4 | Analyse du code |
| Adaptateurs | 54 | FastAPI, SQLite |
| Non-régression | 19 | FastAPI, SQLite |
| Sécurité | 19 | FastAPI, SQLite |
| API initiale | 6 | FastAPI, SQLite |
| **Total** | **257** | |

## Domaine (92 tests)

Ces tests ne démarrent ni FastAPI ni SQLite : le `conftest.py` ne charge ces technologies que pour les tests qui demandent le fixture `client`.

- [tests/unit/scheduling](../../tests/unit/scheduling) : `test_schedule.py` (30), `test_time_slot.py` (12), `test_concert.py` (12), `test_schedule_publishable.py` (7).
- [tests/unit/logistics](../../tests/unit/logistics) : `test_festival.py` (8), `test_stage.py` (7), `test_equipment_set.py` (3), `test_festival_period.py` (4).
- [tests/unit/operations](../../tests/unit/operations) : `test_incident.py` (9).

Ils couvrent les créneaux invalides, les chevauchements, les invariants et les transitions d'état. `test_schedule.py` vérifie l'agrégat du planning : chaque règle refusée laisse le planning inchangé.

## Cas d'usage (63 tests)

Ces tests utilisent des repositories en mémoire et des fausses notifications.

- **Planification** : `test_scheduling_use_cases_rules.py` (15), `test_reschedule_use_case.py` (7), `test_schedule_use_case.py` (5).
- **Opérations** : `test_publish_festival_use_case.py` (14), `test_incident_use_cases.py` (6), `test_unpublish_festival_use_case.py` (4).
- **Référentiel** : `test_festival_use_cases.py` (5), `test_stage_use_cases.py` (4), `test_artist_use_cases.py` (3).

Ils vérifient les décisions métier, les erreurs et les appels aux ports, notamment l'absence de notification après un refus.

## Sens des dépendances (4 tests)

[test_architecture.py](../../tests/unit/test_architecture.py) analyse les imports. Le domaine et l'application ne peuvent pas importer de framework ni d'adaptateur, et les adaptateurs entrants ne peuvent pas importer SQLAlchemy ni les adaptateurs sortants.

## Adaptateurs (54 tests)

- **Routes HTTP** : `test_logistics_api.py` (14), `test_operations_integration.py` (12), `test_inbound_ports.py` (7).
- **Persistance SQLite** : `test_concert_incident_sql_repositories.py` (10), `test_logistics_sql_repositories.py` (8).
- **Notification** : `test_email_notification_adapter.py` (3).

## Non-régression (19 tests)

- [test_scheduling_integration.py](../../tests/integration/test_scheduling_integration.py) (6) : parcours HTTP, dont les trois défauts du sujet.
- [test_scheduling_regressions.py](../../tests/integration/test_scheduling_regressions.py) (13) : erreurs corrigées pendant la refactorisation, comme une scène d'un autre festival, un concert annulé ou un fuseau horaire.

Les 4 tests HTTP des défauts échouent sur le code initial et passent sur le code livré. La comparaison est décrite dans [05_reproduction_defauts.md](05_reproduction_defauts.md).

## Autres tests

- [tests/security](../../tests/security) (19) : en-têtes HTTP, injections, XSS, charges trop volumineuses, identifiants hors limites et masquage des erreurs.
- `tests/test_*_api.py`, `test_publication.py` et `test_scheduling.py` (6) : tests fournis avec le projet initial, conservés pour vérifier le comportement de départ.

## Choix retenus

- **Doubles en mémoire plutôt que mocks** : ils exécutent réellement les contrats des ports et rendent les tests lisibles.
- **Base SQLite dans les tests d'adaptateurs** : le mapping entre entités et tables doit être vérifié avec une vraie base.
- **Couverture ciblée** : la priorité porte sur les règles métier, les erreurs et les défauts, pas sur chaque ligne de code.

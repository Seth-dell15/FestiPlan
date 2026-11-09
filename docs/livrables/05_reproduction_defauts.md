# Reproduction des trois défauts

Ce document montre le comportement des défauts sur le code initial (commit `3a5aa55`) et sur le code livré. Tous les résultats ci-dessous ont été obtenus en exécutant les deux versions sur le jeu de données de démonstration.

## Sommaire

1. Rejouer le code initial
2. Défaut 1 : conflits de programmation
3. Défaut 2 : notification en échec
4. Défaut 3 : planning publié
5. Preuve par les tests

## 1. Rejouer le code initial

Depuis la racine du dépôt, créez une copie isolée du code initial :

```powershell
git worktree add ..\festiplan-initial 3a5aa55
cd ..\festiplan-initial
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

Utilisez ensuite Swagger sur `http://127.0.0.1:8000/docs`. Relancez `python -m app.seed` avant chaque scénario pour repartir du même planning. Une fois terminé, revenez dans le dépôt puis supprimez la copie avec `git worktree remove --force ..\festiplan-initial`.

## 2. Défaut 1 : conflits de programmation

### Chevauchement sur une scène

**Requête.** Le concert 2 est déplacé pendant le concert 1, qui occupe Mainstage de 18:00 à 19:00.

```http
PATCH /concerts/2/reschedule
{"start_time": "2027-06-18T18:30:00", "end_time": "2027-06-18T19:30:00"}
```

- **Code initial** : 200, le concert est déplacé et chevauche le concert 1.
- **Code livré** : 409, `Conflit de scène`, et le concert reste à 19:30-20:30.

### Artiste sur deux scènes

**Requêtes.** L'artiste 2 joue sur Mainstage de 19:30 à 20:30. Un second concert est créé sur Warzone, puis déplacé sur ce créneau.

```http
POST /concerts
{"festival_id": 1, "artist_id": 2, "stage_id": 2, "start_time": "2027-06-19T10:00:00", "end_time": "2027-06-19T11:00:00"}

PATCH /concerts/15/reschedule
{"start_time": "2027-06-18T19:45:00", "end_time": "2027-06-18T20:15:00"}
```

- **Code initial** : 201 puis 200, l'artiste joue sur deux scènes en même temps.
- **Code livré** : 201 puis 409, `Conflit d'artiste`.

### Déplacement valide

**Requête.** Le concert 1 est déplacé sur un créneau libre.

```http
PATCH /concerts/1/reschedule
{"start_time": "2027-06-18T14:00:00", "end_time": "2027-06-18T15:00:00"}
```

- **Code initial** : 200.
- **Code livré** : 200, avec `notification_sent: true`.

## 3. Défaut 2 : notification en échec

**Préparation.** Avant de lancer l'API, activez la panne simulée :

```powershell
$env:FESTIPLAN_FAIL_NOTIFICATIONS="true"
```

**Requête.** Rejouez le déplacement valide du concert 1, puis relisez `GET /concerts?festival_id=1`.

- **Code initial** : 500, `Simulation : le service de notification est indisponible`, alors que le concert est bien passé à 14:00-15:00.
- **Code livré** : 200, `notification_sent: false`, et le concert est passé à 14:00-15:00.

## 4. Défaut 3 : planning publié

**Requêtes.** Publiez le festival, puis rejouez le déplacement valide du concert 1.

```http
POST /festivals/1/publish
PATCH /concerts/1/reschedule
{"start_time": "2027-06-18T14:00:00", "end_time": "2027-06-18T15:00:00"}
```

- **Code initial** : 200 puis 200, le planning publié est modifié.
- **Code livré** : 200 puis 409, et le concert reste à 18:00-19:00.

Pour modifier ce planning sur le code livré, appelez d'abord `POST /festivals/1/unpublish`. Le déplacement est alors accepté, et une nouvelle publication repasse par les contrôles de R8.

## 5. Preuve par les tests

Les tests HTTP de [test_scheduling_integration.py](../../tests/integration/test_scheduling_integration.py) ont été exécutés sur les deux versions. Ils passent uniquement par l'API, donc ils s'exécutent aussi sur le code initial.

| Test | Code initial | Code livré |
|---|---|---|
| `test_integration_defect_1_stage_overlap_rejected` | Échec | Succès |
| `test_integration_defect_1_artist_overlap_rejected` | Échec | Succès |
| `test_integration_defect_2_notification_failure_does_not_crash_http` | Échec | Succès |
| `test_integration_defect_3_published_festival_locked` | Échec | Succès |

Pour rejouer cette comparaison dans la copie du code initial :

```powershell
Copy-Item ..\FestiPlan\tests\integration\test_scheduling_integration.py tests\test_defects_regression.py
python -m pytest tests/test_defects_regression.py -k integration_defect
```

Adaptez `..\FestiPlan` au nom de votre dossier. Les mêmes défauts sont aussi couverts sans HTTP dans [test_reschedule_use_case.py](../../tests/unit/scheduling/test_reschedule_use_case.py), à l'aide de doubles de test.

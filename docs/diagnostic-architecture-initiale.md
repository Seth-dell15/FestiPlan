# Diagnostic de l'architecture initiale

Ce diagnostic porte sur le dépôt de départ (commit `3a5aa55`), avant toute refactorisation. Il s'appuie uniquement sur le code et sur le `README.md`. Le schéma qui l'accompagne est [architecture-initiale.drawio](architecture-initiale.drawio) : les repères ①, ② et ③ ci-dessous renvoient à ses flèches rouges.

## Sommaire

1. Responsabilités de chaque partie du code
2. Dépendances entre routes, services, modèles et données
3. Emplacement des règles métier
4. Dépendances directes à FastAPI et SQLAlchemy
5. Testabilité et risques d'incohérence
6. Exemple concret : le déplacement d'un concert
7. En résumé

## 1. Responsabilités de chaque partie du code

### `main.py`

- **Rôle** : crée l'application FastAPI et monte les cinq routers.
- **Constat** : appelle `Base.metadata.create_all()` dès l'import du module, donc importer l'application crée les tables.

### Routes (`app/api/`)

- **Rôle** : recevoir la requête HTTP, valider le corps avec Pydantic (`schemas.py`), appeler un service, traduire les exceptions en codes 400, 404 ou 500.
- **Constat** : elles en font plus. `concerts.py` et `incidents.py` interrogent la base eux-mêmes, et `artists.py` et `stages.py` reconvertissent le texte CSV des équipements en liste (fonction `out()`).

### Services (`app/services/`)

- **Rôle** : porter la logique métier (festivals, artistes, scènes, planning, publication).
- **Constat** : la qualité varie d'un service à l'autre. `festival_service` et `artist_service` délèguent proprement à leur repository. `scheduling_service`, `publication_service` et `stage_service` font une partie de leurs requêtes eux-mêmes. Il n'existe aucun service pour les incidents.

### Repositories (`app/repositories/`)

- **Rôle** : lire et écrire une entité (`get`, `list`, `create`).
- **Constat** : chaque `create()` fait lui-même `db.commit()`. Il n'y a ni repository pour les incidents, ni méthode de mise à jour : les modifications passent directement par la Session dans les services.

### Modèles et base (`models.py`, `database.py`)

- **Rôle** : modèles ORM SQLAlchemy, moteur, `SessionLocal` et `get_db()`.
- **Constat** : ces modèles ORM servent aussi d'objets métier. Les équipements y sont stockés en texte séparé par des virgules et les statuts en chaînes libres (`"preparation"`, `"published"`, `"scheduled"`, `"cancelled"`).

### Notification et configuration (`notification_service.py`, `utils/`, `config.py`)

- **Rôle** : `notification_service` appelle `email_sender`, qui simule l'envoi et lève une `RuntimeError` si `FESTIPLAN_FAIL_NOTIFICATIONS=true`. `config.py` expose un objet `settings` global.
- **Constat** : `email_sender` lit directement ce `settings` global ; son comportement dépend donc d'une variable d'environnement, sans paramètre visible.

## 2. Dépendances entre routes, services, modèles et données

**Chemin attendu.** Route → service → repository → modèle ORM → SQLite. Les festivals, artistes et scènes le suivent à peu près.

**Écarts observés.** Trois raccourcis contournent ce chemin :

- ① **La route interroge la base** : `concerts.py:18` et `:33` (`db.query(Concert)`), et tout `incidents.py` (lignes 11 à 23), qui lit, crée et enregistre sans service.
- ② **Le service interroge la base sans repository** : `scheduling_service.py:15` et `:26-28`, `publication_service.py:9`, `stage_service.py:12`.
- ③ **Le service déclenche un effet de bord en dur** : `scheduling_service` et `publication_service` créent eux-mêmes un `NotificationService()`, qui appelle `email_sender`, qui lit `settings`.

**Couplage aux modèles ORM.** Tous les services importent `app.models` et construisent eux-mêmes les objets ORM (`Artist(...)`, `Festival(...)`, `Concert(...)`). Il n'existe aucune représentation métier indépendante de la base.

## 3. Emplacement des règles métier

Les règles sont réparties sur trois couches, sans endroit unique où les lire.

**Dans Pydantic (`schemas.py`) :**

- longueurs minimales et maximales des noms ;
- capacité d'une scène strictement positive, vérifiée seulement ici.

**Dans les routes :**

- `incidents.py:11` : un incident doit viser un concert existant ;
- `concerts.py:36` : la fin d'un déplacement doit être après le début, contrôle refait ensuite dans le service.

**Dans les services :**

- `festival_service.py:13` : un festival doit finir après avoir commencé ;
- `stage_service.py:12` : une scène se crée dans un festival existant ;
- `scheduling_service.create_concert` (lignes 26 à 41) : festival, artiste et scène existants, scène du bon festival, fin après début, concert pendant le festival, pas de conflit de scène ni d'artiste, équipements requis disponibles sur la scène ;
- `scheduling_service.reschedule_concert` : seulement fin après début ;
- `scheduling_service.cancel_concert` et `publication_service.publish` : aucune règle.

**Dans un repository :**

- `concert_repository.py:12` : les concerts annulés sont exclus du planning.

**Code mort.** `festival_service.publish()` (lignes 17 à 21) publie aussi un festival, mais aucune route ne l'appelle : la route `/publish` utilise `publication_service`.

## 4. Dépendances directes à FastAPI et SQLAlchemy

### FastAPI

- **Où** : uniquement `app/api/*.py` et `main.py` (`APIRouter`, `Depends`, `HTTPException`).
- **Constat** : les services n'importent pas FastAPI, mais ils communiquent avec les routes par des exceptions génériques. Une `ValueError` devient 400 et une `RuntimeError` devient 500. Une panne de notification ressort donc comme une erreur serveur.

### SQLAlchemy

- **Où** : routes, services, repositories, `models.py`, `database.py`.
- **Constat** : la `Session` créée par `get_db()` est injectée dans la route par `Depends`, puis transmise au service, puis au repository. Toutes les couches manipulent la même Session et les mêmes modèles ORM. Aucune règle métier n'existe en Python pur, indépendante de la base.

## 5. Testabilité et risques d'incohérence

### Testabilité

- **Pas d'injection** : chaque service crée lui-même son repository et son service de notification dans son constructeur (`scheduling_service.py:9`, `publication_service.py:6`). On ne peut pas leur passer un faux.
- **Base obligatoire** : les règles lisent la Session SQLAlchemy, donc tester une règle de planning demande une vraie base SQLite remplie.
- **Panne non simulable proprement** : pour faire échouer la notification, il faut modifier l'objet `settings` global.
- **Effets à l'import** : importer `app.main` crée les tables.
- **Tests existants** : six tests, tous lancés à travers l'API complète (`TestClient`, `conftest.py`). Ils couvrent des validations simples (dates, capacité, nom, publication d'un festival inconnu) ; aucun ne couvre les trois scénarios du README.

### Risques d'incohérence

- **Enregistrements dispersés** : `db.commit()` est appelé dans une route (`incidents.py:16`), dans deux services (`scheduling_service.py:52` et `:61`, `publication_service.py:13`) et dans chaque `create()` de repository. Aucune couche ne décide seule de la fin d'une opération.
- **Notification après enregistrement** : si l'envoi échoue, la donnée est déjà en base mais l'API répond 500 (scénario 2 du README).
- **Règles divergentes** : la création d'un concert vérifie tout, le déplacement presque rien (scénario 1).
- **Statut publié ignoré** : aucun code ne lit `status == "published"` avant de modifier un concert (scénario 3).
- **Deux méthodes de publication** : `festival_service.publish()` et `publication_service.publish()`.
- **Statuts en chaînes libres** : une faute de frappe sur `"cancelled"` ou `"published"` passe sans erreur.

## 6. Exemple concret : le déplacement d'un concert

**Où.** `PATCH /concerts/{id}/reschedule`, dans `app/api/concerts.py:30-43` et `app/services/scheduling_service.py:44-55`.

**Ce que fait le code.**

```python
# Route : accès direct à la base et règle métier dans le contrôleur
concert = db.query(Concert).filter(Concert.id == concert_id).first()
if payload.end_time <= payload.start_time:
    raise HTTPException(status_code=400, ...)

# Service : seule règle vérifiée, puis enregistrement, puis notification
if payload.end_time <= payload.start_time:
    raise ValueError(...)
concert.start_time = payload.start_time; concert.end_time = payload.end_time
self.db.commit()
self.notifications.notify_schedule_change(...)
```

**Responsabilités mal placées.** La route fait une requête SQL et contrôle une règle métier, ce qui est le rôle du service. Le service, lui, oublie les règles qu'il applique pourtant à la création : conflits de scène et d'artiste, dates du festival, équipements, statut publié.

**Dépendance problématique.** Le service enregistre en base, puis appelle une notification qu'il a créée lui-même. Quand la notification échoue, la `RuntimeError` remonte, la route renvoie 500, mais le déplacement est déjà enregistré.

**Conséquence.** Ce seul parcours réunit les trois scénarios du README : un concert peut être déplacé sur un créneau occupé, dans un festival déjà publié, et le client reçoit une erreur alors que la modification est faite. Il est en plus impossible à tester sans base ni vraie notification.

## 7. En résumé

Les règles métier sont dispersées entre Pydantic, les routes, les services et un repository. SQLAlchemy traverse toutes les couches et ses modèles servent d'objets métier. Les effets de bord, la notification et les enregistrements en base, ne sont pas isolés. La refactorisation devra regrouper les règles dans un domaine indépendant, faire passer tout accès aux données par des ports, et décider en un seul endroit du moment où une opération est enregistrée et notifiée.

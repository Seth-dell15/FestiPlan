# FestiPlan — API de Gestion de Festival (Architecture Hexagonale)

API FastAPI de gestion de festival de musique (*Hellforge Open Air*), refactorisée selon les principes de l'**Architecture Hexagonale (Ports & Adapters)** et du **Domain-Driven Design (DDD)**.

---

## 1. Fonctionnalités & Domaine Métier

* **Festivals :** Création, consultation, cycle de vie et publication du planning.
* **Artistes & Scènes :** Enregistrement des groupes et de leurs besoins techniques, gestion des capacités et équipements des scènes.
* **Programmation des Concerts (`Scheduling`) :**
  * Création de concerts avec contrôle strict de non-chevauchement (**R2, R3**) et respect des dates du festival (**R6**).
  * Déplacement de concerts (`reschedule`) avec protection contre les conflits de scène et d'artiste.
  * Verrouillage des modifications si le festival est déjà publié (**R7**).
  * Découplage de la notification (une panne réseau n'annule pas la persistance et ne crash pas l'API).
* **Incidents :** Déclaration et suivi des incidents techniques en cours de concert.

---

## 2. Organisation de l'Architecture

Le code sépare rigoureusement la logique métier pure des mécanismes techniques :

```text
app/
├── domain/                         # Cœur Métier 100% Python pur (0 dépendance framework/DB)
│   ├── models/                     # Entités DDD (Concert, etc.)
│   ├── value_objects/              # Objets-Valeurs immuables (TimeSlot, etc.)
│   ├── exceptions/                 # Exceptions métier explicites (StageOccupiedError...)
│   ├── events/                     # Événements de domaine (ConcertRescheduledEvent)
│   └── ports/                      # Interfaces abstraites (IConcertRepository, IFestivalQueryPort...)
├── application/                    # Cas d'usage applicatifs (Use Cases)
│   └── use_cases/scheduling/       # RescheduleConcertUseCase, ScheduleConcertUseCase...
└── adapters/                       # Adaptateurs d'infrastructure
    ├── primary/api/                # Contrôleurs HTTP FastAPI & Schemas Pydantic
    └── secondary/                  # Repositories SQLAlchemy, InMemory & Adaptateurs Mail
```

---

## 3. Installation et Démarrage rapide

### Prérequis
* Python 3.11+
* SQLite3

### Installation

```bash
# 1. Créer et activer l'environnement virtuel
python -m venv .venv
# Sous Windows PowerShell :
.venv\Scripts\Activate.ps1
# Sous macOS / Linux :
source .venv/bin/activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Initialiser la base de données SQLite avec le jeu de données démo
python -m app.seed
```

### Lancement de l'API

```bash
uvicorn app.main:app --reload
```

* **API Swagger interactive :** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Healthcheck :** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 4. Exécution des Tests

Le projet intègre une suite complète de **83 tests automatisés** (unitaires purs, applicatifs, intégration réelle et sécurité OWASP) exécutables en moins de 2 secondes :

```bash
# Exécution de toute la suite de tests
python -m pytest

# Exécution avec détails verbeux
python -m pytest -v

# Exécution de la suite de sécurité (Injections SQL, XSS, En-têtes, DoS, Info Leak)
python -m pytest tests/security/

# Exécution ciblée des tests unitaires du domaine
python -m pytest tests/unit/

# Exécution des tests d'intégration avec l'API
python -m pytest tests/integration/
```

---

## 5. Comment tester les scénarios clés manuellement

Vous pouvez tester l'application directement depuis Swagger ([http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)) :

### Scénario 1 : Déplacement nominal d'un concert
1. Exécutez `GET /concerts?festival_id=1` pour visualiser les concerts seedés.
2. Déplacez le concert n°1 via `PATCH /concerts/1/reschedule` avec le JSON :
   ```json
   {
     "start_time": "2027-06-18T14:00:00",
     "end_time": "2027-06-18T15:00:00"
   }
   ```
3. L'API renvoie **HTTP 200 OK** et la date est mise à jour.

### Scénario 2 : Protection contre les conflits de programmation (Défaut 1 résolu)
* **Conflit de scène (R2) :** Tentez de déplacer un concert sur le créneau d'un autre concert de la même scène (ex: 18h30 à 19h30 sur Mainstage) ➔ L'API renvoie **HTTP 400 Bad Request** (`"Conflit de scène"`).
* **Conflit d'artiste (R3) :** Tentez de déplacer un concert pour faire jouer un artiste sur deux scènes différentes en même temps ➔ L'API renvoie **HTTP 400 Bad Request** (`"Conflit d'artiste"`).

### Scénario 3 : Résistance aux pannes de notification (Défaut 2 résolu)
1. Activez la simulation de panne de notification dans votre fichier `.env` ou console :
   ```bash
   $env:FESTIPLAN_FAIL_NOTIFICATIONS="true"
   ```
2. Déplacez un concert via `PATCH /concerts/1/reschedule` ou publiez un festival via `POST /festivals/1/publish`.
3. Contrairement au code legacy qui crashait en HTTP 500, l'API renvoie **HTTP 200 OK** et la persistance est préservée.

### Scénario 4 : Verrouillage du festival publié (Défaut 3 résolu)
1. Publiez le festival via `POST /festivals/1/publish`.
2. Tentez ensuite de déplacer un concert via `PATCH /concerts/1/reschedule`.
3. L'API refuse la modification et renvoie **HTTP 400 Bad Request** (`"Le festival a déjà été publié. Les modifications ordinaires du planning sont verrouillées."`).

### Scénario 5 : Publication avec contrôle strict du planning (R8)
1. Tentez de publier un festival dont le planning contient des conflits ou des concerts hors dates : l'API bloque la publication et renvoie **HTTP 400 Bad Request**.
2. Sur un planning valide, `POST /festivals/1/publish` passe le statut à `"published"` et notifie les équipes.

### Scénario 6 : Déclaration et résolution d'incidents (R10)
1. Déclarez un incident via `POST /incidents` avec :
   ```json
   {
     "concert_id": 1,
     "description": "Panne de retour son sur la scène principale"
   }
   ```
2. Une description vide est immédiatement rejetée (**HTTP 400**).
3. Clôturez l'incident via `PATCH /incidents/{id}/resolve` ➔ son statut passe à `resolved: true`.

---

## 6. Documentation Technique & Livrables

Tous les livrables d'ingénierie logicielle sont disponibles dans le dossier `docs_h/` :
* [Livrable Intermédiaire Étape 1 : Diagnostic Initial](docs_h/livrable_intermediaire_step_1.md)
* [Livrable Intermédiaire Étape 2 : Modélisation Métier DDD](docs_h/livrable_intermediaire_step_2.md)
* [Livrable Étape 6 : Stratégie de Tests & Pyramide](docs_h/strategie_de_tests.md)
* [Livrables Finaux (Pôle Développeur 1) : Diagrammes UML & Note d'Architecture](docs_h/livrables_finaux.md)
* [Livrables Finaux (Pôle Développeur 3) : Diagrammes UML & Note d'Architecture Opérations](docs_h/livrables_dev3_operations.md)
* [Dossier d'Ingénierie Cybersécurité & Hardening OWASP](docs_h/cybersecurite_hardening.md)
* [Matrice de Traçabilité des Règles Métier](docs_h/regles_metier.md)



# FestiPlan — API de Gestion de Festival (Architecture Hexagonale)

API FastAPI de gestion de festival de musique (*Hellforge Open Air*), refactorisée selon les principes de l'**Architecture Hexagonale (Ports & Adapters)** et du **Domain-Driven Design (DDD)**.

---

## 1. Fonctionnalités & Domaine Métier

* **Festivals :** Création, consultation, publication et dépublication du planning.
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
├── composition.py                  # Point de composition : crée et injecte les adaptateurs
├── domain/                         # Cœur métier sans framework
│   ├── models/                     # Entités (Festival, Concert, Stage, Artist, Incident)
│   ├── value_objects/              # TimeSlot, FestivalPeriod, EquipmentSet, statuts
│   ├── services/                   # scheduling_policy : règles du planning
│   ├── events/                     # Événements de domaine
│   ├── exceptions/                 # Exceptions métier
│   └── ports/                      # Ports sortants (repositories, notification)
├── application/
│   ├── ports/inbound.py            # Ports entrants et commandes
│   └── use_cases/                  # scheduling, logistics, operations
└── adapters/
    ├── primary/                    # Routes FastAPI, schémas Pydantic, sécurité HTTP
    └── secondary/                  # SQLAlchemy, doubles en mémoire, notification
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

Le projet contient **236 tests automatisés** : domaine, cas d'usage, adaptateurs, non-régression et sécurité.

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
* **Conflit de scène (R2) :** Tentez de déplacer un concert sur le créneau d'un autre concert de la même scène (ex : concert n°1 déplacé le 18 juin de 19h45 à 20h15, pendant le concert n°2 sur Mainstage) ➔ L'API renvoie **HTTP 409 Conflict** (`"Conflit de scène"`).
* **Conflit d'artiste (R3) :** Tentez de déplacer un concert pour faire jouer un artiste sur deux scènes différentes en même temps ➔ L'API renvoie **HTTP 409 Conflict** (`"Conflit d'artiste"`).

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
3. L'API refuse la modification et renvoie **HTTP 409 Conflict** (`"Le festival a déjà été publié. Les modifications ordinaires du planning sont verrouillées."`).
4. Pour rouvrir le planning, appelez `POST /festivals/1/unpublish`. Le déplacement est alors accepté, et une nouvelle publication repasse par tous les contrôles.

### Scénario 5 : Publication avec contrôle strict du planning (R8)
1. Tentez de publier un festival dont le planning contient des conflits ou des concerts hors dates : l'API bloque la publication et renvoie **HTTP 400 Bad Request**.
2. Sur un planning valide, `POST /festivals/1/publish` passe le statut à `"published"` et notifie les équipes.
3. Publier un festival déjà publié renvoie **HTTP 409 Conflict**.

### Scénario 6 : Déclaration et résolution d'incidents (R10)
1. Déclarez un incident via `POST /incidents` avec :
   ```json
   {
     "concert_id": 1,
     "description": "Panne de retour son sur la scène principale"
   }
   ```
2. Une description vide est immédiatement rejetée (**HTTP 422**).
3. Clôturez l'incident via `PATCH /incidents/{id}/resolve` ➔ son statut passe à `resolved: true`.

---

## 6. Documentation Technique & Livrables

Tous les livrables sont regroupés dans le dossier [`docs/`](docs/) :

* [Note d'architecture et diagramme de séquence](docs/note_architecture.md)
* [Diagramme UML de composants](docs/diagramme_composants.svg) ([version modifiable](docs/diagramme_composants.drawio))
* [Diagnostic de l'architecture initiale](docs/livrable_intermediaire_step_1.md) et son [schéma](docs/architecture-initiale.drawio)
* [Modélisation DDD](docs/livrable_intermediaire_step_2.md) et son [schéma](docs/modele-domaine.drawio)
* [Reproduction des trois défauts](docs/reproduction_defauts.md)
* [Stratégie de tests](docs/strategie_de_tests.md)
* [Traçabilité des règles métier](docs/regles_metier.md)
* [Sécurité](docs/cybersecurite_hardening.md)
* [Rétrospective et bonnes pratiques](docs/bilan_critique_et_guide_bonnes_pratiques.md)

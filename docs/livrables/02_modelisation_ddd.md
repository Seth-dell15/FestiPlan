# Livrable Intermédiaire — Étape 2 : Modélisation Métier DDD (Domain-Driven Design)

**Projet :** FestiPlan — Gestion d'un festival metal fictif (*Hellforge Open Air*)  
**Contexte :** Module Architecture Hexagonale & DDD — Ynov B3  
**Référence du sujet :** Consignes Étape 2 (p. 7-8 du sujet de synthèse)

> [!NOTE]
> **Lecture conseillée sur GitHub** : il est préférable de consulter ce document sur GitHub, où la présentation est meilleure et les schémas plus lisibles.

---

## 1. Vue d'ensemble du Modèle Métier DDD

Dans l'architecture hexagonale, le **Domaine** constitue le cœur pur de l'application : il ne dépend ni d'une base de données relationnelle (SQLAlchemy), ni d'un protocole réseau (HTTP / FastAPI).

Pour structurer ce domaine et protéger nos règles métier, nous appliquons les concepts clés de **Domain-Driven Design (DDD)** :
* **Entités :** objets définis par leur identité propre et leur cycle de vie.
* **Objets-Valeurs (Value Objects) :** notions immuables définies par leurs attributs, auto-validées à la création.
* **Invariants :** règles de cohérence garanties à chaque instant.
* **Agrégats :** grappes d'objets délimitant les frontières de consistance transactionnelle.
* **Événements de Domaine :** faits métier accomplis permettant le découplage des effets secondaires.

---

## 2. Modélisation Conceptuelle du Domaine

Le modèle complet présente les cinq agrégats, les objets-valeurs, les invariants et les événements de domaine.

![Modèle du domaine](../schemas/modele-domaine.svg)

Version modifiable : [modele-domaine.drawio](../schemas/modele-domaine.drawio).

Le schéma suivant détaille le déplacement d'un concert.

![Modèle du déplacement d'un concert](../schemas/modele_deplacement.svg)

Version modifiable : [modele_deplacement.drawio](../schemas/modele_deplacement.drawio).

---

## 3. Justification des Entités vs Objets-Valeurs

### 3.1 Les Entités (Identité & Cycle de Vie)

Une entité possède un identifiant unique qui persiste même si l'ensemble de ses attributs change. Deux entités ayant exactement les mêmes valeurs restent distinctes si leurs identifiants diffèrent.

- **`Schedule`** ([schedule.py](../../app/domain/models/schedule.py)) : planning d'un festival, identifié par ce festival. Il contient les concerts et constitue le seul point d'entrée pour les modifier.
- **`Concert`** ([concert.py](../../app/domain/models/concert.py)) : un même artiste peut jouer plusieurs concerts. Le concert a son propre cycle de vie, de programmé à annulé, à l'intérieur du planning.
- **`Festival`** : événement global, dont le planning passe de préparation à publié, et peut être retiré.
- **`Artist`** : groupe invité, partagé entre festivals.
- **`Stage`** : espace rattaché à un festival, avec sa capacité et ses équipements.
- **`Incident`** : signalement horodaté rattaché à un concert, résolu une seule fois.

---

### 3.2 Les Objets-Valeurs / Value Objects (Immuabilité & Égalité structurelle)

Un objet-valeur n'a pas d'identité propre. Il est défini uniquement par les valeurs qu'il contient. Deux objets-valeurs possédant les mêmes attributs sont strictement interchangeables. Ils sont **immuables** (`frozen=True`) et garantissent leur propre validité dès leur instanciation.

#### 1. L'Objet-Valeur `TimeSlot` ([app/domain/value_objects/time_slot.py](../../app/domain/value_objects/time_slot.py))
* **Attributs :** `start: datetime`, `end: datetime`.
* **Pourquoi est-ce un Value Object ?** Un créneau *18h00 - 19h00* n'a pas d'ID en base. Si deux concerts ont lieu de 18h à 19h, ils partagent conceptuellement la même valeur temporelle.
* **Richesse comportementale :**
  * `duration` : calcul dynamique de la durée.
  * `overlaps(other)` : calcul pur d'intersection temporelle (`start_a < end_b and start_b < end_a`).
  * `is_within(start_limit, end_limit)` : vérification d'inclusion dans une période.

#### 2. L'Objet-Valeur `FestivalPeriod` ([app/domain/value_objects/festival_period.py](../../app/domain/value_objects/festival_period.py))
* **Attributs :** `start: datetime`, `end: datetime`.
* **Pourquoi est-ce un Value Object ?** Une période n'existe pas sans son festival et se compare par ses dates. Elle refuse à sa création une fin antérieure ou égale au début, et fournit les bornes utilisées par R6.

#### 3. L'Objet-Valeur `EquipmentSet` ([app/domain/value_objects/equipment_set.py](../../app/domain/value_objects/equipment_set.py))
* **Attributs :** `items: frozenset[str]`.
* **Pourquoi est-ce un Value Object ?** Les besoins d'un artiste et la dotation d'une scène sont un même concept : un ensemble d'équipements, sans identité. Il remplace les chaînes CSV du code initial.
* **Richesse comportementale :** `covers(required)` et `missing(required)` portent la règle R5, ce qui évite de la réécrire dans un service ou une route.

#### 4. Les statuts `FestivalStatus` et `ConcertStatus` ([app/domain/value_objects/](../../app/domain/value_objects))
* Énumérations fermées (`PREPARATION` / `PUBLISHED`, `SCHEDULED` / `CANCELLED`) qui remplacent les chaînes libres du code initial : un statut inconnu ne peut plus exister.

---

### 3.3 Le Langage Omniprésent (Ubiquitous Language)

Le code reprend le vocabulaire du sujet, pour qu'un terme métier désigne la même chose dans la discussion, dans le modèle et dans les tests.

| Terme du sujet | Nom dans le code |
| :--- | :--- |
| Festival | `Festival` |
| Scène | `Stage` |
| Artiste | `Artist` |
| Concert | `Concert` |
| Créneau | `TimeSlot` |
| Période du festival | `FestivalPeriod` |
| Besoins techniques, équipements | `EquipmentSet` |
| Planning | `Schedule` |
| Publication | `Festival.publish()` |
| Incident | `Incident` |

Les cas d'usage portent le nom de l'action métier : programmer (`ScheduleConcert`), déplacer (`RescheduleConcert`), annuler (`CancelConcert`), publier (`PublishFestival`), dépublier (`UnpublishFestival`), déclarer un incident (`DeclareIncident`).

---

## 4. Définition et Localisation des Invariants

Un **invariant** est une règle de cohérence qui doit être vraie à tout instant pour qu'un objet métier soit dans un état valide.

DDD impose de placer chaque invariant **au plus près de la structure qui en a la responsabilité** :

- **R1, fin après début** : `TimeSlot.__post_init__`. Un créneau invalide ne peut pas exister.
- **Concert annulé non modifiable** : `Concert.reschedule()` et `Concert.cancel()`. L'entité protège son cycle de vie.
- **R2 et R3, conflits** : `Schedule.add_concert()` et `Schedule.reschedule_concert()`. La règle compare plusieurs concerts, donc elle appartient à la racine qui les contient ; la comparaison de deux concerts reste dans `Concert.check_conflict_with()`.
- **R4 et R5, scène adaptée** : `Schedule.add_concert()`, qui s'appuie sur `Stage.belongs_to()` et `Stage.ensure_can_host()`.
- **R6, période du festival** : `Schedule`, qui connaît la période de son festival.
- **R7, planning publié** : `Schedule`, pour programmer, déplacer et annuler. La procédure explicite est `Festival.unpublish()`.
- **R8, publication** : `Schedule.ensure_publishable()`, appelée avant `Festival.publish()`.
- **R9, capacité** : `Stage.__post_init__`.
- **R10, incident** : `Incident.__post_init__` pour la description, `DeclareIncidentUseCase` pour l'existence du concert.

---

## 5. Définition des Frontières d'Agrégats (Aggregate Boundaries)

Un **agrégat** regroupe des objets métier soumis à des règles de cohérence communes. Sa **racine d'agrégat (Aggregate Root)** est le seul point d'entrée pour les modifications externes.

### Le choix de conception retenu

Le sujet met en garde contre deux excès : placer tous les objets dans un seul agrégat, ou créer un agrégat par classe. Trois découpages ont été comparés.

1. **Un agrégat géant `Festival`**, contenant scènes, artistes et concerts. Tout serait vérifiable dans un seul objet, mais créer une scène chargerait et verrouillerait le festival entier, et `Artist` ne peut pas lui appartenir puisqu'un artiste est partagé entre festivals.
2. **Un agrégat par entité**, chaque concert étant sa propre racine. C'est le plus simple à écrire, mais aucune racine ne peut alors garantir R2 et R3 : un concert ne connaît pas les autres. Les règles du planning sortiraient du modèle.
3. **Cinq agrégats, dont un planning**, solution retenue :
   - **`Schedule`** : planning d'un festival, racine qui contient les entités `Concert`. C'est le seul agrégat à plusieurs entités, car c'est le seul endroit où des objets doivent rester cohérents ensemble.
   - **`Festival`** : identité, période et cycle de publication.
   - **`Stage`** : capacité et équipements, rattachée à un festival.
   - **`Artist`** : besoins techniques, partagé entre festivals.
   - **`Incident`** : description et résolution, rattaché à un concert.

### Justification de la frontière

- **Les invariants décident de la frontière** : R2, R3, R6 et R7 portent sur l'ensemble des concerts d'un festival. Ces concerts sont donc dans le même agrégat, et `Schedule` les vérifie à chaque modification.
- **Une seule porte d'entrée** : programmer, déplacer et annuler passent par `Schedule.add_concert()`, `reschedule_concert()` et `cancel_concert()`. Il n'existe pas de repository de concert : `IScheduleRepository` charge et enregistre le planning entier en une transaction, et `IConcertQueryPort` ne sert qu'à la lecture.
- **Ce qui reste dehors** : `Stage` et `Artist` sont référencés par identifiant et passés en paramètre à `add_concert()` pour R4 et R5. La période et l'état de publication appartiennent à `Festival` ; le planning les lit au chargement.
- **R3 entre festivals** : cette règle croise deux plannings. Le cas d'usage charge les concerts de l'artiste dans les autres festivals et les transmet à la racine, qui tranche.
- **Coût assumé** : chaque modification charge tous les concerts du festival, ce qui reste raisonnable à l'échelle d'un festival. Sans verrou en base, deux requêtes simultanées peuvent encore contourner le contrôle. La [note d'architecture](03_note_architecture.md) détaille ces compromis.

---

## 6. Événements de Domaine (Domain Events) & Découplage

Le sujet insiste particulièrement sur la distinction de quatre concepts dans le flux de traitement :

```text
┌────────────────────────────┐
│ 1. Commande                │  Demande d'action explicite (intention)
│ RescheduleConcertCommand   │  Ex: "Déplacer le concert #1 de 14h à 15h"
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│ 2. Cas d'Utilisation       │  Orchestration : charge le planning (Schedule),
│ RescheduleConcertUseCase   │  qui valide R2, R3, R6 et R7
└─────────────┬──────────────┘  - Persiste le planning via IScheduleRepository
              │
              ▼
┌────────────────────────────┐
│ 3. Événement de Domaine    │  Fait accompli immuable (passé)
│ ConcertRescheduledEvent    │  "Le concert #1 a été déplacé"
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│ 4. Mécanisme Technique     │  Effet secondaire réactif non bloquant
│ EmailNotificationAdapter   │  Envoi d'un email de notification
└────────────────────────────┘
```

### Bénéfice immédiat (Résolution du Défaut 2)
Dans le code legacy, l'appel à la notification était directement imbriqué après le commit SQL, faisant crasher la requête en 500 en cas de défaillance réseau.  
En séparant clairement **le fait accompli** (`ConcertRescheduledEvent`) du **mécanisme technique réactif** (`INotificationSenderPort`), l'échec de la notification est traité comme un incident technique secondaire : il est consigné dans les logs sans annuler la réussite du cas d'usage, assurant une parfaite cohérence pour l'utilisateur.

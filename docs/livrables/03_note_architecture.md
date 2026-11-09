# Note d'architecture — FestiPlan

Cette note justifie la refactorisation de FestiPlan en architecture hexagonale, avec les concepts DDD utiles au projet. Elle décrit le code livré sur `feat/logistics-domain-usecases`.

## Sommaire

1. Défauts de l'architecture initiale
2. Diagrammes UML
3. Responsabilités de chaque couche
4. Ports et adaptateurs
5. Modèle métier
6. Correction des trois défauts
7. Stratégie de tests
8. Limites et compromis
9. Patrons de conception

Documents associés : [diagnostic initial](01_diagnostic_initial.md), [modélisation DDD](02_modelisation_ddd.md), [reproduction des défauts](05_reproduction_defauts.md), [traçabilité des règles](04_regles_metier.md), [stratégie de tests](06_strategie_de_tests.md).

## 1. Défauts de l'architecture initiale

Le diagnostic complet figure dans le [livrable de l'étape 1](01_diagnostic_initial.md). Quatre problèmes ont guidé la refactorisation.

- **Couplage technique** : la `Session` SQLAlchemy et les modèles ORM traversaient les routes, les services et les repositories. Tester une règle demandait une base SQLite.
- **Responsabilités mal placées** : certaines routes interrogeaient la base, et les règles étaient réparties entre Pydantic, les routes et les services.
- **Dépendances instanciées en dur** : chaque service créait son repository et son service de notification, ce qui empêchait de les remplacer.
- **Effets de bord non isolés** : la notification partait après le commit, donc une panne produisait une erreur 500 alors que la donnée était enregistrée.

Le déplacement d'un concert réunissait ces problèmes : il ne vérifiait que l'ordre des dates. Les trois défauts du sujet ont été [reproduits sur le code initial](05_reproduction_defauts.md).

## 2. Diagrammes UML

### Diagramme de composants

![Diagramme UML de composants](../schemas/diagramme_composants.svg)

La version modifiable est [diagramme_composants.drawio](../schemas/diagramme_composants.drawio).

Une requête arrive sur une route FastAPI. La route valide le format avec Pydantic, puis appelle un cas d'usage fourni par `app/composition.py`. Le cas d'usage s'appuie sur le domaine et sur des ports sortants. Les adaptateurs SQLAlchemy et email implémentent ces ports. Le sens des dépendances est vérifié par [test_architecture.py](../../tests/unit/test_architecture.py).

### Diagramme de séquence : déplacer un concert

![Diagramme UML de séquence du déplacement d'un concert](../schemas/diagramme_sequence.svg)

Version modifiable : [diagramme_sequence.drawio](../schemas/diagramme_sequence.drawio).

## 3. Responsabilités de chaque couche

- **Domaine (`app/domain`)** : entités, objets-valeurs, événements, exceptions métier et politique de programmation. Il n'importe ni FastAPI, ni SQLAlchemy, ni Pydantic.
- **Application (`app/application`)** : cas d'usage. Chacun charge les données par les ports, appelle le domaine, enregistre le résultat puis déclenche les effets de bord.
- **Adaptateurs entrants (`app/adapters/primary`)** : routes FastAPI, schémas Pydantic et protections HTTP. Ils traduisent une requête en commande et une erreur métier en code HTTP.
- **Adaptateurs sortants (`app/adapters/secondary`)** : persistance SQLAlchemy, doubles en mémoire et notification.
- **Composition (`app/composition.py`)** : seul module qui crée les adaptateurs concrets et les injecte dans les cas d'usage.

Une règle est placée au plus près de ce qu'elle protège. Un créneau invalide n'a pas de sens, donc `TimeSlot` le refuse à sa création. Un conflit compare plusieurs concerts, donc il relève de `Concert.check_conflict_with` et de `scheduling_policy`. Vérifier qu'un artiste existe nécessite un accès aux données, donc le cas d'usage s'en charge. Pydantic ne contrôle que le format des requêtes.

Les codes HTTP suivent une règle unique. Le code 400 signale des données contraires à une règle métier, 404 une ressource absente, 409 un conflit avec l'état du planning, et 422 un format de requête invalide.

## 4. Ports et adaptateurs

### Ports entrants

Définis dans [inbound.py](../../app/application/ports/inbound.py), ils décrivent les commandes métier principales : `IScheduleConcertPort`, `IRescheduleConcertPort`, `IPublishFestivalPort`, `IUnpublishFestivalPort` et `IDeclareIncidentPort`.

Les lectures simples, les créations du référentiel et l'annulation appellent directement leur cas d'usage. Une interface supplémentaire n'y protégerait aucune variation réelle. [test_inbound_ports.py](../../tests/integration/test_inbound_ports.py) vérifie qu'une route accepte toute implémentation de son port.

### Ports sortants

| Port | Production | Double de test |
|---|---|---|
| `IConcertRepository` | `ConcertSqlRepository` | `InMemoryConcertRepository` |
| `IFestivalRepository` | `FestivalSqlRepository` | `InMemoryFestivalRepository` |
| `IFestivalQueryPort` | `FestivalSqlQueryAdapter` | Doublure locale aux tests |
| `IStageRepository` | `StageSqlRepository` | `InMemoryStageRepository` |
| `IArtistRepository` | `ArtistSqlRepository` | `InMemoryArtistRepository` |
| `IIncidentRepository` | `IncidentSqlRepository` | `InMemoryIncidentRepository` |
| `INotificationSenderPort` | `EmailNotificationAdapter` | `FakeNotificationAdapter` |

Les repositories isolent le stockage et permettent de tester les cas d'usage sans base. `IFestivalQueryPort` fournit uniquement les dates et l'état de publication nécessaires à la programmation. `INotificationSenderPort` reçoit des événements métier, ce qui permet de simuler une panne sans réseau.

## 5. Modèle métier

Le schéma complet est [modele-domaine.drawio](../schemas/modele-domaine.drawio).

### Entités

`Festival`, `Concert`, `Stage`, `Artist` et `Incident` possèdent une identité et sont comparés par identifiant : deux concerts aux mêmes horaires restent distincts.

### Objets-valeurs

- `TimeSlot` : créneau immuable, garantit R1 et calcule les chevauchements.
- `FestivalPeriod` : période immuable d'un festival.
- `EquipmentSet` : ensemble d'équipements qui remplace la manipulation de texte CSV.
- `FestivalStatus` et `ConcertStatus` : statuts fermés qui remplacent les chaînes libres.

### Invariants

- **Objet-valeur** : R1 et cohérence des dates du festival.
- **Entité** : R9 et R5 sur `Stage`, R10 sur `Incident`, transitions de `Festival` et interdiction de modifier un concert annulé.
- **Politique de domaine** : R2 à R8 dans `scheduling_policy`, car ces règles croisent plusieurs agrégats.
- **Cas d'usage** : existence des références (R4 et R10), car elle demande un accès aux données.

### Agrégats

Le modèle compte cinq agrégats, dont la racine est l'entité du même nom : `Festival`, `Concert`, `Stage`, `Artist` et `Incident`. Ils se référencent par identifiant.

Un agrégat `Festival` contenant scènes et concerts aurait rendu les conflits vérifiables dans un seul objet, mais il aurait obligé à charger tout le planning pour la moindre modification et aurait augmenté les conflits d'écriture. `Artist` ne peut pas lui appartenir, car un artiste est partagé entre festivals.

Ce découpage a un coût : R2 et R3 ne sont pas garanties par une seule racine. La politique de domaine les vérifie à partir des concerts chargés par le cas d'usage, et la section 8 en décrit la limite.

### Contextes métier

Le code distingue trois sous-domaines : planification, référentiel et opérations. Ils partagent un seul modèle et une seule base. Séparer davantage ces contextes ajouterait des traductions sans besoin réel pour un monolithe de cette taille.

### Commande, cas d'usage, événement, réaction

Pour un déplacement, `RescheduleConcertCommand` exprime la demande, `RescheduleConcertUseCase` l'orchestre, `ConcertRescheduledEvent` décrit le fait accompli, et `EmailNotificationAdapter` y réagit à travers `INotificationSenderPort`. `FestivalPublishedEvent` et `FestivalUnpublishedEvent` suivent le même principe.

## 6. Correction des trois défauts

Le détail des requêtes et des résultats, avant et après, figure dans [05_reproduction_defauts.md](05_reproduction_defauts.md).

### Défaut 1 : conflits de programmation

`ScheduleConcertUseCase` et `RescheduleConcertUseCase` appliquent les mêmes fonctions de `scheduling_policy`. Le déplacement construit un concert candidat, le compare aux concerts actifs du festival et de l'artiste, puis seulement modifie le concert réel. Un conflit renvoie 409.

R3 est contrôlée entre festivals, car un artiste ne peut pas être à deux endroits en même temps.

### Défaut 2 : notification en échec

Le déplacement et la publication sont les opérations métier ; la notification est un effet de bord. Elle part après `save()`. Si elle échoue, l'exception est journalisée, la modification reste enregistrée, et l'API répond 200 avec `notification_sent: false`.

Le client sait ainsi que l'opération a réussi et que l'alerte n'est pas partie. Une file de messages n'a pas été retenue, car elle serait disproportionnée pour ce projet.

### Défaut 3 : planning publié

`FestivalStatus` représente l'état du planning, et `Festival` porte les transitions `publish()` et `unpublish()`.

La règle retenue est le refus suivi d'une dépublication explicite. Programmer, déplacer ou annuler un concert d'un festival publié renvoie 409. `POST /festivals/{id}/unpublish` remet le planning en préparation et prévient les équipes. Une nouvelle publication repasse par tous les contrôles de R8.

## 7. Stratégie de tests

La suite compte 236 tests, tous au vert. Le détail est dans [06_strategie_de_tests.md](06_strategie_de_tests.md).

- **Domaine** : 81 tests, sans FastAPI ni SQLite.
- **Cas d'usage** : 63 tests avec des doubles de test.
- **Adaptateurs** : 49 tests sur les routes, SQLite et la notification.
- **Non-régression** : 19 tests HTTP sur les défauts et les erreurs corrigées.
- **Autres** : 14 tests de sécurité, 6 tests de l'API initiale et 4 tests du sens des dépendances.

Les 4 tests HTTP des trois défauts échouent sur le code initial et passent sur le code livré.

## 8. Limites et compromis

- **Concurrence** : les conflits sont vérifiés puis enregistrés sans verrou ni contrainte en base. Deux requêtes simultanées peuvent donc créer un chevauchement. Un numéro de version ou une contrainte SQL le corrigerait.
- **Notification** : l'envoi reste synchrone et n'est pas retenté. Une notification en échec est signalée mais perdue. Une table outbox et un worker seraient la suite logique.
- **Validation de l'enregistrement** : chaque `save()` valide sa transaction. C'est suffisant ici, car chaque cas d'usage modifie un seul agrégat ; une opération sur plusieurs agrégats nécessiterait une unité de travail.
- **Entités mutables** : les invariants d'entité sont vérifiés à la création et dans les méthodes métier, mais un attribut comme `Stage.capacity` reste modifiable directement.
- **Modification après publication** : il n'existe que la dépublication. Une procédure d'urgence ciblant un seul concert serait un ajout métier distinct.
- **Emplacement des ports** : les ports sortants sont dans le domaine et les ports entrants dans l'application. Ils pourraient être regroupés sans changer le sens des dépendances.
- **Schéma de base** : les tables sont créées par `create_all()`, sans migrations. Les équipements restent stockés en texte, convertis par `EquipmentSet`.
- **Hors périmètre** : l'API n'a ni authentification ni gestion des rôles.

## 9. Patrons de conception

- **Repository** : isole la persistance derrière un contrat.
- **Adapter** : traduit les contrats des ports vers SQLAlchemy et l'envoi d'emails.
- **Value Object** : donne un sens et une validation aux créneaux, périodes et équipements.
- **Domain Event** : décrit un fait accompli sans coupler le domaine à la notification.
- **Command** : porte une intention métier indépendante du format HTTP.
- **Domain Service** : `scheduling_policy` centralise les règles qui croisent plusieurs agrégats.
- **Composition Root** : `app/composition.py` assemble les dépendances à un seul endroit.
- **DTO** : les schémas Pydantic séparent le contrat de l'API du modèle métier.
- **Middleware** : ajoute les en-têtes de sécurité sans toucher au cœur applicatif.

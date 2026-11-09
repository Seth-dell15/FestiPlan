# Convention de commits — FestiPlan

## Format

```text
<gitmoji> <type>(<pôle>): <description>
```

Exemple : `✨ feat(logistique): ajouter le value object EquipmentSet`

## Règles

- Description en français, au présent de l'impératif (« ajouter », « corriger », « supprimer »).
- Les termes techniques ne sont pas traduits : value object, entity, aggregate, repository, use case, port, adapter.
- Tout en minuscules après les deux-points, sans point final.
- Première ligne de 72 caractères maximum.
- Un commit = un changement cohérent : ne pas mélanger une fonctionnalité et un refactor sans rapport.
- Le pôle est optionnel pour les fichiers communs : `👷 ci: …`, `📝 docs: …`.
- Si le changement mérite une explication, ajouter un corps séparé par une ligne vide, qui dit pourquoi plutôt que comment.

## Pôles

| Pôle | Périmètre |
| :--- | :--- |
| `planification` | Dev 1 : concerts, créneaux, conflits |
| `logistique` | Dev 2 : festivals, artistes, scènes |
| `operations` | Dev 3 : publication, incidents, notifications |

## Types et gitmojis

Liste complète des gitmojis : https://gitmoji.dev

| Gitmoji | Type | Usage |
| :--- | :--- | :--- |
| ✨ | `feat` | Nouvelle fonctionnalité |
| 🐛 | `fix` | Correction de bug |
| ♻️ | `refactor` | Restructuration sans changer le comportement |
| ✅ | `test` | Ajout ou correction de tests |
| 🗃️ | `db` | Repositories SQL, modèles ORM, seed |
| 👷 | `ci` | Intégration continue |
| 📝 | `docs` | README, note d'architecture, diagrammes |
| 🔥 | `remove` | Suppression de code |
| 🚨 | `lint` | Corrections de linter ou SonarLint |
| 🔧 | `config` | Configuration du projet |

## Exemples

- `✨ feat(logistique): ajouter les entités Festival, Artist et Stage`
- `🐛 fix(planification): refuser le déplacement d'un concert sur une scène occupée`
- `🐛 fix(operations): renvoyer un succès quand seule la notification échoue`
- `♻️ refactor(logistique): déplacer la création de scène dans un use case`
- `✅ test(planification): couvrir le chevauchement d'un artiste sur deux scènes`
- `🗃️ db(logistique): implémenter FestivalSqlRepository`
- `🔥 remove(logistique): supprimer FestivalService.publish sans contrôle`
- `👷 ci: lancer pytest sur chaque pull request`
- `📝 docs: ajouter le diagramme de séquence du déplacement de concert`

## Commit avec corps

```bash
git commit -m "🐛 fix(operations): renvoyer un succès quand seule la notification échoue" -m "La modification est persistée avant l'envoi : un échec de notification ne doit plus produire une erreur 500."
```

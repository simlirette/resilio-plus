# resilio-archive/

Archivage du dépôt Resilio+. Fichiers ici = hors scope actif, conservés pour référence.

**Politique**: Archiver plutôt que supprimer. Contenu récupérable via git history ou tags `archive/*`.

## Structure

| Dossier | Contenu |
|---|---|
| `branches/` | Index des branches archivées (tags git `archive/<nom>-2026-04-19`) |
| `frontend-experiments/` | Tentatives UI mises de côté |
| `docs-obsolete/` | Documents remplacés ou complétés |
| `misc/test-logs/` | Sorties de tests ponctuelles |
| `misc/session-reports/` | Rapports de sessions Claude Code |
| `misc/review-reports/` | Rapports de review |
| `misc/skill-builder/` | Artefact superpowers tooling |

## Récupérer une branche archivée

```bash
git checkout -b <nom> archive/<nom>-2026-04-19
```

Audit initial: 2026-04-19. Voir `docs/cleanup-2026-04-19.md` pour changelog complet.

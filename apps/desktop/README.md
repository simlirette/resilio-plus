# @resilio/desktop

Tauri wrapper of `apps/web` — à scaffolder en Vague 1 Session T (Tauri setup).

## Statut

**Placeholder — Vague 1**

Ce dossier sera scaffoldé avec `npm create tauri-app` en Vague 1 Session T.

## Architecture prévue

- Tauri v2 wrap de `apps/web` (Next.js exporté en mode statique ou servi localement)
- Accès aux APIs natives : file system, notifications, tray icon
- Distribution : macOS (dmg), Windows (msi)

## Dépendances prévues

- `@tauri-apps/api`
- `@tauri-apps/cli`

## Pourquoi pas maintenant ?

Le scaffolding Tauri nécessite Rust toolchain + configuration native.
C'est le périmètre d'une session dédiée pour éviter de polluer
la session S-0 qui est focalisée sur la structure monorepo.

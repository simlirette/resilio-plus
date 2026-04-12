# @resilio/mobile

Expo React Native iOS app — à scaffolder en Vague 1 Session M (Expo setup).

## Statut

**Placeholder — Vague 1**

Ce dossier sera scaffoldé avec `npx create-expo-app` en Vague 1 Session M.

## Architecture prévue

- Expo SDK (dernière version stable)
- React Native + Expo Router (file-based navigation)
- iOS uniquement en V1 (Android en V2)
- Partage de code via `@resilio/ui-mobile`, `@resilio/shared-logic`, `@resilio/api-client`, `@resilio/design-tokens`

## Ce qui sera implémenté

- Écrans principaux : Dashboard, Check-in, Energy, Plan, History
- Push notifications (Expo Notifications)
- HealthKit integration (React Native Health)

## Pourquoi pas maintenant ?

Le scaffolding Expo nécessite la configuration Xcode + simulateur iOS.
C'est le périmètre d'une session dédiée pour éviter de polluer
la session S-0 qui est focalisée sur la structure monorepo.

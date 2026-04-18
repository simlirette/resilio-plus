# UI Integration v1 — Corrections d'anti-patterns

- [Task 4] app/(auth)/login.tsx : SpaceGrotesk → Inter (via Text ui-mobile)
- [Task 4] app/(auth)/login.tsx : `Text` RN brut → `Text` de @resilio/ui-mobile
- [Task 4] app/(auth)/login.tsx : hex hardcodés → themeColors.* via useTheme()
- [Task 4] app/(auth)/login.tsx : `colors.primary` (ancien) → `colors.accent`
- [Task 4] app/(auth)/login.tsx : accent oklch(0.62 0.14 35) amber → colors.accent (#3B74C9)

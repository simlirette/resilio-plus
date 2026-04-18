# Design Analysis — Resilio+ Home Screen
**Source:** `docs/design/home/home-screen.jsx` + `Resilio Home.html`
**Date:** 2026-04-17

## Palette

### Light Mode
| Token | Hex | Usage |
|-------|-----|-------|
| bg | `#F7F4EE` | Screen background |
| surface | `#FDFBF7` | Card background |
| surface2 | `#F3EFE8` | Inner metric bg, zone badge |
| text | `#2B2824` | Primary text |
| textSec | `rgba(43,40,36,0.62)` | Secondary text |
| textTer | `rgba(43,40,36,0.38)` | Tertiary / labels |
| hairline | `rgba(43,40,36,0.08)` | Borders, dividers |
| track | `rgba(43,40,36,0.08)` | SVG ring track |
| warn | `#B8863A` | Nutrition metric |
| ok | `#6B9259` | Strain metric |
| okStrong | `#5C8250` | Sleep metric |
| caution | `#A6762E` | Prudent state dot |

### Dark Mode
| Token | Hex | Usage |
|-------|-----|-------|
| bg | `#131210` | Screen background |
| surface | `#1C1B18` | Card background |
| surface2 | `#232120` | Inner metric bg |
| text | `#EDE9E2` | Primary text |
| textSec | `rgba(237,233,226,0.62)` | Secondary text |
| textTer | `rgba(237,233,226,0.38)` | Tertiary / labels |
| hairline | `rgba(237,233,226,0.08)` | Borders, dividers |
| track | `rgba(237,233,226,0.08)` | SVG ring track |
| warn | `#D6A24A` | Nutrition metric |
| ok | `#7DA66A` | Strain metric |
| okStrong | `#6B9259` | Sleep metric |
| caution | `#C79140` | Prudent state dot |

### Accent Options
| Key | Hex | Default |
|-----|-----|---------|
| clinical | `#3B74C9` | ✅ Yes |
| emerald | `#2F7D5B` | — |
| indigo | `#5B5BAF` | — |

## Typography
**Font:** Inter (NOT Space Grotesk) — migration required

| Usage | Size | Weight | Tracking | Line Height |
|-------|------|--------|----------|-------------|
| Readiness number | 72px | 300 | -2px | 1 |
| Allostatic number | 38px | 300 | -1.2px | 1 |
| Greeting name | 26px | 500 | -0.6px | 1.15 |
| Metric value (small ring) | 20px | 500 | -0.5px | — |
| Session title | 17px | 500 | -0.3px | 1.25 |
| Body / badge text | 13px | 500 | -0.1px | — |
| Date / session details | 13px | 400 | +0.1px | — |
| Metric label | 12px | 400 | +0.1px | — |
| Section label (CAPS) | 11px | 500 | +1.2px | — |
| Eyebrow / legend | 10-11px | 500 | +0.6–1.4px | — |
| Numeric tabular | — | — | — | `fontVariantNumeric: 'tabular-nums'` |

## Spacing
- Screen horizontal: 24px (greeting), 20px (cards)
- Screen paddingTop: 56px (header area)
- Screen paddingBottom: 100px (above tab bar)
- Card vertical gap: 16–20px
- Section gaps: 16–24px

## Radius
- Card: 22px
- Button: 16px
- State badge pill: 999 (full round)
- Zone badge: 4px
- Chevron circle: 50%
- Tab bar: 33px

## Components

### ReadinessRing
- SVG size: 216×216px
- Stroke width: 10px
- Fill color: accent (`#3B74C9`)
- Track: `t.track`
- Inner label "Readiness": 11px, uppercase, tracking 1.2, textTer
- Value: 72px, weight 300, tracking -2, tabular-nums

### State Badge (ReadinessStatusBadge)
- bg: `t.surface`, border: `0.5px solid t.hairline`, radius: 999
- Dot: 7px circle, bg=`t.caution` / `t.ok` / red
- Text: 13px, weight 500, tracking -0.1

### Metric Rings (MetricRow)
- SVG size: 68×68px  
- Stroke: 5px
- Colors: nutrition=`warn`, strain=`ok`, sleep=`okStrong`
- Wrapped in Card with 0.5px hairline dividers between columns
- Card padding: 2px 4px
- Each metric: flex=1, 16px top pad, 14px bottom pad

### AllostaticDial (CognitiveLoadDial)
- SVG: 180×96px, cx=90, cy=90, r=76, stroke=9
- Tick marks at 0.25, 0.5, 0.75 (hairline color)
- Fill: accent color
- Value: 38px weight 300 tabular-nums
- Sub-label: 10px uppercase "/ 100"

### SessionCard
Layout: flex row, left=text, right=chevron circle
- Section label row: "SÉANCE DU JOUR" + zone badge (surface2 bg, 4px radius)
- Title: 17px weight 500
- Details: 13px textSec tabular-nums (duration + zone)
- Chevron: 36×36px circle, surface2 bg, SVG chevron icon
- Card padding: 18px 20px

### Button (Primary)
- Height: 54px
- Radius: 16px
- Background: accent
- Text: 16px weight 500, tracking -0.1
- Shadow: `0 6px 18px ${accent}33` + inset highlight

## Layout Order (Home Screen)
1. Greeting (paddingHorizontal 24)
2. Readiness ring (paddingHorizontal 24)
3. Metric row card (paddingHorizontal 20)
4. Allostatic card (paddingHorizontal 20) — side-by-side: text left, dial right
5. Session card (paddingHorizontal 20)
6. Primary button (paddingHorizontal 20)

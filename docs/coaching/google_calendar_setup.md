# Google Calendar Setup

Push your training plan (runs + gym) to a dedicated Google Calendar so you get
notifications on your iPhone before every session.

## 1. Create Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create project → name it **resilio-app** (or anything)
3. Left menu → **APIs & Services** → **Library**
4. Search **Google Calendar API** → Enable

## 2. Create OAuth credentials

1. **APIs & Services** → **Credentials** → **Create credentials** → **OAuth client ID**
2. Application type: **Desktop app**
3. Name: resilio (anything)
4. Download JSON → save as **`credentials.json`** in the repo root (same folder as `CLAUDE.md`)

> `credentials.json` is gitignored — never committed.

## 3. Configure OAuth consent screen

1. **APIs & Services** → **OAuth consent screen**
2. User type: **External** → Create
3. App name: resilio, email: yours
4. Scopes: add `https://www.googleapis.com/auth/calendar`
5. **Test users** → add your Google account email
6. Save

## 4. First run — browser authorization

```bash
poetry run resilio calendar auth
```

- Browser opens → log in with your Google account → click Allow
- Token saved to `data/google_calendar/token.json` (gitignored)
- "Resilio Training" calendar created automatically in your Google Calendar

## 5. Initial or manual sync

```bash
# Sync next 2 weeks (default)
poetry run resilio calendar sync

# Sync further ahead
poetry run resilio calendar sync --weeks 4

# Preview without touching API
poetry run resilio calendar sync --dry-run
```

This command remains available for initial setup, recovery, and dry-run checks.
It is idempotent (no duplicates even if run 10×).

## 6. Verify on iPhone

1. Open **Google Calendar** app on iPhone
2. Menu → your account → should see **Resilio Training** calendar
3. If not visible: Settings → tap your account → enable Resilio Training
4. iPhone **Settings** → Notifications → Google Calendar → Allow

You'll receive a popup notification 30 min before each run, 60 min before long runs.

## 7. Event format

| Session | Title | Content |
|---|---|---|
| Easy run | 🏃 Easy 8km | Pace + RPE + notes |
| Intervals | 🏃 5×1000m intervals | WU + reps + recovery + CD |
| Long run | 🏃 Long run 15km | Full detail |
| Rest | 🛌 Rest | Notes if any |
| Gym | 🏋️ Leg day | "Voir Hevy pour le détail" |

## 8. Automatic sync after plan updates

Whenever `resilio plan populate` adds or modifies an approved week, that exact
week is synchronized automatically. `resilio plan update-from` does the same for
every replaced week, including weeks beyond the normal `sync_weeks_ahead` window.

The plan command response includes a `calendar_sync` result. No separate calendar
command is needed when `calendar_sync.ok` is `true`.

Changed events are patched, removed sessions deleted, new ones added.
Past events are never modified.

Calendar synchronization is non-blocking: if Google is unavailable or its token
needs renewal, the local plan remains saved and `calendar_sync.ok` is `false` with
the required recovery action. Automatic sync never opens a browser while a plan
is being saved.

## Settings

Customize in `config/settings.yaml` under `google_calendar:`:

```yaml
google_calendar:
  sync_weeks_ahead: 2        # default window
  timezone: America/Toronto
  calendar_name: Resilio Training
  # default_times and reminders also configurable
```

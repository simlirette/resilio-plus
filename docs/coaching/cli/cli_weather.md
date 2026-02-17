# Weather Commands

> **Quick Links**: [Back to Index](index.md) | [Core Concepts](core_concepts.md)

Commands for retrieving weekly weather context used during training-plan generation.

**Commands in this category:**
- `resilio weather week` - Monday-Sunday forecast with planning advisories

---

## resilio weather week

Get a 7-day weather forecast for a planning week.

**Usage:**

```bash
# Use location from profile.weather_preferences.location_query
resilio weather week --start 2026-02-16

# Override location for this lookup
resilio weather week --start 2026-02-16 --location "Paris, France"
```

**Parameters:**

- `--start` (required): Week start date in `YYYY-MM-DD`, must be Monday
- `--location` (optional): Override location query string

**Returns:**

- Resolved location (name, coordinates, timezone)
- Daily forecast fields (`temp`, `wind`, `precipitation`, weather code)
- Advisory signals (`heat`, `cold`, `wind`, `precipitation`) with severity level, factual reason, and signal label (e.g. `HEAT_HIGH`, `WIND_MODERATE`)
- Weekly summary string for coach context

**Example success response:**

```json
{
  "ok": true,
  "message": "Retrieved weekly weather forecast for Paris, Ile-de-France, France (2026-02-16 to 2026-02-22)",
  "data": {
    "start_date": "2026-02-16",
    "end_date": "2026-02-22",
    "source": "open-meteo",
    "location": {
      "location_query": "Paris, France",
      "resolved_name": "Paris, Ile-de-France, France",
      "latitude": 48.853,
      "longitude": 2.3499,
      "timezone": "Europe/Paris"
    },
    "daily": [
      {
        "date": "2026-02-16",
        "temperature_min_c": 3.0,
        "temperature_max_c": 9.0,
        "precipitation_mm": 1.2,
        "precipitation_probability_max_pct": 40,
        "wind_speed_max_kph": 18.0,
        "weather_code": 3
      }
    ],
    "advisories": [
      {
        "date": "2026-02-18",
        "type": "heat",
        "level": "high",
        "reason": "Hot day forecast (32.0°C max)",
        "signal": "HEAT_HIGH"
      }
    ],
    "weekly_summary": "Weather advisories for 1/7 days (high-risk days: 1, moderate-risk days: 0)."
  }
}
```

**Example error response (no location configured):**

```json
{
  "ok": false,
  "error_type": "invalid_input",
  "message": "No weather location configured in profile.",
  "data": {
    "next_steps": "Run: resilio profile set --weather-location \"City, Country\" or pass --location to resilio weather week."
  }
}
```

**Timezone behavior:**

The `timezone` field uses the value resolved from Open-Meteo geocoding (e.g., `"Europe/Paris"`). When `timezone` is not yet cached in the profile, the request uses `"auto"` — Open-Meteo automatically selects the timezone based on coordinates. After the first successful lookup, the resolved timezone is cached in `profile.weather_preferences` for consistent future responses.

**Ambiguous locations:**

If your query matches multiple places (e.g., "Springfield"), Open-Meteo returns the highest-ranked result. Use city + country format to be precise: `"Springfield, Missouri, United States"` or `"Springfield, Illinois, United States"`.

**Caching behavior:**

- Profile-based lookups (no `--location`) may enrich `profile.weather_preferences` with resolved location metadata (`resolved_name`, `latitude`, `longitude`, `timezone`) for stable future lookups.
- `--location` is treated as a one-off override and is not persisted to profile.
- After the first successful profile-based lookup, subsequent lookups use cached coordinates (faster, skips geocoding round-trip).

**Error handling:**

| Condition | Error type | Exit code |
|-----------|-----------|-----------|
| `--start` is not Monday | `invalid_input` | 5 |
| No location configured and `--location` omitted | `invalid_input` with `next_steps` | 5 |
| Geocoding finds no match | `not_found` | 2 |
| Open-Meteo API error / rate limit | `api_error` | 5 |
| Network failure | `network` | 4 |

**Profile setup tip:**

Set a default weather location once:

```bash
resilio profile set --weather-location "Paris, France"
```

---

**Navigation**: [Back to Index](index.md) | [Previous: VDOT Commands](cli_vdot.md)

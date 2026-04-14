# Auth System — Resilio+

## Overview

JWT-based auth with access + refresh tokens.

| Token | TTL | Storage |
|---|---|---|
| Access (JWT) | 15 min | Stateless — client only |
| Refresh | 30 days | DB (`refresh_tokens` table, hash only) |
| Password reset | 1 hour | DB (`password_reset_tokens` table, hash only) |

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login` | No | Email + password → access + refresh tokens |
| `POST` | `/auth/refresh` | No | Rotate refresh token → new access + refresh |
| `POST` | `/auth/logout` | Bearer | Revoke refresh token |
| `GET` | `/auth/me` | Bearer | Current user info |
| `POST` | `/auth/forgot-password` | No | Send reset email |
| `POST` | `/auth/reset-password` | No | Set new password via reset token |
| `POST` | `/athletes/onboarding` | No | Register + create plan → tokens |

---

## Flow: Login

```
POST /auth/login
{ "email": "alice@example.com", "password": "secret123" }

→ 200
{
  "access_token": "eyJ...",
  "refresh_token": "dGhpc...",
  "token_type": "bearer",
  "athlete_id": "uuid-here"
}
```

Store both tokens client-side. Use `access_token` as Bearer on protected endpoints.
When `access_token` expires (15 min), call `/auth/refresh`.

---

## Flow: Refresh

```
POST /auth/refresh
{ "refresh_token": "dGhpc..." }

→ 200
{ "access_token": "eyJ...", "refresh_token": "NEW_TOKEN...", ... }
```

Strict rotation: old refresh token is immediately revoked. Store the new one.

---

## Flow: Logout

```
POST /auth/logout
Authorization: Bearer <access_token>
{ "refresh_token": "dGhpc..." }

→ 200 { "message": "Logged out" }
```

---

## Flow: Password Reset

```
POST /auth/forgot-password
{ "email": "alice@example.com" }
→ 200 (always, no email enumeration)

# User receives email with link: https://app/reset-password?token=<raw_token>

POST /auth/reset-password
{ "token": "<raw_token>", "new_password": "newpass123" }
→ 200

# All refresh tokens revoked — user must log in again
```

---

## curl Examples

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret123"}'

# Protected endpoint
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"

# Refresh
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'

# Logout
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

---

## TypeScript Client Example

```typescript
// Store tokens
localStorage.setItem('access_token', body.access_token);
localStorage.setItem('refresh_token', body.refresh_token);

// Authenticated request with auto-refresh
async function apiFetch(url: string, options: RequestInit = {}) {
  let token = localStorage.getItem('access_token');
  let res = await fetch(url, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${token}` },
  });

  if (res.status === 401) {
    // Access token expired — refresh
    const refreshRes = await fetch('/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: localStorage.getItem('refresh_token') }),
    });
    if (!refreshRes.ok) {
      // Refresh failed — redirect to login
      window.location.href = '/login';
      throw new Error('Session expired');
    }
    const tokens = await refreshRes.json();
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    token = tokens.access_token;
    // Retry original request
    res = await fetch(url, {
      ...options,
      headers: { ...options.headers, Authorization: `Bearer ${token}` },
    });
  }
  return res;
}
```

---

## Environment Variables

```bash
JWT_SECRET=<openssl rand -hex 32>     # NEVER commit
JWT_ACCESS_TTL_MINUTES=15
JWT_REFRESH_TTL_DAYS=30
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password        # Gmail: generate at myaccount.google.com/apppasswords
SMTP_FROM=noreply@resilio.app
APP_BASE_URL=http://localhost:3000
```

---

## V2 Roadmap

- Email verification on registration
- 2FA (TOTP via `pyotp`)
- Password hashing migration: bcrypt → argon2id
- Immediate access token revocation (Redis blocklist)
- OAuth2 social login (Google)

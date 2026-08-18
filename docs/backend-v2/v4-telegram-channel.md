# V4 Telegram Channel Design

**Status:** Approved by `docs/GOAL-V4-TEXT-COACH.md` and implemented as work package T2.

## Justification

Resilio V4 replaces the frozen client applications with a text-native coaching surface. Telegram is
the locked V4 channel because it provides an official Bot API, inline buttons, webhook delivery,
and a local long-polling development mode without adding another service or framework.

## Scope

T2 adds only the Telegram transport around the channel-neutral messaging core delivered in T1:

- a synchronous, 15-second `httpx` Bot API client;
- an HTML `MessagingChannel` adapter with a 4,096-character limit;
- an unauthenticated webhook authenticated by Telegram's secret-token header;
- background update processing, process-local update deduplication, and a typing action;
- a stoppable daemon long-poller for local development;
- lazy environment-based runtime composition and FastAPI lifespan wiring.

Approval tokens and callback resolution remain T3. Onboarding, connector links, Google Calendar,
weekly automation, and deployment automation remain later work packages.

## Data Flow

```text
Telegram webhook or poller
  -> validate/dedupe update
  -> fresh SessionLocal for that update
  -> TelegramUpdateProcessor
  -> MessagingGateway.handle_inbound("telegram", chat_id, text)
  -> CoordinatorService.dispatch(...)
  -> NotificationService
  -> TelegramChannel
  -> Telegram Bot API
```

The webhook never captures a request-scoped database session. The background task and polling loop
share the same synchronous update processor, and each update owns a fresh SQLAlchemy session.

## Bot API Client

The client supports `sendMessage`, `answerCallbackQuery`, `setWebhook`, `getUpdates`, and
`sendChatAction`. It retries only explicit Telegram 429 responses and sleeps for
`parameters.retry_after`; ambiguous transport and 5xx failures are not retried because retrying a
possibly accepted `sendMessage` can duplicate athlete-facing messages. Provider errors are
translated to sanitized exceptions so the bot token embedded in the request URL is never exposed.

## Formatting and Buttons

`TelegramChannel.format()` escapes raw HTML first and then converts only the supported subset:
`**bold**`, `*italic*`, inline code, and bullet prefixes. `send()` receives already-formatted text,
matching the T1 gateway and notification service contracts, and always uses `parse_mode="HTML"`.
Inline callback data is validated as 1-64 UTF-8 bytes; it contains opaque tokens only.

## Identity Bootstrap

Normal unknown senders may redeem a one-time T1 link code. For the locked single-athlete deployment,
`TELEGRAM_BOOTSTRAP_CHAT_ID` may also be linked idempotently to the existing
`ADMIN_ATHLETE_ID` on its first message. This path never creates an athlete and never reassigns an
existing messaging identity.

## Configuration

- `TELEGRAM_BOT_TOKEN`: BotFather token; required when Telegram mode is enabled.
- `TELEGRAM_MODE`: unset disables transport startup; `polling` starts the local daemon;
  `webhook` accepts secret-authenticated deliveries without a polling thread.
- `TELEGRAM_WEBHOOK_SECRET`: required for webhook requests.
- `TELEGRAM_BOOTSTRAP_CHAT_ID`: optional single-athlete bootstrap chat identifier.

Configuration is read lazily. Importing the application remains safe for existing tests and
deployments where Telegram is not enabled.

## Security and Reliability

- The webhook compares the secret header in constant time and has no JWT dependency by design.
- Incoming `update_id` values are recorded under a lock in a 1,000-entry LRU before background work
  is scheduled.
- Bot tokens, chat identifiers, callback identifiers, and message bodies are not logged.
- Polling has an explicit stop event and bounded shutdown; it is intended for a single local process.
- The in-memory LRU is process-local. Production V4 must use webhook mode and a single worker if
  cross-worker duplicate processing is unacceptable; durable/cross-process deduplication is outside
  the expressly approved T2 design.

## Verification

New tests use `respx.mock(base_url="https://api.telegram.org")`, never a global patch of
`httpx.Client`. They cover client payloads and 429 delays, HTML escaping and formatting, the 4,096
limit, button encoding, webhook secret rejection, background scheduling, update deduplication,
typing-before-dispatch, identity bootstrap/link-code redemption, polling offsets, and lifecycle
startup/shutdown.

T2 has no database schema change and therefore no Alembic revision.

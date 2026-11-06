# LanDo 🧠

An open-source, self-hosted AI personal assistant designed to reduce cognitive load and streamline daily task and event management.

## Project Structure

- `apps/mobile`: Cross-platform mobile app (React Native + Expo)
- `apps/api`: Backend service & AI agent orchestration (FastAPI + LangGraph)
- `packages/shared`: Shared TypeScript types and API client utilities
- `docs/`: System documentation and Architecture Decision Records (ADRs)

## Features

- **Event Management**: Create, reschedule, and absorb external reminders for events.
- **Location Management**: Add and manage user locations for geolocation-based reminders.
- **Settings**: Configure AI provider settings and manage user preferences.
- **Chat Integration**: Interact with LanDo through a chat interface for quick tasks and queries.
- **Advanced AI Capabilities**: Utilize advanced AI models for natural language processing, task automation, and more.
- **User Authentication**: Secure user authentication and authorization for a personalized experience.
- **Real-time Notifications**: Receive real-time notifications for important events and reminders.

## Prerequisites

- Docker & Docker Compose
- Node.js (v18+)
- Python (3.11+)
- Local Ollama instance

## API

The versioned API is mounted under `/api/v1`. FastAPI's interactive docs are
available at `/docs`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/auth/register` | Create an account |
| `POST` | `/api/v1/auth/login` | Get a JWT bearer token |
| `GET`, `PATCH` | `/api/v1/users/me` | Read or update the account language (`es`/`en`) |
| `POST` | `/api/v1/chat` | Send a message to the assistant |
| `GET`, `POST` | `/api/v1/events` | List or create events |
| `GET` | `/api/v1/events/{event_id}` | Get an event |
| `POST` | `/api/v1/events/{event_id}/reschedule` | Reschedule an event |
| `GET`, `POST` | `/api/v1/locations` | List or create saved locations |
| `GET`, `PUT` | `/api/v1/settings/llm` | Read or update LLM settings |
| `GET` | `/api/v1/settings/llm/ollama-models` | List local Ollama models |
| `POST` | `/api/v1/webhooks/location-trigger` | Receive a location trigger |
| `POST` | `/api/v1/webhooks/external-event` | Absorb external reminders |

Chat requests accept `message` and `thread_id` (or the shared client fields
`content` and `conversationId`). The response includes `reply`, `thread_id`,
and `tool_outputs`. Registration and login are public. All other user-facing
API routes require `Authorization: Bearer <access_token>`. Set a strong
`SECRET_KEY` (at least 32 characters) in production; JWTs expire after
`ACCESS_TOKEN_EXPIRE_MINUTES` (default 60). Event, location, LLM settings,
agent tools, vector-memory lookups, and chat checkpoints are scoped to the
authenticated account.

The shared-secret webhooks remain machine-authenticated and require the tenant
UUID in `user_id`; location triggers are accepted only for a location owned by
that user. External-event webhook bodies also include `user_id`. Send the
secret using `X-LanDo-Webhook-Secret`; the legacy `X-Webhook-Secret` header is
still accepted. Configure `WEBHOOK_SECRET` in the environment.

## Database migrations

The API does not create or alter tables at startup. Apply versioned SQL
migrations before starting the API. For a fresh database:

```sh
docker compose up -d db
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
  < apps/db/migrations/000_initial_schema.sql
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
  < apps/db/migrations/001_multi_tenant.sql
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
  < apps/db/migrations/002_localization_outbox.sql
```

For a database created with the previous schema, skip `000_initial_schema.sql`
and apply only `001_multi_tenant.sql` using the second command above.

Apply `002_localization_outbox.sql` after `001_multi_tenant.sql` on both fresh
and upgraded databases. It adds account language preference and a durable event
outbox. Run the migrations in order before starting the API.

This migration intentionally deletes existing event, reminder, location, and
LLM-settings rows because they have no trustworthy tenant owner. Back up the
database first if those records must be retained. New accounts start with
empty tenant data and receive default LLM settings on first access.

Provider API keys are encrypted at rest. In development, the encryption key is
derived from `SECRET_KEY`; production must set a dedicated
`LLM_SECRETS_ENCRYPTION_KEY` generated with
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
Back up this key separately from the database. For existing deployments, set
the key and run `docker compose exec -T api uv run python scripts/migrate_llm_keys.py`
once to encrypt plaintext keys in place. Do not lose or rotate the key without
decrypting/re-encrypting stored provider keys.

Chat language resolution uses the supported `Accept-Language` header first,
then the account preference, then Spanish. The mobile app sends the device or
user-selected language.

The outbox worker sends `event.created` and `event.rescheduled` payloads to
`N8N_WEBHOOK_URL` with `X-LanDo-Webhook-Secret` when configured. Configure an
n8n POST webhook at that URL (the default path is `/webhook/lando-events`).
Delivery is asynchronous and retries with capped exponential backoff; a failed
n8n call does not roll back an API operation.

## Docker Compose E2E check

After applying the database migrations above, start the stack and run the
connectivity smoke test:

```sh
docker compose up -d --build
docker compose exec -T api uv run python scripts/e2e_stack.py
```

The check inserts a temporary vector, runs a nearest-neighbor query, verifies
the API chat round-trip through Ollama and checks n8n health. It restores the
LLM settings that were active before the test and drops its temporary table
automatically.

## Mobile app

The Expo app uses `http://localhost:8001` as its default API URL. Set
`EXPO_PUBLIC_API_URL` before starting Expo when the API is hosted elsewhere
(for example, use the computer's LAN IP when testing on a physical device).
The app supports Expo Web and can be started with `npm run mobile -- --web`.
Native builds store the access token with Expo SecureStore; web builds keep it
in memory only, so a browser reload requires signing in again.

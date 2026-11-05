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
and `tool_outputs`. The location-trigger webhook accepts a JSON body containing
`user_id`, `location_id`, and a `trigger_type` of `LOCATION_ENTER` or
`LOCATION_EXIT`. Send the shared secret using `X-LanDo-Webhook-Secret`; the
legacy `X-Webhook-Secret` header is still accepted. Configure the secret with
the `WEBHOOK_SECRET` environment variable.

## Docker Compose E2E check

The API container initializes missing SQLModel tables and enables the
PostgreSQL `vector` extension at startup. To run the stack smoke test after
starting Compose:

```sh
docker compose up -d --build
docker compose exec -T api uv run python scripts/e2e_stack.py
```

The check inserts a temporary vector, runs a nearest-neighbor query, verifies
the API chat round-trip through Ollama and checks n8n health. It restores the
LLM settings that were active before the test and drops its temporary table
automatically.

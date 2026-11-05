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

## Prerequisites

- Docker & Docker Compose
- Node.js (v18+)
- Python (3.11+)
- Local Ollama instance

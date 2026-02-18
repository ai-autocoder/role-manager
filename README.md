# Role Manager

Role Manager is an open-source platform for managing rotating roles and publishing fair, explainable weekly schedules for teams.

Under the hood, Role Manager uses an event-driven pipeline to ingest updates (availability, preferences, qualifications, overrides), transform them into assignment inputs, and process recommendations reliably at scale.

## Product overview

Role Manager helps admins define teams, users, and roles, then generate and publish weekly assignments that are fair, auditable, and easy to adjust.

Core functionality:

- Manage **teams, users, roles**, and **weekly assignments**
- Keep an **assignment history** and expose "why" an assignment was suggested (transparency + fairness)
- Support both **manual assignment** and **automatic recommendations** (scoring + constraints)
- Provide a basic **admin area** (role definitions, qualifications, preferences, availability, overrides)

Benefits:

- **Fairness and transparency**: recommendation explainability plus an auditable assignment history
- **Efficiency**: automatic recommendations reduce scheduling effort week-to-week
- **Flexibility**: manual overrides support edge cases and last-minute changes
- **Data-driven insights**: surfaces trends in availability, workload balance, and role coverage
- **Scalability**: supports growth in teams, roles, and scheduling frequency without linear admin overhead

## What the project does

- Manages teams, users, roles, and weekly assignments
- Keeps assignment history and explainability signals
- Supports both manual assignment and automatic recommendations
- Adds a pipeline-first architecture to process raw events into durable outputs

## Tech stack

- **Python**: pipeline services and data transformation
- **RabbitMQ**: messaging and asynchronous processing
- **Redis**: caching, short-lived state, and deduplication
- **MongoDB**: durable storage for core entities and assignment history
- **Bash**: automation for setup and operations
- **Docker**: local containerized environment and service orchestration
- **Kubernetes (optional extension)**: worker scaling and deployment patterns

## Quickstart (target workflow)

The pipeline and worker services are still being implemented. This section describes the intended developer workflow once the first end-to-end slice is in place.

1. Clone and install dependencies
   - `npm install`
   - `cd backend && python -m venv venv && .\venv\Scripts\pip install -r requirements.txt`
2. Start infra services (RabbitMQ, Redis, MongoDB)
   - `docker compose up -d`
3. Start the API
   - `npm run start@backend`
4. Start the worker
   - `cd backend && .\venv\Scripts\python -m app.worker`
5. Publish an event (example)
   - `curl -X POST http://localhost:8000/events -H "Content-Type: application/json" -d @event.json`

## Architecture

```
UI/Admin Actions
   |
   v
FastAPI API (ingest/validate)
   |
   v
RabbitMQ Exchange -> Queue(s) -> Worker(s)
   |                               |
   v                               v
Redis (dedup/state/cache)      Transform/Score
   |                               |
   +--------------> MongoDB <-------+
                   (history/audit)
```

## Message contract (example)

Role Manager is designed around versioned, self-describing events. This is an example payload shape (field names may evolve as endpoints land):

```json
{
  "schema_version": 1,
  "event_id": "01JED0R66R0B3S6QH8G2H5M2TZ",
  "event_type": "availability.updated",
  "occurred_at": "2026-02-18T10:45:00Z",
  "producer": "api",
  "correlation_id": "c8b7f6d2-8f52-46e1-9c55-0d3b1c3a0a0f",
  "team_id": "team_123",
  "payload": {
    "user_id": "user_456",
    "week_start": "2026-02-23",
    "availability": [
      {"day": "mon", "status": "unavailable"},
      {"day": "tue", "status": "available"}
    ],
    "reason": "PTO"
  }
}
```

## Reliability (target behavior)

- **Delivery semantics**: at-least-once processing from RabbitMQ; workers acknowledge messages only after successful handling.
- **Retries**: failed messages are retried with backoff up to a configured max attempt count.
- **DLQ**: messages that exceed max attempts are routed to a dead-letter queue for inspection and replay.
- **Idempotency/dedup**: `event_id` is treated as an idempotency key; workers use Redis to record processed IDs (TTL-backed) to safely handle redeliveries.
- **Poison messages**: invalid payloads are rejected early (API validation) or quarantined (DLQ) with structured error context.

## Observability (baseline)

- **Structured logs**: JSON logs for API and worker, including `event_id`, `event_type`, `team_id`, and `correlation_id`.
- **Health checks**: API health endpoint exposes service readiness (and database connectivity where applicable).
- **Operational visibility (planned)**: queue depth, worker throughput, retry/DLQ counts, and processing latency metrics.

## Engineering focus

- High throughput and low latency
- Fault tolerance and high availability
- Dead-letter queue and retry handling
- Idempotent processing patterns
- Observability and operational robustness

## Design goals

- Keep scheduling decisions explainable and auditable
- Make weekly operations fast for admins and predictable for teams
- Ensure the pipeline behaves safely under load and failure scenarios

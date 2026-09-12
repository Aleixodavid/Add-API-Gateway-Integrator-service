# API Gateway Integrator

A lightweight, resilient API Gateway built with Python and Flask, implementing traffic control and fault-tolerance patterns for distributed systems.

## Key Features

- **Circuit Breaker State Machine**: Implements `CLOSED`, `OPEN`, and `HALF_OPEN` states to prevent cascading failures.
- **Token Bucket Rate Limiter**: Per-client IP rate limiting with continuous token refill.
- **Exponential Backoff with Jitter**: Automated request retry handler to handle transient network issues safely.
- **Decoupled Architecture**: Clean separation between routing, resilience policies, and HTTP handlers.

## Architecture & Design Patterns

### Circuit Breaker (`circuit_breaker.py`)
Tracks consecutive failures. If failures reach `failure_threshold` (default: 5), the circuit transitions from `CLOSED` to `OPEN`, immediately short-circuiting downstream requests. After `recovery_timeout` (default: 30s), it enters `HALF_OPEN` to test downstream availability.

### Token Bucket Rate Limiter (`rate_limiter.py`)
Enforces request rate limits using a sliding window token bucket (default: 60 tokens capacity, 10 tokens/sec refill rate).

### Retry Handler (`retry_handler.py`)
Wraps execution in exponential backoff ($0.5s \times 2^{n-1}$) with randomized jitter to prevent thundering herd problems.

## Configuration & Security

Authentication credentials and secrets are managed via environment variables:
- `AUTH_USERNAME` (default placeholder in `config.json`: `YOUR_USERNAME_HERE`)
- `AUTH_PASSWORD` (default placeholder in `config.json`: `YOUR_PASSWORD_HERE`)

## API Specification

- `GET /api/health` — Service health check and circuit state.
- `POST /api/proxy` — Main proxy endpoint with rate limiting and circuit breaker protection.
- `GET /api/circuit-breaker/status` — Inspect current state machine metrics.
- `POST /api/circuit-breaker/reset` — Manual reset trigger to restore `CLOSED` state.
- `GET /api/rate-limit/stats` — Active client stats and token bucket metrics.

## Running Tests

```bash
python -m pytest tests/ -v
```

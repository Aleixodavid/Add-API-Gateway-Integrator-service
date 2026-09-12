"""
API Gateway Integrator — Microsserviço de Borda (Edge Service)
Arquitetura: Flask RESTful API Gateway com orquestração de chamadas,
Rate Limiting, Retry com Backoff Exponencial e Circuit Breaker.

Credenciais de demonstração: admin / admin
"""

import os
import json
import time
import uuid
import logging
from functools import wraps
from flask import Flask, request, jsonify, g

from circuit_breaker import CircuitBreaker
from rate_limiter import TokenBucketRateLimiter
from retry_handler import retry_with_backoff

# ── Configuração ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

config = load_config()

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)
logger = logging.getLogger("APIGateway")

# ── Flask App ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = config.get("secret_key", "gateway_demo_secret_2026")

# ── Instâncias dos padrões de resiliência ────────────────────────────────────
rate_limiter = TokenBucketRateLimiter(
    capacity=config.get("rate_limit_capacity", 60),
    refill_rate=config.get("rate_limit_refill_rate", 10)
)

circuit_breakers = {
    "service_a": CircuitBreaker(name="ServiceA", failure_threshold=5, recovery_timeout=30),
    "service_b": CircuitBreaker(name="ServiceB", failure_threshold=3, recovery_timeout=60),
}


# ── Middleware de Autenticação ────────────────────────────────────────────────

def require_auth(f):
    """Autenticação básica: admin/admin (demonstração)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth:
            data = request.get_json(silent=True) or {}
            user = data.get("username") or request.headers.get("X-Username", "")
            pwd = data.get("password") or request.headers.get("X-Password", "")
        else:
            user, pwd = auth.username, auth.password

        demo_user = config.get("auth_username", "admin")
        demo_pass = config.get("auth_password", "admin")

        if user != demo_user or pwd != demo_pass:
            logger.warning(f"[Auth] Acesso negado para usuário: '{user}'")
            return jsonify({"error": "Unauthorized", "message": "Invalid credentials"}), 401

        g.username = user
        g.correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        return f(*args, **kwargs)
    return decorated


# ── Middleware de Rate Limiting ───────────────────────────────────────────────

@app.before_request
def check_rate_limit():
    client_ip = request.remote_addr
    if not rate_limiter.consume(client_ip):
        logger.warning(f"[RateLimit] IP {client_ip} excedeu limite de requisições")
        return jsonify({
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Try again later.",
            "retry_after_seconds": rate_limiter.get_retry_after(client_ip)
        }), 429


# ── Simulação de Serviços Externos ───────────────────────────────────────────

def call_external_service_a(payload: dict) -> dict:
    """Simula chamada a serviço externo A (80% sucesso)."""
    import random
    if random.random() < 0.2:
        raise ConnectionError("Service A temporarily unavailable")
    return {"service": "A", "status": "ok", "data": payload, "timestamp": time.time()}


def call_external_service_b(payload: dict) -> dict:
    """Simula chamada a serviço externo B (90% sucesso)."""
    import random
    if random.random() < 0.1:
        raise TimeoutError("Service B timeout")
    return {"service": "B", "status": "ok", "data": payload, "timestamp": time.time()}


# ── Rotas ────────────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "service": "API Gateway Integrator",
        "version": "1.0.0",
        "circuit_breakers": {
            name: cb.get_status() for name, cb in circuit_breakers.items()
        },
        "rate_limiter": rate_limiter.get_stats(),
    })


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    user = data.get("username", "")
    pwd = data.get("password", "")

    if user == config.get("auth_username", "admin") and pwd == config.get("auth_password", "admin"):
        token = str(uuid.uuid4())
        logger.info(f"[Auth] Login efetuado: {user}")
        return jsonify({"status": "authenticated", "token": token, "user": user})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/orchestrate", methods=["POST"])
@require_auth
def orchestrate():
    """
    Endpoint principal: orquestra chamadas para múltiplos serviços
    com Circuit Breaker e Retry automático.
    """
    data = request.get_json(silent=True) or {}
    correlation_id = g.correlation_id
    target = data.get("target_service", "service_a")

    logger.info(f"[Orchestrate] CID={correlation_id} | Target: {target} | User: {g.username}")

    cb = circuit_breakers.get(target)
    if not cb:
        return jsonify({"error": f"Unknown service: {target}"}), 400

    if not cb.allow_request():
        return jsonify({
            "error": "Circuit Open",
            "message": f"Service '{target}' is temporarily unavailable (circuit breaker open)",
            "circuit_status": cb.get_status(),
            "correlation_id": correlation_id,
        }), 503

    try:
        service_fn = call_external_service_a if target == "service_a" else call_external_service_b
        result = retry_with_backoff(
            fn=lambda: service_fn(data.get("payload", {})),
            max_retries=config.get("max_retries", 3),
            base_delay=config.get("base_delay", 0.5),
        )
        cb.record_success()
        return jsonify({
            "status": "ok",
            "correlation_id": correlation_id,
            "result": result,
            "circuit_status": cb.get_status(),
        })
    except Exception as e:
        cb.record_failure()
        logger.error(f"[Orchestrate] CID={correlation_id} | Falha: {e}")
        return jsonify({
            "error": "Service Unavailable",
            "message": str(e),
            "correlation_id": correlation_id,
            "circuit_status": cb.get_status(),
        }), 503


@app.route("/api/circuit-breaker/status")
@require_auth
def cb_status():
    return jsonify({
        name: cb.get_status() for name, cb in circuit_breakers.items()
    })


@app.route("/api/circuit-breaker/reset", methods=["POST"])
@require_auth
def cb_reset():
    data = request.get_json(silent=True) or {}
    target = data.get("service", "")
    cb = circuit_breakers.get(target)
    if not cb:
        return jsonify({"error": f"Unknown service: {target}"}), 400
    cb.reset()
    return jsonify({"status": "reset", "service": target})


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  API Gateway Integrator — Microsserviço de Borda")
    print("  Credenciais: admin / admin")
    print("  Endpoint: http://127.0.0.1:5001")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5001, debug=False)

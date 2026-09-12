"""
Token Bucket Rate Limiter — Controle de taxa de requisições por IP.
Implementação thread-safe com janela deslizante.
"""

import time
import threading
import logging

logger = logging.getLogger("RateLimiter")


class TokenBucketRateLimiter:
    """
    Rate Limiter baseado no algoritmo Token Bucket.

    Args:
        capacity:    Número máximo de tokens (burst máximo)
        refill_rate: Tokens adicionados por segundo
    """

    def __init__(self, capacity: int = 60, refill_rate: float = 10.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._buckets = {}  # {client_id: {"tokens": float, "last_refill": float}}
        self._lock = threading.Lock()
        self._total_allowed = 0
        self._total_denied = 0

    def _get_or_create_bucket(self, client_id: str) -> dict:
        if client_id not in self._buckets:
            self._buckets[client_id] = {
                "tokens": float(self.capacity),
                "last_refill": time.time(),
            }
        return self._buckets[client_id]

    def _refill(self, bucket: dict):
        now = time.time()
        elapsed = now - bucket["last_refill"]
        tokens_to_add = elapsed * self.refill_rate
        bucket["tokens"] = min(self.capacity, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now

    def consume(self, client_id: str, tokens: int = 1) -> bool:
        """
        Tenta consumir tokens. Retorna True se permitido, False se rate limited.
        """
        with self._lock:
            bucket = self._get_or_create_bucket(client_id)
            self._refill(bucket)

            if bucket["tokens"] >= tokens:
                bucket["tokens"] -= tokens
                self._total_allowed += 1
                return True
            else:
                self._total_denied += 1
                logger.debug(f"[RateLimit] {client_id} denied ({bucket['tokens']:.1f} tokens remaining)")
                return False

    def get_retry_after(self, client_id: str) -> float:
        """Retorna segundos estimados até que tokens estejam disponíveis."""
        with self._lock:
            bucket = self._get_or_create_bucket(client_id)
            if bucket["tokens"] >= 1:
                return 0.0
            tokens_needed = 1.0 - bucket["tokens"]
            return round(tokens_needed / self.refill_rate, 2)

    def get_stats(self) -> dict:
        return {
            "capacity": self.capacity,
            "refill_rate_per_second": self.refill_rate,
            "active_clients": len(self._buckets),
            "total_allowed": self._total_allowed,
            "total_denied": self._total_denied,
        }

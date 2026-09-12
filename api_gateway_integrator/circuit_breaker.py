"""
Circuit Breaker Pattern — Implementação pura para tolerância a falhas.

Estados:
  CLOSED    → Operação normal, todas as requisições passam
  OPEN      → Serviço indisponível, requisições bloqueadas
  HALF_OPEN → Teste de recuperação, uma requisição de prova passa

Transições:
  CLOSED → OPEN:      Quando falhas atingem failure_threshold
  OPEN → HALF_OPEN:   Após recovery_timeout segundos
  HALF_OPEN → CLOSED: Se a requisição de prova for bem-sucedida
  HALF_OPEN → OPEN:   Se a requisição de prova falhar
"""

import time
import threading
import logging

logger = logging.getLogger("CircuitBreaker")


class CircuitBreakerOpenError(Exception):
    """Exceção lançada quando o circuit breaker está aberto."""
    pass


class CircuitBreaker:
    """
    Implementação thread-safe do padrão Circuit Breaker.

    Args:
        name:              Nome identificador do circuito
        failure_threshold: Número de falhas consecutivas para abrir o circuito
        recovery_timeout:  Segundos para transitar de OPEN para HALF_OPEN
        success_threshold: Sucessos consecutivos em HALF_OPEN para fechar o circuito
    """

    STATE_CLOSED    = "CLOSED"
    STATE_OPEN      = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    def __init__(self, name: str = "default",
                 failure_threshold: int = 5,
                 recovery_timeout: float = 30.0,
                 success_threshold: int = 2):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = self.STATE_CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._total_requests = 0
        self._total_failures = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.STATE_OPEN:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = self.STATE_HALF_OPEN
                    self._success_count = 0
                    logger.info(f"[CB:{self.name}] OPEN → HALF_OPEN (recovery timeout elapsed)")
            return self._state

    def allow_request(self) -> bool:
        """Verifica se a requisição é permitida no estado atual."""
        current = self.state
        if current == self.STATE_CLOSED:
            return True
        elif current == self.STATE_HALF_OPEN:
            return True  # Permite requisição de prova
        else:  # OPEN
            return False

    def record_success(self):
        """Registra uma requisição bem-sucedida."""
        with self._lock:
            self._total_requests += 1
            if self._state == self.STATE_HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = self.STATE_CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(f"[CB:{self.name}] HALF_OPEN → CLOSED (recovery confirmed)")
            elif self._state == self.STATE_CLOSED:
                self._failure_count = 0  # Reset de falhas consecutivas

    def record_failure(self):
        """Registra uma falha."""
        with self._lock:
            self._total_requests += 1
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == self.STATE_HALF_OPEN:
                self._state = self.STATE_OPEN
                logger.warning(f"[CB:{self.name}] HALF_OPEN → OPEN (probe request failed)")
            elif self._state == self.STATE_CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._state = self.STATE_OPEN
                    logger.warning(
                        f"[CB:{self.name}] CLOSED → OPEN "
                        f"(failures: {self._failure_count}/{self.failure_threshold})"
                    )

    def reset(self):
        """Reset manual do circuit breaker."""
        with self._lock:
            self._state = self.STATE_CLOSED
            self._failure_count = 0
            self._success_count = 0
            logger.info(f"[CB:{self.name}] Manual reset → CLOSED")

    def get_status(self) -> dict:
        """Retorna status detalhado do circuit breaker."""
        current = self.state
        return {
            "name": self.name,
            "state": current,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_s": self.recovery_timeout,
            "total_requests": self._total_requests,
            "total_failures": self._total_failures,
            "last_failure_ago_s": round(time.time() - self._last_failure_time, 1) if self._last_failure_time else None,
        }

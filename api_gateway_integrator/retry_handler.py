"""
Retry Handler — Retentativa com Backoff Exponencial e Jitter.
"""

import time
import random
import logging

logger = logging.getLogger("RetryHandler")


def retry_with_backoff(fn, max_retries: int = 3, base_delay: float = 0.5,
                       max_delay: float = 30.0, jitter: bool = True):
    """
    Executa fn() com retentativa automática e backoff exponencial.

    Args:
        fn:          Callable a ser executado
        max_retries: Número máximo de tentativas
        base_delay:  Delay base em segundos (dobra a cada tentativa)
        max_delay:   Delay máximo em segundos
        jitter:      Se True, adiciona jitter aleatório para evitar thundering herd

    Returns:
        Resultado de fn() em caso de sucesso

    Raises:
        Última exceção se todas as tentativas falharem
    """
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            result = fn()
            if attempt > 1:
                logger.info(f"[Retry] Sucesso na tentativa {attempt}/{max_retries}")
            return result
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(
                    f"[Retry] Todas as {max_retries} tentativas falharam. "
                    f"Última exceção: {e}"
                )
                raise

            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"[Retry] Tentativa {attempt}/{max_retries} falhou: {e}. "
                f"Aguardando {delay:.2f}s antes da próxima tentativa..."
            )
            time.sleep(delay)

    raise last_exception

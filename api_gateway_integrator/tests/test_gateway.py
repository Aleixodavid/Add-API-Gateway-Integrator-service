"""Testes unitários do API Gateway Integrator."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from circuit_breaker import CircuitBreaker
from rate_limiter import TokenBucketRateLimiter
from retry_handler import retry_with_backoff


class TestCircuitBreaker:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        assert cb.state == "CLOSED"
        assert cb.allow_request() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=60)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.allow_request() is False

    def test_transitions_to_half_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"
        import time; time.sleep(0.15)
        assert cb.state == "HALF_OPEN"
        assert cb.allow_request() is True

    def test_recovers_from_half_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1, success_threshold=1)
        cb.record_failure()
        cb.record_failure()
        import time; time.sleep(0.15)
        assert cb.state == "HALF_OPEN"
        cb.record_success()
        assert cb.state == "CLOSED"

    def test_reset(self):
        cb = CircuitBreaker(name="test", failure_threshold=1)
        cb.record_failure()
        assert cb.state == "OPEN"
        cb.reset()
        assert cb.state == "CLOSED"

    def test_get_status(self):
        cb = CircuitBreaker(name="test_status")
        status = cb.get_status()
        assert status["name"] == "test_status"
        assert status["state"] == "CLOSED"


class TestRateLimiter:
    def test_allows_within_capacity(self):
        rl = TokenBucketRateLimiter(capacity=5, refill_rate=1)
        for _ in range(5):
            assert rl.consume("test_client") is True

    def test_denies_over_capacity(self):
        rl = TokenBucketRateLimiter(capacity=2, refill_rate=0.01)
        rl.consume("test_client")
        rl.consume("test_client")
        assert rl.consume("test_client") is False

    def test_refills_over_time(self):
        rl = TokenBucketRateLimiter(capacity=1, refill_rate=100)
        rl.consume("test_client")
        assert rl.consume("test_client") is False
        import time; time.sleep(0.05)
        assert rl.consume("test_client") is True

    def test_stats(self):
        rl = TokenBucketRateLimiter(capacity=10)
        rl.consume("a")
        stats = rl.get_stats()
        assert stats["active_clients"] == 1
        assert stats["total_allowed"] == 1


class TestRetryHandler:
    def test_succeeds_on_first_try(self):
        result = retry_with_backoff(lambda: "ok", max_retries=3)
        assert result == "ok"

    def test_retries_on_failure(self):
        counter = {"n": 0}
        def flaky():
            counter["n"] += 1
            if counter["n"] < 3:
                raise ValueError("fail")
            return "success"
        result = retry_with_backoff(flaky, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert counter["n"] == 3

    def test_raises_after_max_retries(self):
        def always_fail():
            raise RuntimeError("permanent failure")
        with pytest.raises(RuntimeError):
            retry_with_backoff(always_fail, max_retries=2, base_delay=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

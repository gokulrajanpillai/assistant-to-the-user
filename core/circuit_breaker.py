"""
ATHU Core - Circuit Breaker
Prevents cascading failures by tracking module health and applying backoff.
"""

import asyncio
import logging
import time
from enum import Enum
from functools import wraps

logger = logging.getLogger("athu.circuit_breaker")


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing — requests blocked
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for a single module/service.
    States: CLOSED -> OPEN (on failure threshold) -> HALF_OPEN (after timeout) -> CLOSED/OPEN
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and (time.monotonic() - self._last_failure_time) >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(f"Circuit '{self.name}' -> HALF_OPEN (testing recovery)")
        return self._state

    def is_available(self) -> bool:
        return self.state != CircuitState.OPEN

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(f"Circuit '{self.name}' -> CLOSED (recovered)")
        elif self.state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                f"Circuit '{self.name}' -> OPEN after {self._failure_count} failures. "
                f"Will retry in {self.recovery_timeout}s"
            )

    def reset(self):
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None

    def __repr__(self):
        return f"CircuitBreaker(name={self.name!r}, state={self.state.value}, failures={self._failure_count})"


class CircuitBreakerRegistry:
    """Registry of circuit breakers for all modules."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name)
        return self._breakers[name]

    def get_status(self) -> dict:
        return {name: cb.state.value for name, cb in self._breakers.items()}

    def reset_all(self):
        for cb in self._breakers.values():
            cb.reset()


# Global registry
registry = CircuitBreakerRegistry()


def with_circuit_breaker(module_name: str, fallback=None):
    """Decorator to wrap an async function with circuit breaker logic."""
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            cb = registry.get(module_name)
            if not cb.is_available():
                logger.warning(f"Circuit '{module_name}' is OPEN. Skipping call.")
                if fallback is not None:
                    return fallback
                raise RuntimeError(f"Module '{module_name}' is currently unavailable (circuit open).")
            try:
                result = await fn(*args, **kwargs)
                cb.record_success()
                return result
            except Exception as e:
                cb.record_failure()
                raise
        return wrapper
    return decorator

"""
Exponential-backoff retry decorator for AI API calls in GRIDSENSE.
Handles transient network errors and rate limits without crashing the daemon.
"""
from __future__ import annotations
import time
import functools
from app.logging_config import get_logger

log = get_logger(__name__)


def with_retry(max_attempts: int = 3, base_delay: float = 2.0, exceptions: tuple = (Exception,)):
    """
    Decorator: retry the function up to max_attempts times with exponential backoff.
    - Attempt 1: immediate
    - Attempt 2: wait base_delay seconds
    - Attempt 3: wait base_delay * 2 seconds
    After all attempts are exhausted, re-raises the last exception.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        log.warning(
                            "API call failed, retrying",
                            extra={
                                "attempt": attempt,
                                "max_attempts": max_attempts,
                                "delay_s": delay,
                                "error": str(e),
                                "func": func.__name__,
                            }
                        )
                        time.sleep(delay)
                    else:
                        log.error(
                            "API call failed after all retries",
                            extra={
                                "attempt": attempt,
                                "error": str(e),
                                "func": func.__name__,
                            }
                        )
            raise last_exc
        return wrapper
    return decorator

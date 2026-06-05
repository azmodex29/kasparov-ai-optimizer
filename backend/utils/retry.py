import time
import random
from typing import Callable, Any


def with_retry(
    func: Callable,
    *args,
    max_attempts: int = 2,
    delay_s: float = 1.5,
    fallback: Any = None,
    label: str = "function",
    **kwargs
) -> Any:
    """
    Call func with args/kwargs.
    Retry once on failure.
    Return fallback if all attempts fail.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            result = func(*args, **kwargs)
            if attempt > 1:
                print(f"[retry] {label} succeeded on attempt {attempt}")
            return result

        except Exception as e:
            print(f"[retry] {label} attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                # Small jitter to avoid hammering API
                sleep_time = delay_s + random.uniform(0, 0.5)
                print(f"[retry] waiting {round(sleep_time, 2)}s before retry...")
                time.sleep(sleep_time)
            else:
                print(f"[retry] {label} all attempts failed — using fallback")

    return fallback
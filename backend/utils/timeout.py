import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)


async def run_with_timeout(func, *args, timeout_s: int = 30, **kwargs):
    """
    Run a sync function with a timeout.
    Returns result or raises TimeoutError.
    """
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                functools.partial(func, *args, **kwargs)
            ),
            timeout=timeout_s
        )
        return result
    except asyncio.TimeoutError:
        raise TimeoutError(f"{func.__name__} exceeded {timeout_s}s timeout")
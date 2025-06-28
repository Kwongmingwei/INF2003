import time
import logging
from functools import wraps

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("perf_logger")

def log_duration(name=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            label = name or func.__name__
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            logger.info(f"[PERF] {label} took {end - start:.3f}s")
            return result
        return wrapper
    return decorator
import asyncio
import json
import os
import pickle
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def cache_results(name=None):
    """
    Decorator to cache the results of a function based on its name.
    The cache is stored in a file named after the function.
    Uses pickle for serialization.
    """
    def decorator(func):
        nonlocal name
        if name is None:
            name = func.__name__
        # if func is synchronous, use this wrapper
        if not asyncio.iscoroutinefunction(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                skip_cache = False
                if 'skip_cache' in kwargs:
                    skip_cache = kwargs.pop('skip_cache')

                cache_file = f"{name}_cache.pkl"
                if os.path.exists(cache_file):
                    with open(cache_file, 'rb') as f:
                        cache = pickle.load(f)
                else:
                    cache = {}

                key = json.dumps((args, kwargs), sort_keys=True)
                if not skip_cache and key in cache:
                    log.debug(f"Cache hit for {name} with args: {args}, kwargs: {kwargs}")
                    return cache[key]

                log.debug(f"Cache miss for {name} with args: {args}, kwargs: {kwargs}")
                result = func(*args, **kwargs)
                cache[key] = result

                with open(cache_file, 'wb') as f:
                    pickle.dump(cache, f)

                return result
            return wrapper
        else:
            # if func is asynchronous, use this wrapper
            @wraps(func)
            async def awrapper(*args, **kwargs):
                skip_cache = False
                if 'skip_cache' in kwargs:
                    skip_cache = kwargs.pop('skip_cache')

                cache_file = f"{name}_cache.pkl"
                if os.path.exists(cache_file):
                    with open(cache_file, 'rb') as f:
                        cache = pickle.load(f)
                else:
                    cache = {}

                key = json.dumps((args, kwargs), sort_keys=True)
                if not skip_cache and key in cache:
                    log.debug(f"Cache hit for {name} with args: {args}, kwargs: {kwargs}")
                    return cache[key]

                log.debug(f"Cache miss for {name} with args: {args}, kwargs: {kwargs}")
                result = await func(*args, **kwargs)
                cache[key] = result

                with open(cache_file, 'wb') as f:
                    pickle.dump(cache, f)

                return result
            return awrapper

    # if the parameter is a function, we called this without parentheses
    # so just run the decorator directly
    if callable(name):
        func = name
        name = func.__name__
        return decorator(func)

    return decorator
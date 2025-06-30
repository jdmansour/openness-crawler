import asyncio
import json
import os
import pickle
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class CacheMiss:
    pass
CACHE_MISS = CacheMiss()

class Unset:
    pass
UNSET = Unset()

def cache_results(name=None, dummy_on_miss=UNSET):
    """
    Decorator to cache the results of a function based on its name.
    The cache is stored in a file named after the function.
    Uses pickle for serialization.
    """
    def decorator(func):
        nonlocal name
        if name is None:
            name = func.__name__

        cache_file = f"{name}_cache.pkl"

        def cache_get(args, kwargs):
            skip_cache = False
            if 'skip_cache' in kwargs:
                skip_cache = kwargs.pop('skip_cache')

            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    cache = pickle.load(f)
            else:
                cache = {}

            key = json.dumps((args, kwargs), sort_keys=True)
            if skip_cache:
                log.debug(f"Skipping cache for {name} with args: {args}, kwargs: {kwargs}")
                return cache, key, CACHE_MISS
    
            if key in cache:
                log.debug(f"Cache hit for {name} with args: {args}, kwargs: {kwargs}")
                return cache, key, cache[key]

            log.debug(f"Cache miss for {name} with args: {args}, kwargs: {kwargs}")
            return cache, key, CACHE_MISS

        def cache_store(cache, key, result):
            cache[key] = result

            with open(cache_file, 'wb') as f:
                pickle.dump(cache, f)

            return result

        # if func is synchronous, use this wrapper
        if not asyncio.iscoroutinefunction(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache, key, result = cache_get(args, kwargs)                
                if result is CACHE_MISS:
                    if dummy_on_miss is not UNSET:
                        log.debug(f"Returning dummy value for {name} with args: {args}, kwargs: {kwargs}")
                        return dummy_on_miss
                    result = func(*args, **kwargs)
                    cache_store(cache, key, result)
                return result
            return wrapper
        else:
            # if func is asynchronous, use this wrapper
            @wraps(func)
            async def awrapper(*args, **kwargs):
                cache, key, result = cache_get(args, kwargs)
                if result is CACHE_MISS:
                    if dummy_on_miss is not UNSET:
                        log.debug(f"Returning dummy value for {name} with args: {args}, kwargs: {kwargs}")
                        return dummy_on_miss
                    result = await func(*args, **kwargs)
                    cache_store(cache, key, result)
                return result
            return awrapper

    # if the parameter is a function, we called this without parentheses
    # so just run the decorator directly
    if callable(name):
        func = name
        name = func.__name__
        return decorator(func)

    return decorator
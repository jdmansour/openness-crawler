import asyncio
import json
import os
import pickle
from functools import wraps
import logging
from utils import sync_async_decorator

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class Unset:
    pass
UNSET = Unset()


def cache_results(name=None, dummy_on_miss=UNSET):
    """
    Decorator to cache the results of a function based on its name.
    The cache is stored in a file named after the function.
    Uses pickle for serialization.
    """
    @sync_async_decorator
    def decorator(func, *args, **kwargs):
        nonlocal name
        if name is None:
            name = func.__name__

        cache_file = f"{name}_cache.pkl"

        skip_cache = kwargs.pop('skip_cache', False)
        cache_return_info = kwargs.pop('cache_return_info', False)
        def add_info(value, info):
            if cache_return_info:
                return (value, info)
            return value

        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                cache = pickle.load(f)
        else:
            cache = {}

        key = json.dumps((args, kwargs), sort_keys=True)

        if not skip_cache and key in cache:
            log.debug(f"Cache hit for {name} with args: {args}, kwargs: {kwargs}")
            result = cache[key]
            log.debug("Returning cached result")
            return add_info(result, 'hit')
        else:
            if skip_cache:
                log.debug(f"Skipping cache for {name} with args: {args}, kwargs: {kwargs}")
            else:
                log.debug(f"Cache miss for {name} with args: {args}, kwargs: {kwargs}")

            if dummy_on_miss is not UNSET:
                log.debug(f"Returning dummy value for {name} with args: {args}, kwargs: {kwargs}")
                return add_info(dummy_on_miss, 'dummy')
            
            # call the wrapped function
            result = yield args, kwargs
        
            # store the result in cache
            cache[key] = result
            with open(cache_file, 'wb') as f:
                pickle.dump(cache, f)

            return add_info(result, 'skip' if skip_cache else 'miss')

    # if the parameter is a function, we called this without parentheses
    # so just run the decorator directly
    if callable(name):
        func = name
        name = func.__name__
        return decorator(func)

    return decorator
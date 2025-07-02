
import json
import os

from pydantic import BaseModel

from utils import sync_async_decorator


@sync_async_decorator
def record_results(func, *args, **kwargs):
    """
    Decorator to record the results of a function call.
    For a function like `google_search`, the results are of the form:
    {
        "cache_hit": false,
        "args": {
            "query": "site:example.com moodle"
        },
        "return": [
            "https://example.com/moodle",
            "https://example.com/moodle2"
        ]
    }
    For each run of the program, a new file is created:
    `results/<function_name>_<timestamp>.json`
    """
    kwargs['cache_return_info'] = True
    # call wrapped function
    inner_result = yield args, kwargs
    print("Inner result:", inner_result)
    result, cache_hit = inner_result

    if isinstance(result, BaseModel):
        # if the result is a Pydantic model, convert it to a dict
        result_dict = result.model_dump(mode="json")
    else:
        result_dict = result

    # prepare the result data
    result_data = {
        "cache_hit": cache_hit,
        "args": {k: v for k, v in zip(func.__code__.co_varnames, args)},
        "return": result_dict
    }

    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    # create a unique filename based on the function name and execution time
    filename = f"{results_dir}/{func.__name__}_{record_results.init_time}.json"

    # write the result to a file
    with open(filename, 'a', encoding='utf-8') as f:
        # if result_data is a Pydantic model, convert it to a dict
        json.dump(result_data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return result


if not hasattr(record_results, 'init_time'):
    record_results.init_time = time.strftime("%Y%m%d_%H%M%S")
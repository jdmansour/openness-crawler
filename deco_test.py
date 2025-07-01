
import time
import asyncio

from utils import sync_async_decorator


# def decorate_sync_async(decorating_context, func):
#     if asyncio.iscoroutinefunction(func):
#         async def decorated(*args, **kwargs):
#             with decorating_context():
#                 return (await func(*args, **kwargs))
#     else:
#         def decorated(*args, **kwargs):
#             with decorating_context():
#                 return func(*args, **kwargs)

#     return functools.wraps(func)(decorated)

# def mydecorator(myfunc):
#     return decorate_sync_async(decorator_logic, myfunc)

@sync_async_decorator
def log_calls(func, *args, **kwargs):
    print(f"Function `{func.__name__}` called with args: {args}, kwargs: {kwargs}")
    x, y = args
    x += 1
    args = (x, y)
    print(f"Modified args: {args}, kwargs: {kwargs}")
    result = yield args, kwargs
    print(f"Function returned: {result}")

@sync_async_decorator
def stops_if_even(func, x):
    print(f"Function `{func.__name__}` called with x: {x}")
    if x % 2 == 0:
        print(f"Stopping execution because {x} is even")
        return 0
    result = yield [x], {}
    print(f"Function returned: {result}")

@log_calls
def myfunc(a: int, b: int) -> int:
    """
    A simple function that adds two numbers.
    """
    print("Executing myfunc")
    return a + b

@log_calls
async def myasyncfunc(a, b):
    """
    An asynchronous function that adds two numbers.
    """
    print("Executing myasyncfunc")
    await asyncio.sleep(1)
    return a + b

@stops_if_even
def hello(x):
    return f"Hello {x}"

def main():
    # result = myfunc(1, 2)
    # print(f"Result of myfunc: {result}")
    # print("myfunc:", myfunc)
    # print("myfunc.__name__:", myfunc.__name__)
    # print("myfunc.__doc__:", myfunc.__doc__)
    # print("myfunc.__wrapped__:", myfunc.__wrapped__)
    # # with decorator_logic(1):
    # #     print("OK")
    # async def run_async():
    #     result = await myasyncfunc(3, 4)
    #     print(f"Result of myasyncfunc: {result}")
    # asyncio.run(run_async())

    print(hello(1))
    print(hello(2))  # This will stop execution because 2 is even

if __name__ == "__main__":
    main()
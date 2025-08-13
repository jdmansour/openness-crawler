
from unittest.mock import Mock
from cache_results import cache_results
import os
from typing import reveal_type
from pytest import fixture

# fixture to delete the cache file before and after each test
@fixture
def fresh_cache():
    cache_file = "testfunc_square_cache.pkl"
    # delete if it exists
    try:
        os.remove(cache_file)
    except FileNotFoundError:
        pass

    yield  # This is where the test will run

    # delete the cache file after the test
    try:
        os.remove(cache_file)
    except FileNotFoundError:
        pass

def test_cache_results(fresh_cache) -> None:
    def testfunc_square(x):
        return x * x

    mock = Mock(wraps=testfunc_square)
    wrapped = cache_results(name="testfunc_square")(mock)
    assert wrapped(2) == 4
    mock.assert_called_once()

    assert wrapped(2) == 4  # Should hit the cache
    mock.assert_called_once()  # Should not call the function again


def test_without_parentheses(fresh_cache) -> None:
    @cache_results
    def testfunc_square(x: int) -> int:
        return x * x

    # assert that the type of testfunc_square is a function from int -> int
    assert callable(testfunc_square)
    # reveal the type of testfunc_square
    assert testfunc_square.__annotations__ == {'x': int, 'return': int}


def test_with_parentheses(fresh_cache) -> None:
    @cache_results(name="testfunc_square")
    def testfunc_square(x: int) -> int:
        return x * x

    # assert that the type of testfunc_square is a function from int -> int
    assert callable(testfunc_square)
    # reveal the type of testfunc_square
    assert testfunc_square.__annotations__ == {'x': int, 'return': int}


def test_dummy_on_miss(fresh_cache) -> None:
    # pylint: disable=function-redefined

    @cache_results(name="testfunc_square")
    def testfunc_square(x: int) -> int:  # type: ignore
        return x * x

    # populate the cache with a value
    assert testfunc_square(2) == 4

    @cache_results(name="testfunc_square", dummy_on_miss=42)   # type: ignore
    def testfunc_square(x: int) -> int:
        return x * x

    assert testfunc_square(2) == 4
    # Value not in the cache should return the dummy value
    assert testfunc_square(3) == 42

    
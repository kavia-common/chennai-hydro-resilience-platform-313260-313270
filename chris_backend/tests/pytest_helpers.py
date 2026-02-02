"""
Pytest helpers for running async tests.
"""
import asyncio


def run_async(coro):
    """
    Run an async coroutine in a synchronous test.
    
    Args:
        coro: Async coroutine to run
        
    Returns:
        Result of the coroutine
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


# Register helper globally for pytest
import pytest
pytest.helpers = type('Helpers', (), {'run_async': run_async})()

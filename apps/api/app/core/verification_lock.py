from threading import BoundedSemaphore
from contextlib import contextmanager
from app.core.errors import fail
_semaphore=BoundedSemaphore(1)

@contextmanager
def verification_slot():
    if not _semaphore.acquire(timeout=40):
        fail('VERIFICATION_BUSY',429)
    try:
        yield
    finally:
        _semaphore.release()

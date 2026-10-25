from collections import OrderedDict
from copy import deepcopy
from threading import RLock
from time import monotonic
from typing import Protocol


class CacheBackend(Protocol):
    def get(self, key): ...
    def put(self, key, value): ...
    def set(self, key, value, ttl_seconds=None): ...
    def delete_prefix(self, prefix): ...
    def clear(self): ...


class MemoryCache:
    def __init__(self, ttl=30, capacity=512):
        self.ttl, self.capacity = ttl, capacity
        self.values = OrderedDict()
        self.lock = RLock()

    def get(self, key):
        with self.lock:
            item = self.values.pop(key, None)
            if not item or item[0] < monotonic():
                return None
            self.values[key] = item
            return deepcopy(item[1])

    def put(self, key, value):
        with self.lock:
            self.values[key] = (monotonic() + self.ttl, deepcopy(value))
            while len(self.values) > self.capacity:
                self.values.popitem(last=False)

    def set(self, key, value, ttl_seconds=None):
        with self.lock:
            self.values[key] = (monotonic() + (self.ttl if ttl_seconds is None else ttl_seconds), deepcopy(value))
            while len(self.values) > self.capacity:
                self.values.popitem(last=False)

    def delete_prefix(self, prefix):
        with self.lock:
            for key in list(self.values):
                if (isinstance(key, tuple) and isinstance(prefix, tuple) and key[: len(prefix)] == prefix) or str(
                    key
                ).startswith(str(prefix)):
                    del self.values[key]

    def clear(self):
        with self.lock:
            self.values.clear()


cache = MemoryCache()

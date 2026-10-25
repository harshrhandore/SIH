from collections import OrderedDict
from copy import deepcopy
from threading import RLock
from time import monotonic
from typing import Protocol


class CacheBackend(Protocol):
    def get(self, key): ...
    def put(self, key, value): ...


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


cache = MemoryCache()

import json
from django.core.cache.backends.base import BaseCache

class JSONFileCache(BaseCache):
    def __init__(self, location, params):
        super().__init__(params)
        self._location = location
        self._data = {}
        self._load()

    def _load(self):
        try:
            with open(self._location, 'r') as f:
                self._data = json.load(f)
        except FileNotFoundError:
            pass

    def _save(self):
        with open(self._location, 'w') as f:
            json.dump(self._data, f)

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value, timeout=None):
        self._data[key] = value
        self._save()

    def delete(self, key):
        if key in self._data:
            del self._data[key]
            self._save()

    def clear(self):
        self._data = {}
        self._save()

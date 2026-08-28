import unittest

import django
from django.conf import settings


if not settings.configured:
    settings.configure(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            },
        },
        SECRET_KEY="django-generic-tests",
    )

if hasattr(django, "setup"):
    django.setup()

from generic import decorators


class MemoryCache(object):
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def has_key(self, key):
        return key in self.values

    def set(self, key, value):
        self.values[key] = value


class CacheMethodTests(unittest.TestCase):
    def test_list_arguments_and_keywords_form_a_text_cache_key(self):
        memory_cache = MemoryCache()
        calls = []

        class Subject(object):
            pk = 7

            @decorators.cache_method()
            def render(self, values, labels=None):
                calls.append((values, labels))
                return "rendered"

        original_cache = decorators.cache
        decorators.cache = memory_cache
        try:
            subject = Subject()
            first = subject.render(["alpha", 2], labels=["beta", 3])
            second = subject.render(["alpha", 2], labels=["beta", 3])
        finally:
            decorators.cache = original_cache

        self.assertEqual(first, "rendered")
        self.assertEqual(second, "rendered")
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            list(memory_cache.values),
            ["generic-Subject-7-render-alpha,2-labels=beta,3"],
        )


if __name__ == "__main__":
    unittest.main()

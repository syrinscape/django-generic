import base64
import importlib
import unittest

import django
from django.conf import settings


if not settings.configured:
    settings.configure(
        HTTP_AUTH_ALWAYS=True,
        HTTP_AUTH_ENABLED=True,
        SECRET_KEY="django-generic-tests",
    )

if hasattr(django, "setup"):
    django.setup()

http_auth = importlib.import_module("generic.middleware.http_auth")


class AnonymousUser(object):
    def is_authenticated(self):
        return False


class Request(object):
    def __init__(self, authorisation):
        self.META = {"HTTP_AUTHORIZATION": authorisation}
        self.user = AnonymousUser()


class HttpAuthTests(unittest.TestCase):
    def test_basic_credentials_are_decoded_to_text(self):
        received = []

        def authenticate(request, username, password):
            received.append((username, password))
            return True

        password = b"s\xc3\xa9cret".decode("utf-8")
        token = base64.b64encode(("alice:" + password).encode("utf-8"))
        header = "Basic " + token.decode("ascii")
        request = Request(header)

        original_auth_function = getattr(settings, "HTTP_AUTH_FUNCTION", None)
        settings.HTTP_AUTH_FUNCTION = authenticate
        try:
            response = http_auth._http_auth_helper(request)
        finally:
            if original_auth_function is None:
                del settings.HTTP_AUTH_FUNCTION
            else:
                settings.HTTP_AUTH_FUNCTION = original_auth_function

        self.assertIsNone(response)
        self.assertEqual(
            [
                tuple(
                    value.decode("utf-8") if isinstance(value, bytes) else value
                    for value in credentials
                )
                for credentials in received
            ],
            [("alice", password)],
        )


if __name__ == "__main__":
    unittest.main()

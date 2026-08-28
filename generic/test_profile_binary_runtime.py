import unittest

import django
from django import http
from django.conf import settings
from django.test import override_settings


if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="django-generic-tests",
    )

if hasattr(django, "setup"):
    django.setup()

from generic.middleware.debug import ProfileMiddleware


class User(object):
    is_superuser = False


class Request(object):
    GET = {"prof": ""}
    user = User()


class ProfileBinaryResponseTests(unittest.TestCase):
    @override_settings(DEBUG=True)
    def test_profile_output_replaces_non_text_response_bytes(self):
        request = Request()
        middleware = ProfileMiddleware()

        middleware.process_request(request)
        response = middleware.process_view(
            request,
            lambda profiled_request: http.HttpResponse(
                b"\xffbinary",
                content_type="application/octet-stream",
            ),
            (),
            {},
        )
        response = middleware.process_response(request, response)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"function calls", response.content)


if __name__ == "__main__":
    unittest.main()

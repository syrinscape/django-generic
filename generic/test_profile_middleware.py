from django import http
from django.test import RequestFactory, SimpleTestCase, override_settings

from generic.middleware.debug import ProfileMiddleware


class User(object):
    is_superuser = False


class ProfileMiddlewareTests(SimpleTestCase):
    @override_settings(DEBUG=True)
    def test_profiled_view_renders_native_profiler_output(self):
        request = RequestFactory().get("/?prof")
        request.user = User()
        middleware = ProfileMiddleware()

        middleware.process_request(request)
        response = middleware.process_view(
            request,
            lambda profiled_request: http.HttpResponse("body"),
            (),
            {},
        )
        response = middleware.process_response(request, response)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"function calls", response.content)

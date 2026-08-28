import unittest

import django
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.test import RequestFactory


if not settings.configured:
    settings.configure(SECRET_KEY="django-generic-tests")

if hasattr(django, "setup"):
    django.setup()

from generic.views import mixins
from generic.views.exceptions import RedirectInstead


class PermissionDeniedView(mixins.View):
    def get(self, request):
        raise PermissionDenied("Denied text")


class RedirectInsteadView(mixins.View):
    def get(self, request):
        raise RedirectInstead("/target/")


class ViewExceptionTests(unittest.TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")

    def test_permission_denied_message_is_rendered(self):
        response = PermissionDeniedView.as_view()(self.request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content.decode("utf-8"), "Denied text")

    def test_redirect_instead_message_is_forwarded(self):
        original_redirect = getattr(mixins, "redirect", None)
        mixins.redirect = lambda location: HttpResponseRedirect(location)
        try:
            response = RedirectInsteadView.as_view()(self.request)
        finally:
            if original_redirect is None:
                del mixins.redirect
            else:
                mixins.redirect = original_redirect

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/target/")


if __name__ == "__main__":
    unittest.main()

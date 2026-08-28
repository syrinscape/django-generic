import unittest

import django
from django import http
from django.conf import settings


if not settings.configured:
    settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            },
        },
        INSTALLED_APPS=(
            "django.contrib.auth",
            "django.contrib.contenttypes",
        ),
        SECRET_KEY="django-generic-tests",
        TEMPLATE_CONTEXT_PROCESSORS=(),
    )

if hasattr(django, "setup"):
    django.setup()

from generic.utils import testing


class Message(object):
    body = (
        "First https://example.test/one?x=1 "
        "then http://example.test/two"
    )


class Response(object):
    status_code = 200
    context = {"name": "value"}


class Client(object):
    def get(self, url):
        return Response()


class TestingHelpersTests(unittest.TestCase):
    def make_helper(self):
        class Helper(testing.TestCase):
            def runTest(self):
                pass

        return Helper()

    def test_redirect_comparison_can_ignore_only_the_query_string(self):
        helper = self.make_helper()
        response = http.HttpResponseRedirect("/target/?page=2")

        original_assert_redirects = django.test.TestCase.assertRedirects

        def fail_with_redirect_details(*args, **kwargs):
            raise AssertionError(
                "Response redirected to '/target/?page=2', "
                "expected '/target/'"
            )

        django.test.TestCase.assertRedirects = fail_with_redirect_details
        try:
            helper.assertRedirects(
                response,
                "/target/",
                ignore_querystring=True,
                fetch_redirect_response=False,
            )
        finally:
            django.test.TestCase.assertRedirects = original_assert_redirects

    def test_url_context_expectations_are_evaluated_eagerly(self):
        helper = self.make_helper()
        helper.client = Client()

        helper._test_urls(
            [
                (
                    "/ok/",
                    {"context": {"name": "value"}},
                ),
            ]
        )

    def test_email_urls_preserve_accepted_sequence_results(self):
        helper = self.make_helper()

        self.assertEqual(
            helper.extract_urls_from_email(Message()),
            ("/one?x=1", "/two"),
        )
        self.assertEqual(
            helper.extract_urls_from_email(Message(), path_only=False),
            [
                "https://example.test/one?x=1",
                "http://example.test/two",
            ],
        )

    def test_selenium_field_mappings_are_consumed_eagerly(self):
        class Recorder(testing.SeleniumTests):
            def __init__(self):
                self.fields = []

            def fill_field(self, name, value):
                self.fields.append((name, value))

        recorder = Recorder()

        recorder.fill_fields({"first": "one", "second": "two"})

        self.assertEqual(
            sorted(recorder.fields),
            [("first", "one"), ("second", "two")],
        )


if __name__ == "__main__":
    unittest.main()

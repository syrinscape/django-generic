from unittest import mock

import django.test
from django import http
from django.template import Template, TemplateSyntaxError
from django.test import SimpleTestCase


class Python3GrammarTests(SimpleTestCase):
    def test_template_tags_preserve_syntax_error_messages(self):
        cases = [
            (
                "{% load generic_tags %}{% split_list values %}",
                "split_list list as new_list 2",
            ),
            (
                "{% load generic_tags %}"
                "{% split_list values into columns 2 %}",
                "second argument to the split_list tag must be 'as'",
            ),
            (
                "{% load generic_tags %}{% update_GET attr = %}",
                "'update_GET' tag requires arguments in groups of three "
                "(op, attr, value).",
            ),
            (
                "{% load generic_tags %}"
                "{% update_GET attr *= value %}",
                "The only allowed operators are '+=', '-=' and '='. "
                "You have used *=",
            ),
        ]

        from generic.templatetags import generic_tags

        generic_tags.xrange = range
        try:
            for source, message in cases:
                with self.assertRaisesMessage(TemplateSyntaxError, message):
                    Template(source)
        finally:
            del generic_tags.xrange

    def test_decorators_module_imports(self):
        from generic import decorators

        self.assertTrue(callable(decorators.cache_method))

    def test_testing_helper_can_ignore_redirect_query_strings(self):
        from generic.utils import testing

        testing.unicode = str

        class RedirectTestCase(testing.TestCase):
            def runTest(self):
                pass

        helper = RedirectTestCase()
        response = http.HttpResponseRedirect("/target/?page=2")

        try:
            with mock.patch.object(
                django.test.TestCase,
                "assertRedirects",
                side_effect=AssertionError(
                    "Response redirected to '/target/?page=2', "
                    "expected '/target/'"
                ),
            ):
                helper.assertRedirects(
                    response,
                    "/target/",
                    ignore_querystring=True,
                    fetch_redirect_response=False,
                )
        finally:
            del testing.unicode

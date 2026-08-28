from django.template import Context, Template
from django.test import RequestFactory, SimpleTestCase


class UpdateGetValueTests(SimpleTestCase):
    def render_update_get(self, operation, value, initial_values=()):
        query = "&".join(
            "tag={0}".format(initial_value)
            for initial_value in initial_values
        )
        request = RequestFactory().get("/?{0}".format(query))
        template = Template(
            "{% load generic_tags %}"
            "{% update_GET attribute " + operation + " value %}"
        )
        return template.render(Context({
            "attribute": "tag",
            "request": request,
            "value": value,
        }))

    def test_text_is_one_query_value(self):
        self.assertEqual(
            self.render_update_get("=", "abc", ("old",)),
            "tag=abc",
        )

    def test_bytes_are_one_query_value(self):
        self.assertEqual(
            self.render_update_get("=", b"abc", ("old",)),
            "tag=abc",
        )

    def test_iterables_remain_multiple_query_values(self):
        self.assertEqual(
            self.render_update_get("+=", ["one", "two"], ("zero",)),
            "tag=zero&amp;tag=one&amp;tag=two",
        )

from django.template import Context, Template
from django.test import RequestFactory, SimpleTestCase


class UpdateGetMembershipTests(SimpleTestCase):
    def test_none_removes_an_existing_query_value(self):
        request = RequestFactory().get("/?tag=old")
        template = Template(
            "{% load generic_tags %}"
            "{% update_GET attribute = value %}"
        )

        rendered = template.render(Context({
            "attribute": "tag",
            "request": request,
            "value": None,
        }))

        self.assertEqual(rendered, "")

from django.template import Context, Template
from django.test import SimpleTestCase


class TemplateRangeTests(SimpleTestCase):
    def test_update_get_tag_compiles_argument_groups(self):
        template = Template(
            "{% load generic_tags %}"
            "{% update_GET attribute = value %}"
        )

        self.assertEqual(
            template.render(
                Context({
                    "attribute": None,
                    "value": "unused",
                })
            ),
            "",
        )

    def test_split_list_tag_partitions_values(self):
        template = Template(
            "{% load generic_tags %}"
            "{% split_list values as columns 2 %}"
            "{% for column in columns %}{{ column|join:',' }};{% endfor %}"
        )

        self.assertEqual(
            template.render(Context({"values": [1, 2, 3, 4, 5]})),
            "1,2,3;4,5;",
        )

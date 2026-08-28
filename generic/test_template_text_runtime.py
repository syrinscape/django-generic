import unittest

import django
from django.conf import settings


if not settings.configured:
    settings.configure(
        INSTALLED_APPS=(
            "django.contrib.contenttypes",
            "django.contrib.sites",
        ),
        SECRET_KEY="django-generic-tests",
    )

if hasattr(django, "setup"):
    django.setup()

from generic.templatetags import generic_tags


class TemplateTextTests(unittest.TestCase):
    def test_html_entities_are_unescaped_as_text(self):
        copyright_sign = b"\xc2\xa9".decode("utf-8")
        non_breaking_hyphen = b"\xe2\x80\x91".decode("utf-8")

        self.assertEqual(
            generic_tags.htmlparser_unescape(
                "Tom &amp; Jerry &#169; &#x2011; &unknown;"
            ),
            "Tom & Jerry "
            + copyright_sign
            + " "
            + non_breaking_hyphen
            + " &unknown;",
        )

    def test_admin_link_formats_model_and_instance_text(self):
        class ModelMeta(object):
            app_label = "catalogue"
            model_name = "item"
            verbose_name = "item"

        class Model(object):
            _meta = ModelMeta()

        class Item(object):
            def __str__(self):
                return "Item 7"

            def __unicode__(self):
                return "Item 7"

        original_reverse = generic_tags.reverse
        generic_tags.reverse = lambda *args, **kwargs: "/admin/items/7/"
        try:
            result = generic_tags._admin_link(
                "change_link",
                "change",
                {},
                assume_permission=True,
                instance=Item(),
                link_text="Edit <verbose_name>: <instance_unicode>",
                model=Model,
            )
        finally:
            generic_tags.reverse = original_reverse

        self.assertEqual(
            result,
            '<a href="/admin/items/7/" class="admin-link">'
            "Edit item: Item 7</a>",
        )


if __name__ == "__main__":
    unittest.main()

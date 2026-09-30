from unittest import mock

from django.test import SimpleTestCase
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from generic.admin.widgets import (
    ForeignKeyCookedIdWidget,
    StackedInlineForeignKeyCookedIdWidget,
    TabularInlineForeignKeyCookedIdWidget,
)


class InlineCookedIdWidgetTests(SimpleTestCase):
    def test_inline_widget_output_remains_safe_after_class_replacement(self):
        widgets = (
            (
                TabularInlineForeignKeyCookedIdWidget,
                "TabularInlineCookedIdField",
            ),
            (
                StackedInlineForeignKeyCookedIdWidget,
                "StackedInlineCookedIdField",
            ),
        )

        for widget_class, expected_class in widgets:
            with self.subTest(widget_class=widget_class.__name__):
                widget = widget_class.__new__(widget_class)
                with mock.patch.object(
                    ForeignKeyCookedIdWidget,
                    "render",
                    return_value=mark_safe('<input class="CookedIdField">'),
                ):
                    output = widget.render("target", None)

                self.assertIn(expected_class, output)
                self.assertEqual(conditional_escape(output), output)

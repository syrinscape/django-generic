from django.contrib.admin.widgets import (
     ManyToManyRawIdWidget, ForeignKeyRawIdWidget)
from django.utils.safestring import mark_safe

class ForeignKeyCookedIdWidget(ForeignKeyRawIdWidget):
    """
    For situations where RawIdWidgets are a bit too... well, raw.
    """
    def label_for_value(self, value):
        return '' # avoid displaying normal <strong>value</strong>

    def render(self, name, value, attrs=None):
        output = super(ForeignKeyCookedIdWidget, self).render(
            name, value, attrs)
        output = output.replace(
            'RawIdAdminField', 'RawIdAdminField CookedIdField')
        return mark_safe('<ul class="cooked-data"></ul>' + output)

    class Media:
        js = ('generic/js/cooked_id_widgets.js', 'generic/js/jquery.contextMenu.js')
        css = {'all': ('generic/css/cooked_ids.css', 'generic/css/jquery.contextMenu.css')}


class ManyToManyCookedIdWidget(ForeignKeyCookedIdWidget,
                               ManyToManyRawIdWidget):
    pass


class TabularInlineForeignKeyCookedIdWidget(ForeignKeyCookedIdWidget):

    def render(self, name, value, attrs=None):
        output = super(TabularInlineForeignKeyCookedIdWidget, self).render(
            name, value, attrs)
        output = output.replace(
            'CookedIdField', 'TabularInlineCookedIdField')

        return mark_safe(output)


class TabularInlineManyToManyCookedIdWidget(TabularInlineForeignKeyCookedIdWidget,
                                            ManyToManyRawIdWidget):
    pass


class StackedInlineForeignKeyCookedIdWidget(ForeignKeyCookedIdWidget):

    def render(self, name, value, attrs=None):
        output = super(StackedInlineForeignKeyCookedIdWidget, self).render(
            name, value, attrs)
        output = output.replace(
            'CookedIdField', 'StackedInlineCookedIdField')

        return mark_safe(output)


class StackedInlineManyToManyCookedIdWidget(StackedInlineForeignKeyCookedIdWidget,
                                            ManyToManyRawIdWidget):
    pass

from django import forms
from django import http
from django.contrib import admin
from django.contrib.admin.filters import SimpleListFilter
try:
    from django.apps import apps
    get_model = apps.get_model
    get_models = apps.get_models
except ImportError:
    from django.db.models.loading import get_model, get_models
from django.utils.translation import ugettext_lazy as _

try:
    # Prevent deprecation warnings on Django >= 1.4
    from django.conf.urls import patterns, url
except ImportError:
    # For compatibility with Django <= 1.3
    from django.conf.urls.defaults import patterns, url

from ...utils.inheritance import get_subclasses


def get_subclass_choices(parent_model):
    title_if_lower = lambda s: (s.title() if s == s.lower() else s)
    return sorted(
        map(
            lambda model: (
                model._meta.model_name,
                title_if_lower(model._meta.verbose_name),
            ),
            filter(
                lambda model: (
                    issubclass(model, parent_model) and
                    parent_model in model._meta.parents
                ),
                get_models()
            )
        )
    )

class SubclassFilter(SimpleListFilter):
    title = _('Type')
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        return get_subclass_choices(model_admin.model)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.complex_filter(
                {'%s__isnull' % self.value(): False})
        else:
            return queryset


class PolymorphicAdmin(admin.ModelAdmin):
    """
    For use with django-model-utils' InheritanceManager.
    """

    list_filter = (SubclassFilter,)
    subclass_parameter_name = '__subclass'
    subclass_label = _('Type')

    def add_view(self, request, form_url='', extra_context=None):
        if self.subclass_parameter_name in request.POST:
            import urllib
            return http.HttpResponseRedirect(
                '?%s=%s' % (
                    self.subclass_parameter_name,
                    request.POST.get(self.subclass_parameter_name),
                )
                + '&' + urllib.urlencode(request.GET.items())
            )
        return super(PolymorphicAdmin, self).add_view(
            request, form_url=form_url, extra_context=extra_context)

    def get_fieldsets(self, request, obj=None):
        if not self.get_model(request, obj):
            # show subclass selection field only
            return (
                (None, {'fields': (self.subclass_parameter_name,)},),
            )
        return self.get_modeladmin(request, obj).get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        model_admin = self.get_modeladmin(request, obj)
        return model_admin.get_readonly_fields(request, obj)

    def get_inline_instances(self, request, obj=None):
        model_admin = self.get_modeladmin(request, obj)
        return model_admin.get_inline_instances(request, obj)

    def get_formsets(self, request, obj=None):
        if not self.get_model(request, obj):
            return () # hide inlines on add form until subclass selected
        model_admin = self.get_modeladmin(request, obj)
        return model_admin.get_formsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        model_admin = self.get_modeladmin(request, obj)
        if not self.get_model(request, obj):
            # Not passing fields=None as kwargs here breaks Django 1.6
            form_class = model_admin.get_form(request, obj=obj, fields=None, **kwargs)
            return self._build_subclass_selection_form(form_class)
        else:
            form_class = model_admin.get_form(request, obj=obj, **kwargs)
            return form_class

    def get_model(self, request, obj=None):
        if obj:
            return obj.__class__
        model_name = (
            request.POST.get(self.subclass_parameter_name) or
            request.GET.get(self.subclass_parameter_name, '')
        )
        return get_model(self.opts.app_label, model_name) if model_name else None

    def get_modeladmin(self, request, obj=None):
        model = self.get_model(request, obj)
        if model and model != self.model:
            return self.admin_site._registry.get(
                model, # use registered admin if it exists...
                self.get_unregistered_admin_classes().get(
                    model, # or unregistered one if we know about it
                    self.__class__ # ...or build a generic one
                )(model, self.admin_site)
            )
        else:
            return super(PolymorphicAdmin, self)

    def get_unregistered_admin_classes(self):
        return {
            # override with Model: ModelAdmin mapping
        }

    def _build_subclass_selection_form(self, form_class):
        class SubclassSelectionForm(form_class):
            def __init__(form, *args, **kwargs):
                super(SubclassSelectionForm, form).__init__(*args, **kwargs)
                form.fields[self.subclass_parameter_name] = forms.ChoiceField(
                    choices=get_subclass_choices(self.model),
                    label=self.subclass_label,
                )
        return SubclassSelectionForm

    # TODO: disable bulk deletion action when heterogeneous classes selected
    # -- collector doesn't cope, and raises AttributeErrors

    def get_queryset(self, request):
        return self.model.objects.select_subclasses()

    def get_urls(self, *args, **kwargs):
        """
        To make sure that save and continue editing works when adding new
        Polymorphic models, add a url pattern that matches the subclass model
        name. A reverse lookup on this name will still return the change view
        for the parent model, since its URL will be matched first.
        """
        urls = super(PolymorphicAdmin, self).get_urls(*args, **kwargs)
        for subclass in get_subclasses(self.model):
            info = subclass._meta.app_label, subclass._meta.model_name
            urls += patterns('',
                url(r'^(.+)/$',
                    lambda *a, **k: None, # This never gets called
                    name='%s_%s_change' % info),
            )
        return urls

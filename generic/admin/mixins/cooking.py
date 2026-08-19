import django

from django import http
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import Media, MEDIA_TYPES
from django.core.urlresolvers import reverse
from ..widgets import (
    ForeignKeyCookedIdWidget,
    ManyToManyCookedIdWidget,
    TabularInlineForeignKeyCookedIdWidget,
    TabularInlineManyToManyCookedIdWidget,
    StackedInlineForeignKeyCookedIdWidget,
    StackedInlineManyToManyCookedIdWidget,
)

try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url

try:
    import json
except ImportError:
    from django.utils import simplejson as json

class BaseCookedIdAdmin:
    """
    Support for CookedIdWidgets (vs. RawIdWidgets) in admin.

    See:
    - `generic.admin.widgets.ManyToManyCookedIdWidget`, and
    - `generic.admin.widgets.ForeignKeyCookedIdWidget`

    Simply list fields in self.cooked_id_widgets instead of self.raw_id_widgets

    Override self.cook() to customise cooked object representations.
    """
    cooked_id_fields = ()

    def cook(self, obj, request, field_name):
        """
        Override this to customise the "cooked" representation of objects
        """
        view_url = ''
        edit_url = ''

        if hasattr(obj, 'get_absolute_url'):
            view_url = obj.get_absolute_url();

        if request.user.has_perm('%s.change_%s' % (obj._meta.app_label, obj._meta.model_name)):
            edit_url = reverse('admin:%s_%s_change' % (obj._meta.app_label,  obj._meta.model_name),  args=[obj.id])

        result = {'text': unicode(obj),
                  'view_url': view_url,
                  'edit_url': edit_url
                  }
        return result

    def cook_ids(self, request, pk, field_name, raw_ids):
        # TODO: extend to support non-integer/non-`id` PKs
        if not field_name in self.cooked_id_fields:
            raise http.Http404
        try:
            ids = map(int, raw_ids.split(','))
        except ValueError:
            if raw_ids == '':
                ids = []
            else:
                raise http.Http404
        target_model_admin = self.admin_site._registry.get(
            self.model._meta.get_field(field_name).rel.to)
        response_data = {}
        if (
                target_model_admin and
                target_model_admin.has_change_permission(request)
        ):
            for obj in target_model_admin.get_queryset(request).filter(id__in=ids):
                response_data[obj.pk] = self.cook(
                    obj, request=request, field_name=field_name)
        else:
            pass # graceful-ish.

        content_type_kwarg = (
            'content_type' if django.VERSION >= (1,7) else 'mimetype'
        )
        return http.HttpResponse(
            json.dumps(response_data),
            **{content_type_kwarg: 'application/json'}
        )

    def assert_cooked_target_admin(self, db_field):
        if db_field.rel.to in self.admin_site._registry:
            return True
        else:
            if settings.DEBUG:
                raise ImproperlyConfigured(
                    "%s.cooked_id_fields contains '%r', but %r "
                    "is not registed in the same admin site." % (
                        self.__class__.__name__,
                        db_field.name,
                        db_field.rel.to,
                    )
                )
            else:
                pass # fail silently


class CookedIdAdmin(BaseCookedIdAdmin, admin.ModelAdmin):

    def cook_ids_inline(self, request, pk, model_name, field_name, raw_ids):

        # find the correct inline instance and pass control to it's own cook_ids()
        inlines = self.get_inline_instances(request)
        for inline in inlines:
            content_type = ContentType.objects.get_for_model(inline.model)
            if model_name == content_type.model and field_name in inline.cooked_id_fields:
                # this is our guy
                return inline.cook_ids(request, pk, field_name, raw_ids)

        raise http.Http404

    def get_urls(self):

        urlpatterns = patterns(
            '',
            url(r'^(?P<pk>.+)/cook-ids/(?P<field_name>\w+)/(?P<raw_ids>[\d,]+)/$',
                self.admin_site.admin_view(self.cook_ids))
        )

        # add any inline cooked ID urls...

        for inline in self.inlines:
            try:
                if inline.cooked_id_fields:
                    content_type = ContentType.objects.get_for_model(inline.model)
                    urlpatterns += patterns(
                        '',
                        url(r'^(?P<pk>.+)/cook-ids-inline/(?P<model_name>'+content_type.model+')/(?P<field_name>\w+)/(?P<raw_ids>[\d,]+)/$',
                            self.admin_site.admin_view(self.cook_ids_inline))
                    )
            except AttributeError:
                # probably not a TabularInlineCookedIdAdmin
                pass

        return urlpatterns + super(CookedIdAdmin, self).get_urls()

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name in self.cooked_id_fields:
            if self.assert_cooked_target_admin(db_field):
                kwargs['widget'] = ManyToManyCookedIdWidget(
                    db_field.rel, self.admin_site)
        return super(CookedIdAdmin, self).formfield_for_manytomany(
            db_field, request=request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name in self.cooked_id_fields:
            if self.assert_cooked_target_admin(db_field):
                kwargs['widget'] = ForeignKeyCookedIdWidget(
                    db_field.rel, self.admin_site)
        return super(CookedIdAdmin, self).formfield_for_foreignkey(
            db_field, request=request, **kwargs)


class TabularInlineCookedIdAdmin(BaseCookedIdAdmin, admin.TabularInline):

    content_type = None

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        content_type = ContentType.objects.get_for_model(self.model)
        if db_field.name in self.cooked_id_fields:
            if self.assert_cooked_target_admin(db_field):
                kwargs['widget'] = TabularInlineManyToManyCookedIdWidget(
                    db_field.rel, self.admin_site, {
                        'data-model': content_type.model,
                        'data-field': db_field.name,
                    })
        return super(TabularInlineCookedIdAdmin, self).formfield_for_manytomany(
            db_field, request=request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        content_type = ContentType.objects.get_for_model(self.model)
        if db_field.name in self.cooked_id_fields:
            if self.assert_cooked_target_admin(db_field):
                kwargs['widget'] = TabularInlineForeignKeyCookedIdWidget(
                    db_field.rel, self.admin_site, {
                        'data-model': content_type.model,
                        'data-field': db_field.name,
                    })
        return super(TabularInlineCookedIdAdmin, self).formfield_for_foreignkey(
            db_field, request=request, **kwargs)


class StackedInlineCookedIdAdmin(BaseCookedIdAdmin, admin.StackedInline):

    content_type = None

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        content_type = ContentType.objects.get_for_model(self.model)
        if db_field.name in self.cooked_id_fields:
            if self.assert_cooked_target_admin(db_field):
                kwargs['widget'] = StackedInlineManyToManyCookedIdWidget(
                    db_field.rel, self.admin_site, {
                        'data-model': content_type.model,
                        'data-field': db_field.name,
                    })
        return super(StackedInlineCookedIdAdmin, self).formfield_for_manytomany(
            db_field, request=request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        content_type = ContentType.objects.get_for_model(self.model)
        if db_field.name in self.cooked_id_fields:
            if self.assert_cooked_target_admin(db_field):
                kwargs['widget'] = StackedInlineForeignKeyCookedIdWidget(
                    db_field.rel, self.admin_site, {
                        'data-model': content_type.model,
                        'data-field': db_field.name,
                    })
        return super(StackedInlineCookedIdAdmin, self).formfield_for_foreignkey(
            db_field, request=request, **kwargs)


class MediaWithInlineJS(Media):
    """
    Used internally by CookedSingletonFix, a helper class that adds inline JS
    functionality to django's internal Media objects, which otherwise only
    support lists of URLs for JS and CSS files.
    
    Note that the inline JS functionality will be lost if a MediaWithInlineJS
    object is on the right-hand side of an addition with a normal Media object.
    """
    def __init__(self, *args, **kwargs):
        self.inline_js = kwargs.pop('inline_js', '')
        super(MediaWithInlineJS, self).__init__(*args, **kwargs)
    
    def render_js(self):
        return super(MediaWithInlineJS, self).render_js() + [self.inline_js]
    
    def __add__(self, other):
        combined = MediaWithInlineJS(inline_js=self.inline_js)
        for name in MEDIA_TYPES:
            getattr(combined, 'add_' + name)(getattr(self, '_' + name, None))
            getattr(combined, 'add_' + name)(getattr(other, '_' + name, None))
        return combined

class CookedSingletonFix(object):
    """
    A ModelAdmin mixin for singleton objects (provided by the django-singleton
    library) that use cooked IDs. Place before SingletonAdmin and CookiedIdAdmin
    in the inheritance list.
    
    Cooked IDs will not work on singleton models without this fix due to the
    way the JS constructs the URL for the "cook" requests. Singleton models
    don't have a PK in their admin URLs, which is the root of the issue.
    
    This fix adds inline JS via the ModelAdmin.Media mechanic to set the 
    "window.cooked_id_url_base" JS variable, so that working URLs can be
    constructed. The fix is generic enough to work with non-singleton models
    as well, but is provided as an explicit mix-in due to its reliance on
    the addition order of Media objects in the ModelAdmin internals, which is
    subject to sudden and confusing breakage.
    """
    
    @property
    def media(self):
        # Because singleton models don't have a PK section in their URL,
        # using './' doesn't work, but instead of faking a PK, the add
        # URL should be a cleaner approach
        base_url = reverse('admin:%s_%s_add' % (
            self.model._meta.app_label, self.model._meta.model_name)
        )
        extra_script = '<script type="text/javascript">'\
            'window.cooked_id_url_base="%s";</script>' % base_url
        return MediaWithInlineJS(inline_js=extra_script) \
            + super(CookedSingletonFix, self).media

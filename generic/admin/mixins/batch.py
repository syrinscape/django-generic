from django import forms
from django import http
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.contrib.admin import helpers
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.template.response import TemplateResponse
from django.utils.translation import ungettext_lazy, ugettext_lazy as _
from copy import copy

M2M_REMOVE_PREFIX = 'm2m_remove_'
M2M_ADD_PREFIX = 'm2m_add_'


class BatchUpdateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        from django.forms.forms import BoundField
        super(BatchUpdateForm, self).__init__(*args, **kwargs)
        for field_name in self.fields.keys():

            model_field = self._meta.model._meta.get_field(field_name)
            if isinstance(model_field, models.ManyToManyField):

                self.fields['%s%s'%(M2M_REMOVE_PREFIX, field_name,)] = copy(self.fields[field_name])
                self.fields['%s%s'%(M2M_REMOVE_PREFIX, field_name,)].label = _("Remove %s"%(field_name,))
                self.fields['%s%s'%(M2M_REMOVE_PREFIX, field_name,)].update_checkbox = BoundField(
                    self,
                    forms.BooleanField(required=False),
                    'updating-%s%s'%(M2M_REMOVE_PREFIX, field_name,)
                )

                self.fields['%s%s'%(M2M_ADD_PREFIX, field_name,)] = copy(self.fields[field_name])
                self.fields['%s%s'%(M2M_ADD_PREFIX, field_name,)].label = _("Add %s"%(field_name,))
                self.fields['%s%s'%(M2M_ADD_PREFIX, field_name,)].update_checkbox = BoundField(
                    self,
                    forms.BooleanField(required=False),
                    'updating-%s%s'%(M2M_ADD_PREFIX, field_name,)
                )

                self.fields.pop(field_name)
            else:
                self.fields[field_name].update_checkbox = BoundField(
                    self,
                    forms.BooleanField(required=False),
                    'updating-'+field_name
                )

    def clean(self):
        cleaned_data = super(BatchUpdateForm, self).clean()
        self.fields_to_update = []
        for field_name, field in self.fields.iteritems():
            if field.update_checkbox.value():
                self.fields_to_update.append(field_name)
        if not self.fields_to_update:
            raise ValidationError(
                [_("You haven't selected any fields to update")])
        return cleaned_data

    def apply(self, request, queryset):
        update_params = {}
        updated = 0
        for field_name in self.fields_to_update:

            if field_name.startswith(M2M_REMOVE_PREFIX):
                model_field_name = field_name[len(M2M_REMOVE_PREFIX):]
            elif field_name.startswith(M2M_ADD_PREFIX):
                model_field_name = field_name[len(M2M_ADD_PREFIX):]
            else:
                model_field_name = field_name

            field = queryset.model._meta.get_field(model_field_name)
            if isinstance(field, models.ManyToManyField):

                if field_name.startswith(M2M_REMOVE_PREFIX):
                    for obj in queryset.all():
                        for related_obj in self.cleaned_data[field_name]:
                            getattr(obj, model_field_name).remove(related_obj)
                        updated += 1

                if field_name.startswith(M2M_ADD_PREFIX):
                    for obj in queryset.all():
                        for related_obj in self.cleaned_data[field_name]:
                            getattr(obj, model_field_name).add(related_obj)
                        updated += 1

            else:
                update_params[field_name] = self.cleaned_data[field_name]

        self._restore_fields_to_update()

        if update_params:
            updated = queryset.update(**update_params)
        return updated

    def _restore_fields_to_update(self):
        new_list = []
        for field_name in self.fields_to_update:
            model_field_name = field_name
            if field_name.startswith(M2M_REMOVE_PREFIX):
                model_field_name = field_name[len(M2M_REMOVE_PREFIX):]
            elif field_name.startswith(M2M_ADD_PREFIX):
                model_field_name = field_name[len(M2M_ADD_PREFIX):]
            if not model_field_name in new_list:
                new_list.append(model_field_name)
        self.fields_to_update = new_list


class BatchUpdateAdmin(admin.ModelAdmin):
    batch_update_fields = ()

    def _get_url_name(self, view_name, include_namespace=True):
        return '%s%s_%s_%s' % (
            'admin:' if include_namespace else '',
            self.model._meta.app_label,
            self.model._meta.model_name,
            view_name,
        )

    def batch_update(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        return http.HttpResponseRedirect(
            '%s?ids=%s' % (
                reverse(
                    self._get_url_name('batchupdate'),
                    current_app=self.admin_site.name,
                ),
                ','.join(selected),
            )
        )

    def get_batch_update_form_class(self, request):
        return self.get_form(
            request,
            obj=None,
            form=BatchUpdateForm,
            fields=self.batch_update_fields,
        )

    def batch_update_view(self, request):
        template_paths = map(
            lambda path: path % {
                'app_label': self.model._meta.app_label,
                'model_name': self.model._meta.model_name,
            }, (
                'admin/%(app_label)s/%(model_name)s/batch_update.html',
                'admin/%(app_label)s/batch_update.html',
                'admin/batch_update.html',
                'admin/generic/batch_update.html',
            )
        )
        ids = (request.POST.get('ids') or request.GET.get('ids') or '').split(',')
        queryset = self.get_queryset(request).filter(pk__in=ids)
        form_class = self.get_batch_update_form_class(request)
        form = form_class(request.POST or None)
        if form.is_valid():
            updated = form.apply(request, queryset)

            self.message_user(
                request,
                ungettext_lazy(
                    u'Updated fields (%(field_list)s) '
                    u'for %(count)d %(verbose_name)s',
                    u'Updated fields (%(field_list)s) '
                    u'for %(count)d %(verbose_name_plural)s',
                    updated,
                ) % {
                    'field_list': u', '.join(
                        [
                            unicode(self.model._meta.get_field(name).verbose_name)
                            for name in form.fields_to_update
                        ]
                    ),
                    'count': updated,
                    'verbose_name': self.model._meta.verbose_name,
                    'verbose_name_plural': self.model._meta.verbose_name_plural
                }
            )
            return self.response_post_save_change(request, None)

        return TemplateResponse(
            request,
            template_paths, {
                'form': form,
                'model_meta': self.model._meta,
                'has_change_permission': self.has_change_permission(request),
                'count': len(queryset),
                'media': self.media + helpers.AdminForm(
                    form,
                    (), #list(self.get_fieldsets(request)),
                    {}, #self.get_prepopulated_fields(request),
                    (), #self.get_readonly_fields(request),
                    model_admin=self
                ).media,
            },
            current_app=self.admin_site.name,
        )

    def get_urls(self):
        return patterns(
            '',
            url(r'^batch-update/$',
                self.admin_site.admin_view(self.batch_update_view),
                name=self._get_url_name(
                    'batchupdate', include_namespace=False),
            ),
        ) + super(BatchUpdateAdmin, self).get_urls()

    def get_actions(self, request):
        actions = super(BatchUpdateAdmin, self).get_actions(request)
        if self.batch_update_fields:
            self._validate_batch_update_fields()
            if not 'batch_update' in actions:
                actions['batch_update'] = self.get_action('batch_update')
        else:
            if 'batch_update' in actions:
                del actions['batch_update']
        return actions

    def _validate_batch_update_fields(self):
        for field in self.batch_update_fields:
            field = self.model._meta.get_field(field)

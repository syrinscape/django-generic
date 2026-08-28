import json
import django.views.generic

from django import http
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
try:
    from django.shortcuts import resolve_url
except ImportError:
    from generic.utils.future import resolve_url
from django.utils.http import urlquote
from django.utils.decorators import method_decorator

from .exceptions import RedirectInstead
from ..utils.tokens import get_token

class Authenticated(django.views.generic.View):
    """ Base for views which require an authenticated user """
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(Authenticated, self).dispatch(*args, **kwargs)


class View(django.views.generic.View):
    result_text = 'OK'
    ajax_catch_redirects = False
    default_context_data = {}

    def __init__(self, *args, **kwargs):
        super(View, self).__init__(*args, **kwargs)
        self.context_data = dict(self.default_context_data)

    def finalize_response(self, response):
        """ Hook for any last-minute response tweaking; e.g. JSON for AJAX """
        if self.request.is_ajax() and response.status_code == 302:
            if self.ajax_catch_redirects:
                return http.HttpResponse(
                    json.dumps(
                        {
                            'redirect': response['location'],
                            'result': self.result_text,
                        }
                    ),
                    content_type="application/json"
                )
        return response

    def dispatch(self, request, *args, **kwargs):
        """ Allow translation of custom exceptions into HTTP responses. """
        try:
            response = super(View, self).dispatch(request, *args, **kwargs)
        except PermissionDenied as forbidden_exception:
            response = http.HttpResponseForbidden(
                str(forbidden_exception) or 'Permission denied')
        except RedirectInstead as redirect_exception:
            response = redirect(str(redirect_exception))
        return self.finalize_response(response)

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['use_multipart_form'] = self.requires_multipart_form()
        context.update(self.context_data)
        return context

    def requires_multipart_form(self):
        return hasattr(self, 'form') and self.form.is_multipart()


# WIP...
# class MultiFormMixin(ContextMixin):
#     """
#     A mixin that provides a way to show and handle multiple forms in a request.
#     """

#     initial = {}
#     form_classes = {}
#     formset_classes = {}
#     success_url = None

#     def get_initial(self, form_key):
#         """
#         Returns the initial data to use for forms on this view.
#         """
#         return self.initial.get(form_key, {}).copy()

#     def get_form_classes(self):
#         """
#         Returns the form classes to use in this view
#         """
#         return self.form_classes

#     def get_forms(self, form_classes):
#         """
#         Returns instances of the forms to be used in this view.
#         """
#         return [
#             form_class(**self.get_form_kwargs(key)) for
#             key, form_class in self.get_form_classes().iteritems()
#         ]

#     def get_form_kwargs(self, form_key):
#         """
#         Returns the keyword arguments for instantiating the form.
#         """
#         kwargs = {'initial': self.get_initial(form_key)}
#         if self.request.method in ('POST', 'PUT'):
#             kwargs.update({
#                 'data': self.request.POST,
#                 'files': self.request.FILES,
#             })
#         return kwargs

#     def get_formset_kwargs(self, formset_class):
#         return {
#             'data': self.request.POST or None,
#             'files': self.request.FILES or None,
#             'instance': getattr(self, 'object', None),
#         }

#     def get_formset(self, formset_class):
#         return formset_class(**self.get_formset_kwargs(formset_class))

#     def get_formsets(self, formset_class=None):
#         form_class
#         formsets = {}
#         for key, formset_class in self.formset_classes.iteritems():
#             formsets[key] = self.get_formset(formset_class)
#         return formsets

#     def save_formsets(self):
#         for formset in self.formsets.values():
#             formset.save()

#     def form_valid(self, form):
#         form = self.get_form(self.get_form_class())
#         for formset in self.formsets.values():
#             formset.instance = form.save(commit=False)
#             if not formset.is_valid():
#                 return self.form_invalid(form)
#         # OK, all valid
#         response = super(InlineFormSetView, self).form_valid(form)
#         self.save_formsets()
#         return response

#     def get_success_url(self):
#         """
#         Returns the supplied success URL.
#         """
#         if self.success_url:
#             # Forcing possible reverse_lazy evaluation
#             url = force_text(self.success_url)
#         else:
#             raise ImproperlyConfigured(
#                 "No URL to redirect to. Provide a success_url.")
#         return url

#     def all_valid(self, forms):
#         for form in forms:
#             if not form.is_valid():
#                 return False
#         return True

#     def forms_valid(self, forms):
#         """
#         Forms are valid, redirect to the supplied URL.
#         """

#         return http.HttpResponseRedirect(self.get_success_url())

#     def forms_invalid(self, form):
#         """
#         If any form is invalid, re-render the context data with the
#         data-filled forms and errors.
#         """
#         return self.render_to_response(self.get_context_data(forms=forms))


# class MultiFormView(View):
#     """
#     A mixin that renders forms on GET and processes them on POST.
#     """
#     def get(self, request, *args, **kwargs):
#         """
#         Handles GET requests and instantiates a blank version of the form.
#         """
#         form_classes = self.get_form_classes()
#         forms = self.get_forms(form_classes)
#         formset_classes = self.get_formset_classes()
#         formsets = self.get_formsets(formset_classes)
#         return self.render_to_response(
#             self.get_context_data(
#                 forms=forms,
#                 formsets=formsets,
#             )
#         )

#     def post(self, request, *args, **kwargs):
#         """
#         Handles POST requests, instantiating form instances with the passed
#         POST variables and then checking for validity.
#         """
#         form_classes = self.get_form_classes()
#         forms = self.get_forms(form_classes)
#         formset_classes = self.get_formset_classes()
#         formsets = self.get_formsets(formset_classes)
#         if self.all_valid(forms, formsets):
#             return self.forms_valid(forms, formsets)
#         else:
#             return self.forms_invalid(form, formsets)

#     # PUT is a valid HTTP verb for creating (with a known URL) or editing an
#     # object, note that browsers only support POST for now.
#     def put(self, *args, **kwargs):
#         return self.post(*args, **kwargs)

#     def requires_multipart_form(self):
#         return (
#             any([formset.is_multipart() for formset in self.formsets.values()])
#             or super(InlineFormSetView, self).requires_multipart_form()
#         )


class InlineFormSetView(View):
    """ Validates and saves both self.form and self.formsets """
    formset_classes = ()
    formsets = {}

    def requires_multipart_form(self):
        return (
            any([formset.is_multipart() for formset in self.formsets.values()])
            or super(InlineFormSetView, self).requires_multipart_form()
        )

    def get_formset_kwargs(self, formset_class):
        return {
            'data': self.request.POST or None,
            'files': self.request.FILES or None,
            'instance': getattr(self, 'object', None),
        }

    def get_formset(self, formset_class):
        return formset_class(**self.get_formset_kwargs(formset_class))

    def get_form(self, form_class):
        self.formsets = {}
        for formset_class in self.formset_classes:
            key = formset_class.model._meta.model_name
            self.formsets[key] = self.get_formset(formset_class)
        self.context_data['formsets'] = self.formsets
        return super(InlineFormSetView, self).get_form(form_class)

    def is_valid(self, form):
        if not form.is_valid():
            return False
        instance = form.save(commit=False)
        for formset in self.formsets.values():
            formset.instance = instance
            if not formset.is_valid():
                return False
        return True

    def save_form(self, form):
        assert(form.is_valid())
        self.object = form.save()
        for formset in self.formsets.values():
            formset.instance = self.object
            assert(formset.is_valid())
            formset.save()
        return self.object

    def form_valid(self, form):
        self.save_form(form)
        return http.HttpResponseRedirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        if hasattr(self, 'get_object'):
            self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if self.is_valid(form):
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


# TODO:
# - multi-form view (above)

class HashedURLView(django.views.generic.View):
    """
    Use with patterns such as r'/path/with/(?P<param>\w+)/(?P<hash>\w*)/'
    -- prevents alteration of parameters and can act as a verification token.

    The hash pattern must accept a blank value for ease of reversing the URL.

    Place hash parameter at the end of the URL in case the pattern happens to
    exist elsewhere in the URL -- the last occurrence is removed when
    calculating the hash.

    Other parameters in the URL can be obfuscated in conjunction with the
    hash if you like, e.g. r'^verify/a(?P<user_id>\d+)b(?P<hash>\w*)/$'

    Obtain the valid hashed version of a URL by calling HashedURLView.reverse:
    e.g. Verify.reverse('verify', new_user.id)
    """

    hash_parameter = 'hash'

    @classmethod
    def hash_path(cls, path):
        return get_token(path=path)

    @classmethod
    def reverse(cls, to, *args, **kwargs):
        if args:
            args = list(args) + ['']
        else:
            kwargs[cls.hash_parameter] = ''
        base_url = resolve_url(to, *args, **kwargs)
        if args:
            args[-1] = cls.hash_path(base_url)
        else:
            kwargs[cls.hash_parameter] = cls.hash_path(base_url)
        return resolve_url(to, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        provided_hash = kwargs.get(self.hash_parameter)
        expected_hash = self.hash_path(
            ''.join(
                urlquote(request.path).rsplit(provided_hash, 1) # replace last
            )
        )
        if provided_hash != expected_hash:
            return http.HttpResponseForbidden('Invalid hash')
        return super(HashedURLView, self).dispatch(request, *args, **kwargs)

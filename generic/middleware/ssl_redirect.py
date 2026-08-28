""" Loosely modelled off http://djangosnippets.org/snippets/85/ """

from django import http
from django.conf import settings
from django.core.urlresolvers import get_callable

def default_test(request, view_func, view_args, view_kwargs):
    """
    Callable that determines whether SSL should be used.

    Default is the presence of 'SSL' in the view kwargs.

    Override via settings.SSL_REDIRECT_CALLABLE with a dotted path to a
    callable.
    """
    secure_default = getattr(settings, 'SSL_DEFAULT', False)
    return view_kwargs.pop('SSL', secure_default)


use_ssl = get_callable(
    getattr(
        settings,
        'SSL_REDIRECT_CALLABLE',
        'generic.middleware.ssl_redirect.default_test'
    )
)

class SSLRedirect:
    def process_view(self, request, view_func, view_args, view_kwargs):
        secure = use_ssl(request, view_func, view_args, view_kwargs)
        if not secure == request.is_secure():
            if getattr(settings, 'SSL_REDIRECTS_ACTIVE', False):
                return self._redirect(request, secure)

    def _redirect(self, request, secure):
        protocol = 'https' if secure else 'http'
        newurl = "%s://%s%s" % (
            protocol,
            request.get_host(),
            request.get_full_path()
        )
        if settings.DEBUG and request.method == 'POST':
            raise RuntimeError(
                "Django can't perform a SSL redirect while maintaining POST "
                "data. Please structure your views so that redirects only "
                "occur during GETs."
            )
        if getattr(settings, 'SSL_REDIRECTS_PERMANENT', True):
            return http.HttpResponsePermanentRedirect(newurl)
        else:
            return http.HttpResponseRedirect(newurl)

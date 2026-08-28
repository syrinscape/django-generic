try:
    import json
except ImportError:
    from django.utils import simplejson as json

from functools import wraps
from django.conf import settings
try:
    from django.core.cache import cache, get_cache
except ImportError:
    from django.core.cache import cache, caches
    def get_cache(name):
        return caches[name]
from django.http import HttpResponse

import logging
logger = logging.getLogger(__name__)

def cache_method(cache_name=None):
    """
    Caches the result of a method for its object instance using the passed
    arguments to generate a cache key
    """
    def inner(method):
        @wraps(method)
        def wrapped_method(self, *args, **kwargs):
            force_reload = kwargs.pop('force_reload', False)
            cache_obj = get_cache(cache_name) if cache_name else cache
            cache_key = 'generic-%s-%s-%s' % (
                self.__class__.__name__,
                self.pk,
                method.__name__,
            )
            for value in args:
                if isinstance(value, (list, tuple)):
                    value = ','.join(map(str, value))
                cache_key += '-%s' % value
            for key, value in kwargs.items():
                if isinstance(value, (list, tuple)):
                    value = ','.join(map(str, value))
                cache_key += '-%s=%s' % (key, value)
            debug_info = [cache_key]

            if force_reload:
                result = method(self, *args, **kwargs)
                cache_obj.set(cache_key, result)
                debug_info.append('forced reload')
            else:
                try:
                    result = cache_obj.get(cache_key)
                except Exception as e:
                    logger.warning('Cache error: {0}'.format(e))
                    result = None
                if result is None:
                    if not cache_obj.has_key(cache_key):
                        debug_info.append('miss')
                        result = method(self, *args, **kwargs)
                        cache_obj.set(cache_key, result)
                    else:
                        pass # in the cache, but result is None
                else:
                    debug_info.append('hit')
            debug_info.append(result)
            if getattr(settings, 'GENERIC_CACHE_METHOD_DEBUG', False):
                logger.debug(' -- '.join(map(str, debug_info)))
            return result
        return wrapped_method
    return inner


def cache_result_in_instance(method):
    """
    Caches the results of a method into its object instance using the passed
    args as cache key (not the Django cache framework)
    """
    @wraps(method)
    def wrapped_method(self, *args, **kwargs):
        force_reload = kwargs.pop('force_reload', False)
        if kwargs and settings.DEBUG:
            raise RuntimeError(
                "@cache_result_in_instance cannot currently handle methods "
                "with keyword arguments")
        cache_attribute_name = '_%s_cache' % method.__name__
        if not hasattr(self, cache_attribute_name):
            setattr(self, cache_attribute_name, {})
        cache = getattr(self, cache_attribute_name)
        try:
            key = hash(args)
        except TypeError: # unhashable
            return method(self, *args) # forget trying to cache...
        else:
            if not key in cache or force_reload:
                cache[key] = method(self, *args)
            return cache[key]
    return wrapped_method


def json_view(view):
    """
    Convenience decorator for views which return JSON data.

    Allows a view to return data (e.g. a dict) and have it serialized into
    an HTTPResponse with the appropriate mimetype.
    """
    @wraps(view)
    def wrapped_view(request, *args, **kwargs):
        response_data = view(request, *args, **kwargs)
        if isinstance(response_data, HttpResponse):
            if settings.DEBUG:
                raise RuntimeError(
                    'json_view-wrapped method is returning an HttpResponse!')
            else:
                return response_data
        try:
            json_data = json.dumps(response_data)
        except TypeError:
            json_data = json.dumps(
                {'result': False, 'reason': 'Error encoding JSON response'})
        return HttpResponse(json_data, content_type='application/json')
    return wrapped_view

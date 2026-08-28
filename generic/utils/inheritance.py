from functools import reduce
from operator import add

def _get_subclasses(klass):
    return (klass,) + reduce(add, map(_get_subclasses, klass.__subclasses__()), ())

def get_subclasses(model, include_abstract=False):
    """
    Returns a list of unique models that inherit from the specified model. If
    include_abstract is True, abstract inheriting models will also be returned.
    """
    return list(set([klass for klass in _get_subclasses(model) \
        if hasattr(klass, '_meta') and (include_abstract or not klass._meta.abstract)]))
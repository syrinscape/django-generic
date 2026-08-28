import hashlib
from django.conf import settings

def get_token(shortness=5, **params):
    content = settings.SECRET_KEY
    for key in sorted(params.keys()):
        content += '{0!s}={1!s}'.format(key, params[key])
    return hashlib.sha1(content.encode("utf-8")).hexdigest()[::shortness]

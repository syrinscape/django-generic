from django import http
from django.contrib import admin

class ReturnURLAdminMixin(admin.ModelAdmin):
    def response_add(self, request, obj, *args, **kwargs):
        referrer = request.GET.get('_return_url')
        if referrer and not '_continue' in request.POST:
            return http.HttpResponseRedirect(referrer)
        else:
            return super(ReturnURLAdminMixin, self).response_add(
                request, obj, *args, **kwargs)

    def response_change(self, request, obj):
        referrer = request.GET.get('_return_url')
        if (referrer and
            '_continue' not in request.GET and '_continue' not in request.POST and
            '_popup' not in request.GET and '_popup' not in request.POST
        ):
            return http.HttpResponseRedirect(referrer)
        else:
            return super(ReturnURLAdminMixin, self).response_change(
                request, obj)

from django import http
from django.contrib import admin
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase

from generic.admin.mixins.batch import BatchUpdateAdmin


class BatchMessageTextTests(TestCase):
    def test_updated_field_names_are_rendered_in_the_success_message(self):
        class GroupBatchUpdateAdmin(BatchUpdateAdmin):
            batch_update_fields = ("name",)

            def message_user(self, request, message, *args, **kwargs):
                self.success_message = message

            def response_post_save_change(self, request, obj):
                return http.HttpResponse()

        group = Group.objects.create(name="Original")
        request = RequestFactory().post(
            "/admin/auth/group/batch-update/",
            {
                "ids": str(group.pk),
                "name": "Renamed",
                "updating-name": "on",
            },
        )
        model_admin = GroupBatchUpdateAdmin(Group, admin.site)

        response = model_admin.batch_update_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("name", model_admin.success_message)

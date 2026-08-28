from django.contrib import admin
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase

from generic.admin.mixins.batch import BatchUpdateAdmin


class BatchFormCleaningTests(TestCase):
    def test_selected_fields_are_recorded_during_validation(self):
        class GroupBatchUpdateAdmin(BatchUpdateAdmin):
            batch_update_fields = ("name",)

        request = RequestFactory().post("/admin/auth/group/batch-update/")
        model_admin = GroupBatchUpdateAdmin(Group, admin.site)
        form_class = model_admin.get_batch_update_form_class(request)
        form = form_class({
            "name": "Renamed",
            "updating-name": "on",
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.fields_to_update, ["name"])

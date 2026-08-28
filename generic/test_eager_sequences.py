from django import http
from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.test import RequestFactory, TestCase, override_settings

from generic.admin.mixins.batch import BatchUpdateAdmin, BatchUpdateForm
from generic.admin.mixins.cooking import CookedIdAdmin
from generic.admin.mixins.polymorphic import PolymorphicAdmin
from generic.admin.mixins.rich_text import make_rich


class SequenceAdminSite(admin.AdminSite):
    def each_context(self, request):
        return {}


class EagerSequenceTests(TestCase):
    def test_batch_form_can_replace_many_to_many_fields_during_setup(self):
        class GroupBatchUpdateForm(BatchUpdateForm):
            class Meta(object):
                model = Group
                fields = ("permissions", "name")

        form = GroupBatchUpdateForm()

        self.assertEqual(
            list(form.fields),
            [
                "name",
                "m2m_remove_permissions",
                "m2m_add_permissions",
            ],
        )

    @override_settings(
        TINYMCE_JS_URL="tiny-mce.js",
        TINYMCE_JS_INIT_URL=None,
    )
    def test_rich_media_keeps_base_scripts_and_configured_urls(self):
        class BaseAdmin(object):
            class Media(object):
                js = ("base.js",)

        rich_admin = make_rich(BaseAdmin)

        self.assertEqual(
            rich_admin.Media.js,
            ("base.js", "tiny-mce.js"),
        )

    def test_batch_update_keeps_ordered_template_fallbacks(self):
        class GroupBatchUpdateAdmin(BatchUpdateAdmin):
            batch_update_fields = ("name",)

            def has_change_permission(self, request, obj=None):
                return True

        request = RequestFactory().get(
            "/admin/auth/group/batch-update/",
            {"ids": "999999"},
        )
        model_admin = GroupBatchUpdateAdmin(
            Group,
            SequenceAdminSite(name="sequence-test"),
        )

        response = model_admin.batch_update_view(request)

        self.assertEqual(
            response.template_name,
            [
                "admin/auth/group/batch_update.html",
                "admin/auth/batch_update.html",
                "admin/batch_update.html",
                "admin/generic/batch_update.html",
            ],
        )

    def test_cooked_ids_translates_invalid_integer_to_not_found(self):
        class UserCookedIdAdmin(CookedIdAdmin):
            cooked_id_fields = ("groups",)

        class GroupAdmin(admin.ModelAdmin):
            def has_change_permission(self, request, obj=None):
                return True

        admin_site = admin.AdminSite(name="cooked-id-test")
        admin_site.register(Group, GroupAdmin)
        model_admin = UserCookedIdAdmin(User, admin_site)

        with self.assertRaises(http.Http404):
            model_admin.cook_ids(
                RequestFactory().get("/admin/auth/user/cook-ids/"),
                None,
                "groups",
                "1,,2",
            )

    def test_polymorphic_redirect_encodes_query_items(self):
        request = RequestFactory().post(
            "/admin/auth/group/add/?q=sound+set&page=2",
            {"__subclass": "group"},
        )
        model_admin = PolymorphicAdmin(
            Group,
            admin.AdminSite(name="polymorphic-test"),
        )

        response = model_admin.add_view(request)

        location_parts = response["Location"].split("&")
        self.assertEqual(location_parts[0], "?__subclass=group")
        self.assertEqual(
            set(location_parts[1:]),
            {"q=sound+set", "page=2"},
        )
        self.assertIsInstance(response["Location"], str)

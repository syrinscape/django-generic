from django.contrib.auth.models import Group
from django.test import RequestFactory, SimpleTestCase

from generic.admin.mixins.cooking import BaseCookedIdAdmin


class UnpermittedUser(object):
    def has_perm(self, permission):
        return False


class CookedIdTextTests(SimpleTestCase):
    def test_cooked_representation_uses_model_text(self):
        request = RequestFactory().get("/")
        request.user = UnpermittedUser()
        group = Group(id=7, name="Editors")

        cooked = BaseCookedIdAdmin().cook(group, request, "group")

        self.assertEqual(cooked["text"], "Editors")

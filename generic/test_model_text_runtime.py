import unittest

import django
from django.conf import settings


if not settings.configured:
    settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            },
        },
        INSTALLED_APPS=(
            "django.contrib.auth",
            "django.contrib.contenttypes",
        ),
        SECRET_KEY="django-generic-tests",
    )

if hasattr(django, "setup"):
    django.setup()

from django.db import models
from django.utils.encoding import force_text

from generic.mixins import Inheritable
from generic.user.email_based.models import EmailBasedUser


class ModelTextTests(unittest.TestCase):
    def test_inheritable_model_preserves_default_model_text(self):
        class ModelMeta(object):
            def get_all_related_objects(self):
                return []

        class Parent(Inheritable):
            _meta = ModelMeta()

        self.assertEqual(force_text(Parent()), "Parent object")

    def test_email_user_text_is_the_full_name(self):
        class User(EmailBasedUser):
            class Meta:
                app_label = "generic_tests"

        user = User(first_name="Ada", last_name="Lovelace")

        self.assertEqual(force_text(user), "Ada Lovelace")


if __name__ == "__main__":
    unittest.main()

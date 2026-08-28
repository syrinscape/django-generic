from django.test import SimpleTestCase
from django.test.utils import override_settings

from generic.utils.testing import get_hash
from generic.utils.tokens import get_token


class HashlibTextTests(SimpleTestCase):
    def test_get_hash_encodes_logical_text(self):
        self.assertEqual(
            get_hash("compatibility", length=40),
            "4547bd227f901b526413ad5d771186a37a331aed",
        )

    @override_settings(SECRET_KEY="fixed-non-secret")
    def test_get_token_encodes_logical_text(self):
        self.assertEqual(
            get_token(shortness=1, path="/fixed"),
            "64354108d50b71c263531fc1a4c9303906780751",
        )

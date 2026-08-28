from django.test import SimpleTestCase

from generic.templatetags.generic_tags import domain_only


class UrlCompatibilityTests(SimpleTestCase):
    def test_domain_only_returns_text_host_and_port(self):
        domain = domain_only(
            "https://www.example.com:8443/path?q=sound"
        )

        self.assertEqual(domain, "example.com:8443")
        self.assertIsInstance(domain, str)

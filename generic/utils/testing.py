from __future__ import absolute_import

import hashlib
import logging
import re

try:
    from django.contrib.auth import get_user_model
except ImportError:
    # Django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()
from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.db import DEFAULT_DB_ALIAS, connections
try:
    from django.shortcuts import resolve_url
except ImportError:
    from .future import resolve_url
import django.test
from django.test.testcases import _AssertNumQueriesContext
from django.test.utils import override_settings
from django.contrib.auth import authenticate

logger = logging.getLogger(__name__)

TEMPLATE_CONTEXT_PROCESSORS = set(settings.TEMPLATE_CONTEXT_PROCESSORS)
TEMPLATE_CONTEXT_PROCESSORS.add('django.core.context_processors.request')

def get_hash(string, length=8):
    """ Shortcut for generating short hash strings """
    return hashlib.sha1(string.encode("utf-8")).hexdigest()[:length]

def reloaded(obj):
    """ Reload an object from the database """
    return obj.__class__._default_manager.get(pk=obj.pk)


class Client(django.test.Client):
    def resolve_path(self, path):
        if isinstance(path, (tuple, list)): # ala @models.permalink
            return reverse(path[0], None, *path[1:3])
        else:
            return resolve_url(path)

    def get(self, path, *args, **kwargs):
        return super(Client, self).get(
            self.resolve_path(path), *args, **kwargs)

    def post(self, path, *args, **kwargs):
        return super(Client, self).post(
            self.resolve_path(path), *args, **kwargs)

    def head(self, path, *args, **kwargs):
        return super(Client, self).head(
            self.resolve_path(path), *args, **kwargs)

    def options(self, path, *args, **kwargs):
        return super(Client, self).options(
            self.resolve_path(path), *args, **kwargs)

    def put(self, path, *args, **kwargs):
        return super(Client, self).put(
            self.resolve_path(path), *args, **kwargs)

    def delete(self, path, *args, **kwargs):
        return super(Client, self).delete(
            self.resolve_path(path), *args, **kwargs)

    def generic(self, method, path, *args, **kwargs):
        return super(Client, self).generic(
            method, self.resolve_path(path), *args, **kwargs)


class TestCase(django.test.TestCase):
    """ TestCase with moderate superpowers """
    client_class = Client

    PASSWORDS = {}

    def _assertContains(self, super_method, response, text, **kwargs):
        """
        Logs content on failure and accepts case_sensitive kwarg.
        TODO: modify *copy* of content/text rather than actual...
        """
        case_sensitive = kwargs.pop('case_sensitive', True)
        if not case_sensitive:
            response.content = response.content.lower()
            text = text.lower()
        try:
            super_method(response, text, **kwargs)
        except AssertionError:
            logger.warning('Searched content: """%s"""' % response.content)
            raise

    def assertRedirects(self, response, expected_url, *args, **kwargs):
        ignore_querystring = kwargs.pop('ignore_querystring', False)
        try:
            super(TestCase, self).assertRedirects(
                response, expected_url, *args, **kwargs)
        except AssertionError as e:
            if ignore_querystring and re.match(
                    r"Response redirected to '(.*){0}\?.*', "
                    r"expected '\1{0}'".format(expected_url),
                    str(e)
            ):
                pass # silence AssertionError; only query string differed
            else:
                raise

    def assertContains(self, *args, **kwargs):
        return self._assertContains(
            super(TestCase, self).assertContains, *args, **kwargs)

    def assertNotContains(self, *args, **kwargs):
        return self._assertContains(
            super(TestCase, self).assertNotContains, *args, **kwargs)

    def create_user(self, identifier, password=None, super=False, **kwargs):
        """ Shortcut for creating users """
        password = password or get_hash(identifier+'PASSWORD')
        method = (
            User._default_manager.create_superuser if super else
            User._default_manager.create_user
        )
        self.PASSWORDS[identifier] = password
        return method(identifier, password=password, **kwargs)

    def login(self, username):
        """
        Shortcut for logging in which asserts success and stores the
        authenticated user as ``self.authenticated_user``.
        """
        kwargs = {
            'username': username,
            'password': self.PASSWORDS[username],
        }
        self.assertTrue(self.client.login(**kwargs))
        self.authenticated_user = authenticate(**kwargs)

    def _test_urls(self, url_attributes):
        """ Example helper for quick/dirty URL coverage """
        for url, attributes in url_attributes:
            response = self.client.get(url)
            try:
                if 'status_code' in attributes:
                    self.assertEqual(
                        response.status_code, attributes.pop('status_code'))
                if 'template' in attributes:
                    self.assertTemplateUsed(
                        response, attributes.pop('template'))
                if 'contains' in attributes:
                    self.assertContains(response, attributes.pop('contains'))
                if '~contains' in attributes:
                    self.assertNotContains(
                        response, attributes.pop('~contains'))
                if 'icontains' in attributes:
                    self.assertContains(
                        response,
                        attributes.pop('icontains'),
                        case_sensitive=False
                    )
                if '~icontains' in attributes:
                    self.assertNotContains(
                        response,
                        attributes.pop('~icontains'),
                        case_sensitive=False
                    )
                if 'context' in attributes:
                    for key, value in attributes.pop('context').items():
                        if callable(value):
                            self.assertTrue(value(response.context[key]))
                        else:
                            self.assertEqual(response.context[key], value)
                if 'redirects' in attributes:
                    self.assertRedirects(response, attributes.pop('redirects'))
                if 'redirects_permanently' in attributes:
                    self.assertRedirects(
                        response,
                        attributes.pop('redirects_permanently'),
                        status_code=301,
                    )

                # that's all folks...
                self.assertFalse(
                    attributes, 'Untested attributes: {!r}'.format(attributes))
            except AssertionError:
                logger.warning(
                    'AssertionError while testing URL: {!r}'.format(url))
                raise

    @override_settings(TEMPLATE_CONTEXT_PROCESSORS=TEMPLATE_CONTEXT_PROCESSORS)
    def _test_admin(self, MODELS):
        """
        Shortcut for detecting broken admin change lists/forms.
        Beware query expense involved...
        """
        for model in MODELS:
            msg_prefix = 'While testing %r, ' % model

            changelist_url = reverse(
                'admin:%s_%s_changelist' % (
                    model._meta.app_label, model._meta.model_name
                )
            )
            response = self.client.get(changelist_url)
            self.assertTemplateUsed(
                response, 'admin/change_list.html', msg_prefix=msg_prefix)

            add_url = reverse(
                'admin:%s_%s_add' % (
                    model._meta.app_label,
                    model._meta.model_name
                )
            )
            response = self.client.get(add_url)
            self.assertTemplateUsed(
                response, 'admin/change_form.html', msg_prefix=msg_prefix)

            model_admin = response.context['adminform'].model_admin

            for instance in model_admin.get_queryset(response.context['request']):
                change_url = reverse(
                    'admin:%s_%s_change' % (
                        model._meta.app_label,
                        model._meta.model_name,
                    ),
                    args=(instance.pk,)
                )
                response = self.client.get(change_url)
                self.assertTemplateUsed(
                    response, 'admin/change_form.html', msg_prefix=msg_prefix)

    def assertNumQueries(self, num, func=None, *args, **kwargs):
        """ Identical to TransactionTestCase, but with custom Context """
        using = kwargs.pop("using", DEFAULT_DB_ALIAS)
        conn = connections[using]

        context = _VerboseAssertNumQueriesContext(self, num, conn)
        if func is None:
            return context

        with context:
            func(*args, **kwargs)

    def extract_urls_from_email(self, message=None, path_only=True):
        if message is None:
            message = mail.outbox[-1]
        matches = re.findall(
            r'(?P<scheme>\w*:?//)(?P<domain>[\w\-\.:]+)(?P<path>\S+)',
            message.body,
        )
        if path_only:
            return list(zip(*matches))[2]
        else:
            return list(map(''.join, matches))

    def extract_url_from_email(self, message=None, path_only=True):
        urls = self.extract_urls_from_email(message, path_only)
        self.assertEqual(len(urls), 1)
        return urls[0]


class _VerboseAssertNumQueriesContext(_AssertNumQueriesContext):
    """
    Modified context manager which logs the unexpected queries.
    """

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            super(_VerboseAssertNumQueriesContext, self).__exit__(
                exc_type, exc_value, traceback)
        except AssertionError as e:
            start = getattr(
                self, 'initial_queries', getattr(self, 'starting_queries', 0)
            )
            # see django 952ba5237ea62e7647cdd5214b1df79c0e7cea38
            queries = self.connection.queries[start:]
            logger.warning(
                '\n    '.join(
                    ['Unexpected queries (%s):' % e] +
                    list(map(str, queries))
                )
            )
            raise


#---[ Selenium ]---------------------------------------------------------------

from django.test import LiveServerTestCase

class SeleniumTests(LiveServerTestCase):
    save_post_test_screenshots = True

    @classmethod
    def setUpClass(cls):
        from selenium.webdriver.firefox.webdriver import WebDriver
        cls.driver = WebDriver()
        super(SeleniumTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super(SeleniumTests, cls).tearDownClass()

    def tearDown(self):
        if self.save_post_test_screenshots:
            self.driver.save_screenshot(
                '/tmp/{0}_{1}.png'.format(
                    self.__class__.__name__,
                    self._testMethodName
                )
            )
        if mail.outbox and 'Internal Server Error' in mail.outbox[-1].subject:
            print(mail.outbox[-1].body)
        super(SeleniumTests, self).tearDown()

    def get(self, url, *args, **kwargs):
        return self.driver.get(''.join([self.live_server_url, url]))

    def assertContainsText(
            self, needle, container_tag='body', case_sensitive=False):
        haystack = self.driver.find_element_by_tag_name(container_tag).text
        if not case_sensitive:
            haystack = haystack.lower()
            needle = needle.lower()
        self.assertTrue(needle in haystack)

    def assertContains(self, needle, case_sensitive=False):
        haystack = self.driver.page_source
        if not case_sensitive:
            haystack = haystack.lower()
            needle = needle.lower()
        self.assertTrue(needle in haystack)

    def fill_field(self, field_name, value):
        input = self.driver.find_element_by_name(field_name)
        options = input.find_elements_by_tag_name('option')
        if options:
            for option in options:
                if option.get_attribute('value') == value:
                    option.click()
                    return
            logger.warning(
                u"Couldn't find select[name={0}] value ({1})".format(
                    field_name,
                    value,
                )
            )
        else:
            input.send_keys(value)

    def fill_fields(self, data):
        for field_name, value in data.items():
            self.fill_field(field_name, value)

    def submit_form(self):
        self.driver.find_element_by_tag_name('form').submit()

    def get_url(self):
        return self.driver.current_url.replace(self.live_server_url, '', 1)

    def print_text(self, container_tag='body'):
        print(self.driver.find_element_by_tag_name(container_tag).text)

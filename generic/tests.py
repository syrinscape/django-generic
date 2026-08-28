import unittest

import django
from django import http
from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.conf.urls import include, patterns, url
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils.encoding import force_text
from . import decorators
from .admin.mixins.batch import BatchUpdateAdmin
from .admin.mixins.cooking import BaseCookedIdAdmin, CookedSingletonFix
from .admin.mixins.polymorphic import PolymorphicAdmin
from .mixins import Inheritable

request_factory = RequestFactory()
urlpatterns = patterns('', url(r'^admin/', include(admin.site.urls)))

@decorators.json_view
def return_dict(request):
    return {'test': 123}

@decorators.json_view
def return_http_response(request):
    return http.HttpResponse('test')

class GenericTest(TestCase):
    def test_json_view_with_dict(self):
        request = request_factory.get('/')
        response = return_dict(request)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response.content, b'{"test": 123}')

    def test_json_view_with_http_response(self):
        request = request_factory.get('/')
        response = return_http_response(request)
        self.assertTrue('text/html' in response['Content-Type'])
        self.assertEqual(response.content, b'test')


class PolymorphicAdminTests(unittest.TestCase):
    def setUp(self):
        self.model_admin = PolymorphicAdmin(User, admin.site)

    def test_get_model_without_subclass_returns_none(self):
        request = request_factory.get('/')

        self.assertIsNone(self.model_admin.get_model(request))

    def test_get_model_resolves_selected_subclass(self):
        request = request_factory.get('/', {'__subclass': 'group'})

        self.assertIs(self.model_admin.get_model(request), Group)

    def test_get_model_uses_existing_objects_class(self):
        request = request_factory.get('/')
        obj = Group()

        self.assertIs(self.model_admin.get_model(request, obj), Group)


class PermittedUser(object):
    def __init__(self):
        self.permissions_checked = []

    def has_perm(self, permission):
        self.permissions_checked.append(permission)
        return True


class CookedIdAdminTests(unittest.TestCase):
    def test_cook_uses_model_name_for_permission_and_edit_url(self):
        request = request_factory.get('/')
        request.user = PermittedUser()
        obj = Group(id=7, name='Editors')

        cooked = BaseCookedIdAdmin().cook(obj, request, 'group')

        self.assertEqual(
            request.user.permissions_checked,
            ['auth.change_group'],
        )
        self.assertEqual(cooked['edit_url'], '/admin/auth/group/7/')

    def test_singleton_fix_uses_model_name_for_add_url(self):
        class CookedGroupAdmin(CookedSingletonFix, admin.ModelAdmin):
            pass

        model_admin = CookedGroupAdmin(Group, admin.site)

        self.assertIn('/admin/auth/group/add/', force_text(model_admin.media))


class BatchUpdateAdminTests(TestCase):
    class GroupBatchUpdateAdmin(BatchUpdateAdmin):
        batch_update_fields = ('name',)

        def has_change_permission(self, request, obj=None):
            return True

    def assert_batch_context(self, response, admin_site, request):
        self.assertTrue(admin_site.each_context_called)
        self.assertTrue(response.context_data['from_each_context'])
        self.assertEqual(response.context_data['count'], 0)
        self.assertIs(response.context_data['model_meta'], Group._meta)
        self.assertTrue(response.context_data['has_change_permission'])
        self.assertIn('form', response.context_data)
        self.assertIn('media', response.context_data)

    @unittest.skipUnless(
        django.VERSION >= (1, 8),
        'Django 1.8 introduced request-aware AdminSite context',
    )
    def test_batch_update_passes_request_to_admin_site_context(self):
        class ContextAdminSite(admin.AdminSite):
            each_context_called = False

            def each_context(self, request):
                self.each_context_called = request is batch_request
                return {
                    'from_each_context': True,
                    'count': 99,
                }

        batch_request = request_factory.get(
            '/admin/auth/group/batch-update/',
            {'ids': '999999'},
        )
        admin_site = ContextAdminSite(name='batch-context-test')
        model_admin = self.GroupBatchUpdateAdmin(Group, admin_site)

        response = model_admin.batch_update_view(batch_request)

        self.assert_batch_context(response, admin_site, batch_request)

    @unittest.skipUnless(
        django.VERSION < (1, 8),
        'Django 1.7 AdminSite context does not accept a request',
    )
    def test_batch_update_calls_legacy_admin_site_context_without_request(self):
        class ContextAdminSite(admin.AdminSite):
            each_context_called = False

            def each_context(self):
                self.each_context_called = True
                return {
                    'from_each_context': True,
                    'count': 99,
                }

        batch_request = request_factory.get(
            '/admin/auth/group/batch-update/',
            {'ids': '999999'},
        )
        admin_site = ContextAdminSite(name='legacy-batch-context-test')
        model_admin = self.GroupBatchUpdateAdmin(Group, admin_site)

        response = model_admin.batch_update_view(batch_request)

        self.assert_batch_context(response, admin_site, batch_request)


class InheritableTests(unittest.TestCase):
    class RelationField(object):
        class rel(object):
            parent_link = True

    class Meta(object):
        def __init__(self, related_objects):
            self.related_objects = related_objects

        def get_all_related_objects(self):
            return self.related_objects

    class Relation(object):
        def __init__(self, model, related_model, accessor_name):
            self.model = model
            self.related_model = related_model
            self.field = InheritableTests.RelationField()
            self.accessor_name = accessor_name

        def get_accessor_name(self):
            return self.accessor_name

    class LegacyRelation(object):
        def __init__(self, model, accessor_name):
            self.model = model
            self.field = InheritableTests.RelationField()
            self.accessor_name = accessor_name

        def get_accessor_name(self):
            return self.accessor_name

    def test_get_leaf_object_follows_parent_link_to_related_model(self):
        class Parent(Inheritable):
            class DoesNotExist(Exception):
                pass

        class Leaf(Inheritable):
            class DoesNotExist(Exception):
                pass

        relation = self.Relation(Parent, Leaf, 'leaf')
        parent = Parent()
        leaf = Leaf()
        parent._meta = self.Meta([relation])
        parent.leaf = leaf
        leaf._meta = self.Meta([])

        self.assertIs(parent.get_leaf_object(), leaf)

    def test_get_leaf_object_ignores_absent_related_model(self):
        class Parent(Inheritable):
            class DoesNotExist(Exception):
                pass

        class Leaf(Inheritable):
            class DoesNotExist(Exception):
                pass

        class MissingLeaf(object):
            def __get__(self, instance, owner):
                instance.lookup_count += 1
                raise Leaf.DoesNotExist

        Parent.leaf = MissingLeaf()
        relation = self.Relation(Parent, Leaf, 'leaf')
        parent = Parent()
        parent._meta = self.Meta([relation])
        parent.lookup_count = 0

        self.assertIs(parent.get_leaf_object(), parent)
        self.assertEqual(parent.lookup_count, 1)

    def test_get_leaf_object_falls_back_to_relation_model(self):
        class Parent(Inheritable):
            pass

        class Leaf(Inheritable):
            pass

        relation = self.LegacyRelation(Leaf, 'leaf')
        parent = Parent()
        leaf = Leaf()
        parent._meta = self.Meta([relation])
        parent.leaf = leaf
        leaf._meta = self.Meta([])

        self.assertIs(parent.get_leaf_object(), leaf)

import unittest

from django import http
from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.test.client import RequestFactory
from . import decorators
from .admin.mixins.polymorphic import PolymorphicAdmin

request_factory = RequestFactory()

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
        self.assertEqual(response.content, '{"test": 123}')

    def test_json_view_with_http_response(self):
        request = request_factory.get('/')
        response = return_http_response(request)
        self.assertTrue('text/html' in response['Content-Type'])
        self.assertEqual(response.content, 'test')


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

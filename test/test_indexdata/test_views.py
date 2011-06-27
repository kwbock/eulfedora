#!/usr/bin/env python

# file test_indexdata/test_views.py
# 
#   Copyright 2011 Emory University Libraries
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from mock import Mock, patch
import unittest
import os

# must be set before importing anything from django
os.environ['DJANGO_SETTINGS_MODULE'] = 'testsettings'

from django.conf import settings
from django.http import Http404, HttpRequest
from django.utils import simplejson

from eulfedora.indexdata.views import index_config, index_data
from eulfedora.models import DigitalObject, Datastream
from eulfedora.server import Repository

TEST_PIDSPACE = getattr(settings, 'FEDORA_PIDSPACE', 'testme')

class SimpleDigitalObject(DigitalObject):
    CONTENT_MODELS = ['info:fedora/%s:SimpleDjangoCModel' % TEST_PIDSPACE]
    # NOTE: distinguish from SimpleCModel in non-django fedora unit tests
    # and use configured pidspace for automatic clean-up

    # extend digital object with datastreams for testing
    text = Datastream("TEXT", "Text datastream", defaults={
            'mimetype': 'text/plain',
        })

    def _index_data(self):
        pid = 'DoesNotExist'

    def index(self):
        _index_data(self)

class WebserviceViewsTest(unittest.TestCase):

    def setUp(self):
        #Creation of a HTTP request object for tests.
        self.request = HttpRequest
        self.request.META = { 'REMOTE_ADDR': '127.0.0.1' }
        self.pids = []

    def test_index_details(self):
        repo = Repository()
        for pid in self.pids:
            repo.purge_object(pid)

        #Test with no settings set.
        self.assertRaises(AttributeError, index_config, self.request)

        #Test with only the allowed SOLR url set.
        settings.EUL_SOLR_SERVER_URL = 'http://localhost:5555'
        self.assertRaises(AttributeError, index_config, self.request)


        #Test with this IP not allowed to hit the service.
        settings.EUL_INDEXER_ALLOWED_IPS = ['0.13.23.134']
        response = index_config(self.request)
        expected, got = 403, response.status_code
        self.assertEqual(expected, got,
            'Expected %s but returned %s for indexdata/index_details view' \
                % (expected, got))
        expected, got = 'text/html', response['Content-Type']
        self.assertEqual(expected, got,
            'Expected %s but returned %s for mimetype on indexdata/index_details view' \
                % (expected, got))
        

        #Test with this IP allowed to hit the view.
        settings.EUL_INDEXER_ALLOWED_IPS = ['0.13.23.134', '127.0.0.1']
        response = index_config(self.request)
        expected, got = 200, response.status_code
        self.assertEqual(expected, got,
            'Expected %s but returned %s for indexdata/index_details view' \
                % (expected, got))
        expected, got = 'application/json', response['Content-Type']
        self.assertEqual(expected, got,
            'Expected %s but returned %s for mimetype on indexdata/index_details view' \
                % (expected, got)) 
        self.assert_('SOLR_URL' in response.content)
        self.assert_('CONTENT_MODELS' in response.content)

        #Test with the "ANY" setting for allowed IPs
        settings.INDEXER_ALLOWED_IPS = 'ANY'
        response = index_config(self.request)
        expected, got = 200, response.status_code
        self.assertEqual(expected, got,
            'Expected %s but returned %s for indexdata/index_details view' \
                % (expected, got))

    def test_index_data(self):
        # create a test object for testing index data view
        repo = Repository()
        testobj = repo.get_object(type=SimpleDigitalObject)
        testobj.label = 'test object'
        testobj.owner = 'tester'
        testobj.save()
        self.pids.append(testobj.pid)

        response = index_data(self.request, testobj.pid)
        expected, got = 200, response.status_code
        self.assertEqual(expected, got,
            'Expected %s but returned %s for index_data view' \
                % (expected, got))
        expected, got = 'application/json', response['Content-Type']
        self.assertEqual(expected, got,
            'Expected %s but returned %s for mimetype on index_data view' \
                % (expected, got)) 
        response_data = simplejson.loads(response.content)
        self.assertEqual(testobj.index_data(), response_data,
             'Response content loaded from JSON should be equal to object indexdata')
        
        # non-existent pid should generate a 404
        self.assertRaises(Http404, index_data, self.request, 'bogus:testpid')

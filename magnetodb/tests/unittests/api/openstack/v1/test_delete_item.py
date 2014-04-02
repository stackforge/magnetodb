#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import httplib
import json
import unittest

import mock
from magnetodb.tests.fake import magnetodb_api_fake


class DeleteItemTestCase(unittest.TestCase):
    """The test for delete_item method of openstack v1 ReST API."""

    @classmethod
    def setUpClass(cls):
        magnetodb_api_fake.run_fake_magnetodb_api()

    @classmethod
    def tearDownClass(cls):
        magnetodb_api_fake.stop_fake_magnetodb_api()

    @mock.patch('magnetodb.storage.delete_item')
    def test_delete_item(self, mock_delete_item):
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json'}

        conn = httplib.HTTPConnection('localhost:8080')
        url = '/v1/fake_project_id/data/tables/the_table/delete_item'

        # basic test case: delete item by key
        body = """
            {
                "key": {
                    "ForumName": {
                        "S": "MagnetoDB"
                    },
                    "Subject": {
                        "S": "How do I delete an item?"
                    }
                }
            }
        """

        conn.request("POST", url, headers=headers, body=body)
        response = conn.getresponse()

        self.assertTrue(mock_delete_item.called)

        json_response = response.read()

        response_payload = json.loads(json_response)
        self.assertEqual({}, response_payload)

        # more options for delete item: in addition to key,
        # expected conditions and/or return values can be specified
        # expected conditions represents an attribute name to check,
        # along with value comparison
        # or value evaluation before attempting the conditional delete

        body = """
            {
                "key": {
                    "ForumName": {
                        "S": "MagnetoDB"
                    },
                    "Subject": {
                        "S": "How do I delete an item?"
                    }
                },
                "expected": {
                    "Subject": {
                    "value": {
                        "S": "How do I delete an item?"
                    }
                },
                "Replies": {
                        "exists": false
                    }
                },
                "returnValues": ""
            }
        """

        conn.request("POST", url, headers=headers, body=body)
        response = conn.getresponse()

        self.assertTrue(mock_delete_item.called)

        json_response = response.read()

        response_payload = json.loads(json_response)
        self.assertEqual({}, response_payload)

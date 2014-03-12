# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
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

#from boto import exception

import tempest.clients
import tempest.config
from tempest import exceptions
import tempest.test
from tempest.common.utils import data_utils
from tempest.openstack.common import log as logging


LOG = logging.getLogger(__name__)


class MagnetoDBTestCase(tempest.test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(MagnetoDBTestCase, cls).setUpClass()
        cls.os = tempest.clients.Manager()
        cls.client = cls.os.magnetodb_client
        cls._resource_trash_bin = {}

        # SMOKE TABLE: THREADS
        cls.hashkey = 'forum'
        cls.rangekey = 'subject'

        cls.smoke_attrs = [
            {'AttributeName': cls.hashkey, 'AttributeType': 'S'},
            {'AttributeName': cls.rangekey, 'AttributeType': 'S'}
        ]
        # add this attribute to smoke_attrs if want to create index
        # TODO(yyekovenko): full list of attrs should be clarified
        cls.index_attrs = [
            {'AttributeName': 'last_posted_by', 'AttributeType': 'S'},
            #{'AttributeName': 'message', 'AttributeType': 'S'},
            #{'AttributeName': 'replies', 'AttributeType': 'N'}
        ]

        cls.smoke_schema = [
            {'AttributeName': cls.hashkey, 'KeyType': 'HASH'},
            {'AttributeName': cls.rangekey, 'KeyType': 'RANGE'}
        ]
        cls.smoke_gsi = None
        cls.smoke_lsi = [
            {
                'IndexName': 'last_posted_by_index',
                'KeySchema': [
                    {'AttributeName': cls.hashkey, 'KeyType': 'HASH'},
                    {'AttributeName': 'last_posted_by', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]

    @classmethod
    def tearDownClass(cls):
        """Calls the callables added by addResourceCleanUp,
        when you overwire this function dont't forget to call this too.
        """
        fail_count = 0
        trash_keys = sorted(cls._resource_trash_bin, reverse=True)
        for key in trash_keys:
            (function, pos_args, kw_args) = cls._resource_trash_bin[key]
            try:
                LOG.debug("Cleaning up: %s" %
                          friendly_function_call_str(function, *pos_args,
                                                     **kw_args))
                function(*pos_args, **kw_args)
            except BaseException as exc:
                fail_count += 1
                LOG.exception(exc)
            finally:
                del cls._resource_trash_bin[key]
        super(MagnetoDBTestCase, cls).tearDownClass()
        # NOTE(afazekas): let the super called even on exceptions
        # The real exceptions already logged, if the super throws another,
        # does not causes hidden issues
        if fail_count:
            raise exceptions.TearDownException(num=fail_count)

    @classmethod
    def addResourceCleanUp(cls, function, *args, **kwargs):
        """Adds CleanUp callable, used by tearDownClass.
        Recommended to a use (deep)copy on the mutable args.
        """
        cls._sequence = cls._sequence + 1
        cls._resource_trash_bin[cls._sequence] = (function, args, kwargs)
        return cls._sequence

    @classmethod
    def cancelResourceCleanUp(cls, key):
        """Cancel Clean up request."""
        del cls._resource_trash_bin[key]

    @classmethod
    def wait_for_table_active(cls, table_name, timeout=120, interval=3):
        def check():
            resp = cls.client.describe_table(table_name)
            if "Table" in resp and "TableStatus" in resp["Table"]:
                return resp["Table"]["TableStatus"] == "ACTIVE"

        return tempest.test.call_until_true(check, timeout, interval)

    def wait_for_table_deleted(self, table_name, timeout=120, interval=3):
        def check():
            return table_name not in self.client.list_tables()['TableNames']

        return tempest.test.call_until_true(check, timeout, interval)

    @staticmethod
    def build_smoke_item(forum, subject, message='message_text',
                         last_posted_by='John', replies='1'):
        return {
            "forum": {"S": forum},
            "subject": {"S": subject},
            "message": {"S": message},
            "last_posted_by": {"S": last_posted_by},
            "replies": {"N": replies},
        }

    def put_smoke_item(self, table_name,
                       forum, subject, message='message_text',
                       last_posted_by='John', replies='1'):

        item = self.build_smoke_item(forum, subject, message,
                                     last_posted_by, replies)
        self.client.put_item(table_name, item)
        return item

    def populate_smoke_table(self, table_name, keycount, count_per_key):
        """
        Put [keycont*count_per_key] autogenerated items to the table.

        In result, [keycount] unique hash key values
        and [count_per_key] items for each has key value are generated.

        For example, to generate some number of items for the only hash key,
        set keycount=1 and count_per_key=needed_number_of_items.
        """
        new_items = []
        for _ in range(keycount):
            forum = 'forum%s' % data_utils.rand_int_id()
            for i in range(count_per_key):
                item = self.put_smoke_item(
                    table_name, forum=forum, subject='subject%s' % i,
                    message=data_utils.rand_name(),
                    last_posted_by=data_utils.rand_uuid(),
                    replies=str(data_utils.rand_int_id())
                )
                new_items.append(item)
        return new_items


def friendly_function_name_simple(call_able):
    name = ""
    if hasattr(call_able, "im_class"):
        name += call_able.im_class.__name__ + "."
    name += call_able.__name__
    return name


def friendly_function_call_str(call_able, *args, **kwargs):
    string = friendly_function_name_simple(call_able)
    string += "(" + ", ".join(map(str, args))
    if len(kwargs):
        if len(args):
            string += ", "
    string += ", ".join("=".join(map(str, (key, value)))
              for (key, value) in kwargs.items())
    return string + ")"

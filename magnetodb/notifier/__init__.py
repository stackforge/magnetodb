# Copyright 2014 Symantec Corporation.
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

import socket

from oslo.config import cfg
from oslo.messaging import notify
from oslo.messaging import serializer
from oslo.messaging import transport
from oslo.serialization import jsonutils

from magnetodb import common as mdb_common
from magnetodb.notifier import notifier_statsd_adapter
from magnetodb.notifier.notifier_statsd_util import *
from magnetodb.openstack.common import context as ctxt

extra_notifier_opts = [
    cfg.StrOpt('notification_service',
               default=mdb_common.PROJECT_NAME,
               help='Service publisher_id for outgoing notifications'),
    cfg.StrOpt('default_publisher_id',
               default=None,
               help='Default publisher_id for outgoing notifications'),

]

cfg.CONF.register_opts(extra_notifier_opts)

__NOTIFIER = None
__STATSD_ADAPTED_NOTIFIER = None


def setup():
    global __NOTIFIER
    assert __NOTIFIER is None
    global __STATSD_ADAPTED_NOTIFIER
    assert __STATSD_ADAPTED_NOTIFIER is None

    get_notifier()


def _get_messaging_notifier():
    global __NOTIFIER

    if not __NOTIFIER:
        service = cfg.CONF.notification_service
        host = cfg.CONF.default_publisher_id or socket.gethostname()
        publisher_id = '{}.{}'.format(service, host)
        __NOTIFIER = notify.Notifier(
            transport.get_transport(cfg.CONF),
            publisher_id,
            serializer=RequestContextSerializer(JsonPayloadSerializer())
        )

    return __NOTIFIER


def get_notifier():
    global __STATSD_ADAPTED_NOTIFIER

    if not __STATSD_ADAPTED_NOTIFIER:
        __STATSD_ADAPTED_NOTIFIER = (
            notifier_statsd_adapter.StatsdAdaptedNotifier(
                _get_messaging_notifier()))

    return __STATSD_ADAPTED_NOTIFIER


class JsonPayloadSerializer(serializer.NoOpSerializer):
    @staticmethod
    def serialize_entity(context, entity):
        return jsonutils.to_primitive(entity, convert_instances=True)


class RequestContextSerializer(serializer.Serializer):

    def __init__(self, base):
        self._base = base

    def serialize_entity(self, context, entity):
        if not self._base:
            return entity
        return self._base.serialize_entity(context, entity)

    def deserialize_entity(self, context, entity):
        if not self._base:
            return entity
        return self._base.deserialize_entity(context, entity)

    def serialize_context(self, context):
        return context.to_dict()

    def deserialize_context(self, context):
        return ctxt.RequestContext(**context)

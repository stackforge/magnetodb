# Copyright 2014 Mirantis Inc.
# Copyright 2014 Symantec Corporation
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

from magnetodb import storage
from magnetodb.api import validation
from magnetodb.openstack.common.log import logging
from magnetodb.storage import models

from magnetodb.api.openstack.v1 import parser
from magnetodb.api.openstack.v1 import utils
from magnetodb.common import timer
from magnetodb.storage.models import IndexedCondition

LOG = logging.getLogger(__name__)


class QueryController(object):
    """ Query for an items by primary or index key. """

    @timer.timer('api.query')
    def query(self, req, body, project_id, table_name):
        utils.check_project_id(req.context, project_id)
        with timer.Timer('query.jsonschema.validate'):
            validation.validate_object(body, "body")

        req.context.tenant = project_id


        # get attributes_to_get
        attributes_to_get = body.pop(parser.Props.ATTRIBUTES_TO_GET, None)
        if attributes_to_get:
            validation.validate_list(attributes_to_get,
                                     parser.Props.ATTRIBUTES_TO_GET)
            for attr_name in attributes_to_get:
                validation.validate_attr_name(attr_name)

        index_name = body.pop(parser.Props.INDEX_NAME, None)
        if index_name is not None:
            validation.validate_index_name(index_name)

        select = body.pop(parser.Props.SELECT, None)

        if select is None:
            if attributes_to_get:
                select = models.SelectType.SELECT_TYPE_SPECIFIC
            else:
                if index_name is not None:
                    select = models.SelectType.SELECT_TYPE_ALL_PROJECTED
                else:
                    select = models.SelectType.SELECT_TYPE_ALL

        select_type = models.SelectType(select, attributes_to_get)

        # parse exclusive_start_key_attributes
        exclusive_start_key_attributes = body.pop(
            parser.Props.EXCLUSIVE_START_KEY, None)

        if exclusive_start_key_attributes is not None:
            validation.validate_object(exclusive_start_key_attributes,
                                       parser.Props.EXCLUSIVE_START_KEY)
            exclusive_start_key_attributes = (
                parser.Parser.parse_item_attributes(
                    exclusive_start_key_attributes
                )
            )

        # parse indexed_condition_map
        key_conditions = body.pop(parser.Props.KEY_CONDITIONS, None)
        validation.validate_object(key_conditions, parser.Props.KEY_CONDITIONS)

        indexed_condition_map = parser.Parser.parse_attribute_conditions(
            key_conditions, condition_class=IndexedCondition
        )

        # TODO(dukhlov):
        # it would be nice to validate given table_name, key_attributes and
        # attributes_to_get to schema expectation

        consistent_read = body.pop(parser.Props.CONSISTENT_READ, False)
        validation.validate_boolean(consistent_read,
                                    parser.Props.CONSISTENT_READ)
        limit = body.pop(parser.Props.LIMIT, None)
        if limit is not None:
            validation.validate_integer(limit, parser.Props.LIMIT)

        scan_forward = body.pop(parser.Props.SCAN_INDEX_FORWARD, None)

        if scan_forward is not None:
            validation.validate_boolean(scan_forward,
                                        parser.Props.SCAN_INDEX_FORWARD)
            order_type = (
                models.ORDER_TYPE_ASC if scan_forward else
                models.ORDER_TYPE_DESC
            )
        else:
            order_type = None

        validation.validate_unexpected_props(body, "body")

        # select item
        with timer.Timer('api.query.storage.select_item'):
            result = storage.select_item(
                req.context, table_name, indexed_condition_map,
                select_type=select_type, index_name=index_name, limit=limit,
                consistent=consistent_read, order_type=order_type,
                exclusive_start_key=exclusive_start_key_attributes
            )

        # format response
        if select_type.type == models.SelectType.SELECT_TYPE_COUNT:
            response = {
                parser.Props.COUNT: result.count
            }
        else:
            response = {
                parser.Props.COUNT: result.count,
                parser.Props.ITEMS: [
                    parser.Parser.format_item_attributes(row)
                    for row in result.items
                ]
            }

        if limit == result.count:
            response[parser.Props.LAST_EVALUATED_KEY] = (
                parser.Parser.format_item_attributes(
                    result.last_evaluated_key)
            )

        return response

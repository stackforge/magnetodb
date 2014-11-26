# Copyright 2014 Mirantis Inc.
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

from magnetodb.api import validation
from magnetodb.api.openstack.v1 import parser
from magnetodb.api.openstack.v1 import utils
from magnetodb.common import probe


class ListRestoreJobsController(object):
    """ List restore jobs. """

    @probe.Probe(__name__)
    def list_restore_jobs(self, req, project_id, table_id):
        utils.check_project_id(req.context, project_id)
        req.context.tenant = project_id

        validation.validate_table_name(table_id)

        params = req.params.copy()

        # exclusive_start_restore_job_id = params.pop(
        #     parser.Props.EXCLUSIVE_START_RESTORE_JOB_ID, None)

        limit = params.pop(parser.Props.LIMIT, None)
        if limit:
            limit = validation.validate_integer(limit, parser.Props.LIMIT,
                                                min_val=0)

        restore_jobs = []
        response = {}

        if restore_jobs and str(limit) == str(len(restore_jobs)):
            response[
                parser.Props.LAST_EVALUATED_RESTORE_JOB_ID
            ] = restore_jobs[-1].id

        self_link_prefix = req.path_url

        response[parser.Props.RESTORE_JOBS] = [
            parser.Parser.format_restore_job(restore_job, self_link_prefix)
            for restore_job in restore_jobs
        ]

        return response
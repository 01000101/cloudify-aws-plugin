# Copyright (c) 2020 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
    EKSCluster
    ~~~~~~~~~~~~~~
    AWS EKS Cluster interface
"""

from __future__ import unicode_literals

# Boto

from botocore.exceptions import ClientError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.eks import EKSBase

RESOURCE_TYPE = 'EKS Cluster'
CLUSTERS = 'clusters'
CLUSTER = 'cluster'
CLUSTER_ARN = 'clusterArn'
CLUSTER_RESOURCE_NAME = 'clusterName'

IAM_ROLE_ARN = 'RoleArn'
IAM_ROLE_TYPE = 'cloudify.nodes.aws.iam.Role'


class EKSCluster(EKSBase):
    """
        EKSCluster interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EKSBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self.describe_cluster_filter = {}

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        try:
            resources = \
                self.client.describe_clusters(
                    **self.describe_cluster_filter
                )
        except ClientError:
            pass
        else:
            return None if not resources else resources.get(CLUSTERS)[0]

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props.get('status')

    def create(self, params):
        """Create a new AWS EKS cluster"""
        return self.make_client_call('create_cluster', params)

    def delete(self, params=None):
        """Deletes an existing AWS EKS cluster"""
        res = self.client.delete_cluster(
            **{CLUSTER: params.get(CLUSTER_RESOURCE_NAME)}
        )
        self.logger.debug('Response: {}'.format(res))
        return res


def prepare_describe_cluster_filter(params, iface):
    iface.describe_cluster_filter = {
        CLUSTERS: [params.get(CLUSTER_RESOURCE_NAME)],
    }
    return iface

def get_role_arn(ctx):
    target_node = utils.find_rel_by_node_type(
        ctx.instance,
        IAM_ROLE_TYPE)
    if target_node is None:
        raise NonRecoverableError(
            'Service must be connected to type {0}'.format(
                IAM_ROLE_TYPE))
    return target_node.target.instance.runtime_properties.get(
        EXTERNAL_RESOURCE_ID)

@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EKS Cluster"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EKSCluster, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EKS Cluster"""
    params = dict() if not resource_config else resource_config.copy()
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            params.get(CLUSTER_RESOURCE_NAME),
            use_instance_id=True
        )

    # Get the role ARN from either params or a relationship.
    role_arn = params.get(IAM_ROLE_ARN)
    if not role_arn:
        params[IAM_ROLE_ARN] = get_role_arn(ctx)

    utils.update_resource_id(ctx.instance, resource_id)
    iface = prepare_describe_cluster_filter(resource_config.copy(), iface)
    response = iface.create(params)
    if response and response.get(CLUSTER):
        resource_arn = response[CLUSTER].get(CLUSTER_ARN)
        utils.update_resource_arn(ctx.instance, resource_arn)


@decorators.aws_resource(EKSCluster, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EKS Cluster"""

    params = dict() if not resource_config else resource_config.copy()
    iface.delete(params)

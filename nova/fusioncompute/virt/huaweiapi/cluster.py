"""
    Management class for cluster-related functions.
"""
import json

from nova.fusioncompute.virt.huaweiapi import ops_task_base
from nova.openstack.common import jsonutils
from nova.openstack.common.gettextutils import _
from nova.fusioncompute.virt.huaweiapi import utils
from nova.fusioncompute.virt.huaweiapi import constant
from nova.fusioncompute.virt.huaweiapi.utils import LOG
from nova.fusioncompute.virt.huaweiapi import exception as fc_exc
from nova.fusioncompute.virt.huaweiapi.fcinstance import FC_INSTANCE_MANAGER as FC_MGR

UTC_TIME_TO_SEC = 1000

class ClusterOps(ops_task_base.OpsTaskBase):
    """
    cluster system manager and driver resouce info
    """
    def __init__(self, fc_client, task_ops):
        super(ClusterOps, self).__init__(fc_client, task_ops)
        self._stats = {}
        self.clusters = {}
        self.resources = []

    def init_all_cluster(self):
        """
        get all cluster info
        :return:
        """
        LOG.debug('self.site.cluster_uri:%s .' % self.site.cluster_uri)

        cfg_cluster_list = utils.split_strip(constant.CONF.fusioncompute.clusters)
        cluster_list = self.get(self.site.cluster_uri)['clusters']
        LOG.debug('clusters:%s, split:%s .' % (constant.CONF.fusioncompute.clusters,
                                               ','.join(cfg_cluster_list)))

        self.clusters = {}
        for cluster in cluster_list:
            if cluster['name'] in cfg_cluster_list:
                self.clusters[cluster['name']] = cluster

    def get_cluster_detail_by_nodename(self, nodename):
        """get cluster by node name"""
        cluster_urn = self.get_cluster_urn_by_nodename(nodename)
        return self.get(utils.generate_uri_from_urn(cluster_urn))

    def get_local_cluster_urn_list(self):
        """
        get local config cluster urn
        :return:
        """
        self.init_all_cluster()
        return [cluster['urn'] for cluster in self.clusters.values()]

    def get_cluster_urn_by_nodename(self, nodename):
        """get cluster urn by node name"""
        cluster_name = self.get_cluster_name_by_nodename(nodename)
        if cluster_name:
            self.init_all_cluster()
            if self.clusters.get(cluster_name):
                return self.clusters.get(cluster_name)['urn']
        return None

    def update_resources(self):
        """
        ini hypervisor info list
        :return:
        """
        self.resources = []
        self.init_all_cluster()
        for cluster_name in self.clusters:
            self.resources.append(self.create_nodename(cluster_name))

    def get_cluster_name_by_nodename(self, nodename):
        """get cluster name by node info"""
        if nodename:
            temps = nodename.split('@')
            if len(temps) != 2:
                return nodename
            else:
                return temps[1]
        else:
            return nodename

    def get_available_resource(self, nodename):
        """Retrieve resource info.

        This method is called when nova-compute launches, and
        as part of a periodic task.

        :returns: dictionary describing resources
        """
        LOG.debug(_("get_available_resource, nodename: %s ." % nodename))
        cluster_name = self.get_cluster_name_by_nodename(nodename)
        cluster_resource = self.get_cluster_resource(cluster_name)
        if not cluster_resource:
            LOG.error(_("Invalid cluster name : %s"), nodename)
            return {}

        cluster_resource['cpu_info'] = \
        jsonutils.dumps(cluster_resource['cpu_info'])
        cluster_resource['supported_instances'] = jsonutils.dumps(
            cluster_resource['supported_instances'])

        LOG.debug("the resource status is %s", cluster_resource)
        return cluster_resource

    def _query_host_by_scope(self, scope):
        """Query host info

        :param scope : clusterUrn , dvswitchUrn or datasotroeUrn
        :return a list of host in scope
        """
        host_uri = utils.build_uri_with_params(self.site.host_uri,
                                               {'scope':scope})
        return self.get(host_uri)['hosts']

    def _get_cluster_computeresource(self, cluster):
        computeres_uri = cluster["uri"] + "/" + "computeresource"
        return self.get(computeres_uri)

    def get_fc_current_time(self):
        current_time = self.get(self.site.current_time_uri)
        if current_time:
            utc_time = current_time["currentUtcTime"]
            utc_time_num_value = int(utc_time)/UTC_TIME_TO_SEC
            return utc_time_num_value
        return None

    def get_cpu_usage(self, monitor_period, cluster_urn):
        end_time = self.get_fc_current_time()
        start_time = end_time - (monitor_period*2)

        body = [
            {
                "startTime": str(start_time),
                "endTime": str(end_time),
                "interval": str(monitor_period),
                "metricId": "cpu_usage",
                "urn": cluster_urn
            }
        ]

        LOG.debug("get_cpu_usage body:%s", json.dumps(body))
        response = self.fc_client.post(self.site.metric_curvedata_uri,
                                       data=body)
        LOG.debug("get_cpu_usage body:%s response:%s",
                  json.dumps(body), json.dumps(response))
        if response:
            if len(response["items"]) > 0:
                metric_value = response["items"][0]["metricValue"]
                if len(metric_value) > 0:
                    value = metric_value[0]["value"]
                    if len(metric_value) is 2:
                        if metric_value[1]["value"] is not None:
                            value = metric_value[1]["value"]
                    return value
        return None

    def get_cluster_stats_by_name(self, cluster_name):
        """Get the aggregate resource stats of a cluster."""
        cpu_info = {'vcpus': 0, 'cores': 0, 'vendor': [], 'model': []}
        mem_info = {'total': 0, 'used': 0}
        mem_total = 0
        mem_used = 0
        cluster_urn = None
        cluster_query_info = {'name': cluster_name}
        cluster_query_uri = utils.build_uri_with_params(self.site.cluster_uri,
                                                        cluster_query_info)
        clusters = self.get(cluster_query_uri)['clusters']
        find_cluster = None
        if clusters:
            for cluster in clusters:
                if cluster['name'] == cluster_name:
                    find_cluster = cluster

        if find_cluster:
            cluster_urn = find_cluster['urn']
            hosts = self._query_host_by_scope(cluster_urn)
            for host in hosts:
                if host['status'] == 'normal' and (not host['isMaintaining']):
                    cpu_info['vcpus'] += host['cpuQuantity']
                    mem_total += host['memResource']['totalSizeMB']
                    mem_used += host['memResource']['allocatedSizeMB']
                    if 'vendor' in host:
                        cpu_info['vendor'].append(host['vendor'])
                    if 'model' in host:
                        cpu_info['model'].append(host['model'])

            mem_info['total'] = mem_total
            mem_info['used'] = mem_used
            computeresource = self._get_cluster_computeresource(find_cluster)
            cpuResource = computeresource["cpuResource"]
            cpu_info["totalSizeMHz"] = cpuResource.get("totalSizeMHz")
            cpu_info["allocatedSizeMHz"] = cpuResource.get("allocatedSizeMHz")
            cpu_info["allocatedVcpus"] = cpuResource.get("allocatedVcpus", 0)
            cpu_usage_monitor_period = \
                constant.CONF.fusioncompute.cpu_usage_monitor_period
            if cpu_usage_monitor_period not in [300, 1800, 3600, 86400]:
                cpu_usage_monitor_period = 3600
            cpu_info["usage"] = self.get_cpu_usage(cpu_usage_monitor_period,
                                                   cluster_urn)

            data = {'cpu': cpu_info, 'mem': mem_info}
            return cluster_urn, data
        else:
            LOG.warn(_("get cluster status failed, use default."))
            data = {'cpu': cpu_info, 'mem': mem_info}
            return cluster_urn, data

    def query_datastore_by_cluster_urn(self, cluster_urn):
        """Query """
        datastore_cond = {'status' : 'NORMAL', 'scope' : cluster_urn}
        datastore_uri = utils.build_uri_with_params(self.site.datastore_uri,
                                                    datastore_cond)
        return self.get(datastore_uri)['datastores']

    def get_hypervisor_type(self):
        """Returns the type of the hypervisor."""
        return constant.FC_DRIVER_JOINT_CFG['hypervisor_type']

    def get_hypervisor_version(self):
        """Get hypervisor version."""
        return constant.FC_DRIVER_JOINT_CFG['hypervisor_version']

    def create_nodename(self, cluster_name):
        """Creates the name that is stored in hypervisor_hostname column.

        The name will be of the form similar to
        site001_GlodCluster008
        """
        return '@'.join([self.site_id, cluster_name])

    def get_instance_capabilities(self):
        """get_instance_capabilities"""
        return [('i686', 'FusionCompute', 'xen'),
                ('x86_64', 'FusionCompute', 'xen')]

    def get_running_vms(self, cluster_urn):
        """
        return vm counts in this cluster
        :param cluster_urn:
        :return:
        """
        return FC_MGR.get_total_vm_numbers(scope=cluster_urn)

    def get_cluster_resource(self, cluster_name):
        """get the current state of the cluster."""
        res = {}
        cluster_urn, cluster_stats = \
        self.get_cluster_stats_by_name(cluster_name)

        disk_total = 0
        disk_available = 0

        datastores = self.query_datastore_by_cluster_urn(cluster_urn)
        for datastore in datastores:
            disk_total += datastore['actualCapacityGB']
            disk_available += datastore['actualFreeSizeGB']

        res["vcpus"] = int(cluster_stats['cpu']['vcpus']) \
                       * constant.CONF.fusioncompute.cpu_ratio
        res["memory_mb"] = cluster_stats['mem']['total']
        res["local_gb"] = disk_total
        res['vcpus_used'] = cluster_stats["cpu"]["allocatedVcpus"]
        res['memory_mb_used'] = cluster_stats['mem']['used']
        res['local_gb_used'] = disk_total - disk_available
        cpu_info = cluster_stats["cpu"]
        topology = {"cores": cpu_info['cores'],
                    "threads": cpu_info['vcpus']}
        extra_cpu_info = {
            "totalSizeMHz": str(cpu_info["totalSizeMHz"]),
            "allocatedSizeMHz": str(cpu_info["allocatedSizeMHz"]),
            "usage": str(cpu_info["usage"])
            }

        res["cpu_info"] = {"vendor": cpu_info['vendor'],
                           "model": cpu_info['model'],
                           "topology": topology,
                           "extra_info": extra_cpu_info}
        res["hypervisor_type"] = self.get_hypervisor_type()
        res["hypervisor_version"] = self.get_hypervisor_version()
        res["hypervisor_hostname"] = self.create_nodename(cluster_name)
        res["supported_instances"] = self.get_instance_capabilities()

        res['running_vms'] = self.get_running_vms(cluster_urn)

        return res

    def _modify_cluster(self, cluster, changes):
        """

        :param cluster: fc cluster
        :param changes: modify body {}
        :return:
        """

        self.put(cluster['uri'],
                 data=changes,
                 excp=fc_exc.ModifyClusterFailure)

    def _get_drs_rules_from_cluster(self, cluster, rule_name, rule_type):
        """

        :param cluster:
        :param rule_name:
        :param rule_type:
        :return:
        """
        drs_rules = cluster['drsSetting']['drsRules']
        for drs_rule in drs_rules:
            if drs_rule['ruleName'] == rule_name \
            and drs_rule['ruleType'] == rule_type:
                return drs_rule
        return None

    def create_drs_rules(self, cluster, rule_name, rule_type):
        """

        :param cluster:
        :param rule_name:
        :param rule_type:
        :return:
        """

        rule = self._get_drs_rules_from_cluster(cluster, rule_name, rule_type)
        if rule:
            LOG.debug(_("drs rules %s already exists"), rule_name)
            return

        body = {
            'drsSetting':{
                'drsRules':[{
                    'operationType': constant.DRS_RULES_OP_TYPE_MAP['create'],
                    'ruleName': rule_name,
                    'ruleType': rule_type
                    }]
            }
        }
        self._modify_cluster(cluster, body)
        LOG.debug(_("create drs rules %s succeed"), rule_name)

    def delete_drs_rules(self, cluster, rule_name, rule_type):
        """

        :param cluster:
        :param rule_name:
        :param rule_type:
        :return:
        """

        rule = self._get_drs_rules_from_cluster(cluster, rule_name, rule_type)
        if rule is None:
            LOG.debug(_("drs rules %s not exists"), rule_name)
            return

        body = {
            'drsSetting':{
                'drsRules':[{
                    'operationType': constant.DRS_RULES_OP_TYPE_MAP['delete'],
                    'ruleIndex': rule['ruleIndex']
                    }]
            }
        }
        self._modify_cluster(cluster, body)
        LOG.debug(_("delete drs rules %s succeed"), rule_name)

    def modify_drs_rules(self, cluster, rule_name, rule_type, vms):
        """

        :param cluster:
        :param rule_name:
        :param rule_type:
        :param vms:
        :return:
        """

        rule = self._get_drs_rules_from_cluster(cluster, rule_name, rule_type)
        if rule is None:
            msg = _("Can not find drs rules: name=%s, type=%d") % \
                  (rule_name, rule_type)
            raise fc_exc.AffinityGroupException(reason=msg)

        body = {
            'drsSetting':{
                'drsRules':[{
                    'operationType': constant.DRS_RULES_OP_TYPE_MAP['modify'],
                    'ruleIndex': rule['ruleIndex'],
                    'ruleName': rule_name,
                    'ruleType': rule_type,
                    'vms': vms
                    }]
            }
        }
        self._modify_cluster(cluster, body)
        LOG.debug(_("modify drs rules %s succeed"), rule_name)

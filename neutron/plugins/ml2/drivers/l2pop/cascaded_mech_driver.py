# Copyright (c) 2013 OpenStack Foundation.
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

from oslo.config import cfg

from neutron import manager
from neutron.common import constants as q_const
from neutron.common import constants as const
from neutron.common import exceptions
from neutron.common import utils
from neutron import context as n_context
from neutron.db import api as db_api
from neutron.openstack.common import log as logging
from neutron.plugins.common import constants as service_constants
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2.drivers.l2pop import config  # noqa
from neutron.plugins.ml2.drivers.l2pop import db as l2pop_db
from neutron.plugins.ml2.drivers.l2pop import rpc as l2pop_rpc

LOG = logging.getLogger(__name__)


class L2populationMechanismDriver(api.MechanismDriver,
                                  l2pop_db.L2populationDbMixin):

    def __init__(self):
        super(L2populationMechanismDriver, self).__init__()
        self.L2populationAgentNotify = l2pop_rpc.L2populationAgentNotifyAPI()

    def initialize(self):
        LOG.debug(_("Experimental L2 population driver"))
        self.rpc_ctx = n_context.get_admin_context_without_session()
        self.migrated_ports = {}
        self.remove_remote_ports_fdb = {}

    def _get_port_fdb_entries(self, port):
        return [[port['mac_address'],
                 ip['ip_address']] for ip in port['fixed_ips']]

    def _is_remote_port(self, port):
        return port['binding:profile'].get('port_key') == 'remote_port'

    def create_port_postcommit(self, context):
        """
        if port is "remote_port",
        then notify all l2-agent or only l2-gateway-agent
        else do nothing
        """
        port_context = context.current
        if(self._is_remote_port(port_context)):
            other_fdb_entries = self.get_remote_port_fdb(port_context)
            if(not other_fdb_entries):
                return
            if(cfg.CONF.l2pop.cascaded_gateway == 'no_gateway'):
                # notify all l2-agent
                self.L2populationAgentNotify.add_fdb_entries(self.rpc_ctx,
                                                             other_fdb_entries)
                rpc_context = context._plugin_context
                self.add_dvr_arp_rule(rpc_context, port_context.get('id'), 'add')
            else:
                # only notify  to l2-gateway-agent
                pass

    def add_dvr_arp_rule(self, context, port_id, action):
        l3plugin = manager.NeutronManager.get_service_plugins().get(
                        service_constants.L3_ROUTER_NAT)
        if (l3plugin and
                utils.is_extension_supported(l3plugin,
                                 q_const.L3_DISTRIBUTED_EXT_ALIAS)):
            try:
                l3plugin.dvr_remote_port_vmarp_table_update(context, port_id, action)
            except exceptions.PortNotFound:
                LOG.debug('Port %s not found during ARP update', port_id)

    def get_remote_port_fdb(self, port_context):
        port_id = port_context['id']
        network_id = port_context['network_id']

        session = db_api.get_session()
        segment = self.get_segment_by_network_id(session, network_id)
        if not segment:
            LOG.warning(_("Network %(network_id)s has no "
                          " vxlan provider, so cannot get segment"),
                        {'network_id': network_id})
            return
        ip = port_context['binding:profile'].get('host_ip')
        if not ip:
            LOG.debug(_("Unable to retrieve the ip from remote port, "
                        "check the remote port %(port_id)."),
                      {'port_id': port_id})
            return
        other_fdb_entries = {network_id:
                             {'segment_id': segment.segmentation_id,
                              'network_type': segment.network_type,
                              'ports': {ip: []}}}
        #ports = other_fdb_entries[network_id]['ports']

        #agent_ports = ports.get(ip, [const.FLOODING_ENTRY])

        #agent_ports += self._get_port_fdb_entries(port_context)
        #ports[ip] = agent_ports
        session = db_api.get_session()

        remote_ports = self.get_remote_ports(session, network_id)
        if not remote_ports:
            remote_ports = {}
        port_count = 0
        for binding in remote_ports:
            profile = binding['profile']
            remote_ip = self.get_host_ip_from_binding_profile_str(profile)
            if remote_ip and remote_ip == ip:
                port_count = port_count + 1

        if port_count == 1:
            # Agent is removing its last activated port in this network,
            # other agents needs to be notified to delete their flooding entry.
            other_fdb_entries[network_id]['ports'][ip].append(
                const.FLOODING_ENTRY)
        # Notify other agents to remove fdb rules for current port
        other_fdb_entries[network_id]['ports'][ip] += self._get_port_fdb_entries(port_context)

        return other_fdb_entries

    def delete_port_precommit(self, context):
        port = context.current
        if(self._is_remote_port(port)):
            fdb_entry = self.get_remote_port_fdb(port)
            self.remove_remote_ports_fdb[port['id']] = fdb_entry
            rpc_context = context._plugin_context
            self.add_dvr_arp_rule(rpc_context, port['id'] , 'del')

    def delete_port_postcommit(self, context):
        port = context.current
        agent_host = context.host

        remote_port_fdb = self.remove_remote_ports_fdb.pop(port['id'],None)
        LOG.debug(_("the remote port id is %s.") % port['id'])
        if(remote_port_fdb):
            self.L2populationAgentNotify.remove_fdb_entries(
                self.rpc_ctx, remote_port_fdb)
            LOG.debug(_("the remote port fdb_entries is %s.") % remote_port_fdb)
        else:
            fdb_entries = self._update_port_down(context, port, agent_host)
            self.L2populationAgentNotify.remove_fdb_entries(self.rpc_ctx,
                fdb_entries)

    def _get_diff_ips(self, orig, port):
        orig_ips = set([ip['ip_address'] for ip in orig['fixed_ips']])
        port_ips = set([ip['ip_address'] for ip in port['fixed_ips']])

        # check if an ip has been added or removed
        orig_chg_ips = orig_ips.difference(port_ips)
        port_chg_ips = port_ips.difference(orig_ips)

        if orig_chg_ips or port_chg_ips:
            return orig_chg_ips, port_chg_ips

    def _fixed_ips_changed(self, context, orig, port, diff_ips):
        orig_ips, port_ips = diff_ips

        if (port['device_owner'] == const.DEVICE_OWNER_DVR_INTERFACE):
            agent_host = context.host
        else:
            agent_host = context.original_host
        port_infos = self._get_port_infos(
            context, orig, agent_host)
        if not port_infos:
            return
        agent, agent_host, agent_ip, segment, port_fdb_entries = port_infos

        orig_mac_ip = [[port['mac_address'], ip] for ip in orig_ips]
        port_mac_ip = [[port['mac_address'], ip] for ip in port_ips]

        upd_fdb_entries = {port['network_id']: {agent_ip: {}}}

        ports = upd_fdb_entries[port['network_id']][agent_ip]
        if orig_mac_ip:
            ports['before'] = orig_mac_ip

        if port_mac_ip:
            ports['after'] = port_mac_ip

        self.L2populationAgentNotify.update_fdb_entries(
            self.rpc_ctx, {'chg_ip': upd_fdb_entries})

        return True

    def update_port_postcommit(self, context):
        port = context.current
        orig = context.original

        diff_ips = self._get_diff_ips(orig, port)
        if diff_ips:
            self._fixed_ips_changed(context, orig, port, diff_ips)
        if port['device_owner'] == const.DEVICE_OWNER_DVR_INTERFACE:
            if context.status == const.PORT_STATUS_ACTIVE:
                self._update_port_up(context)
            if context.status == const.PORT_STATUS_DOWN:
                agent_host = context.host
                fdb_entries = self._update_port_down(
                        context, port, agent_host)
                self.L2populationAgentNotify.remove_fdb_entries(
                    self.rpc_ctx, fdb_entries)
        elif (context.host != context.original_host
            and context.status == const.PORT_STATUS_ACTIVE
            and not self.migrated_ports.get(orig['id'])):
            # The port has been migrated. We have to store the original
            # binding to send appropriate fdb once the port will be set
            # on the destination host
            self.migrated_ports[orig['id']] = (
                (orig, context.original_host))
        elif context.status != context.original_status:
            if context.status == const.PORT_STATUS_ACTIVE:
                self._update_port_up(context)
            elif context.status == const.PORT_STATUS_DOWN:
                fdb_entries = self._update_port_down(
                    context, port, context.host)
                self.L2populationAgentNotify.remove_fdb_entries(
                    self.rpc_ctx, fdb_entries)
            elif context.status == const.PORT_STATUS_BUILD:
                orig = self.migrated_ports.pop(port['id'], None)
                if orig:
                    original_port = orig[0]
                    original_host = orig[1]
                    # this port has been migrated: remove its entries from fdb
                    fdb_entries = self._update_port_down(
                        context, original_port, original_host)
                    self.L2populationAgentNotify.remove_fdb_entries(
                        self.rpc_ctx, fdb_entries)

    def _get_port_infos(self, context, port, agent_host):
        if not agent_host:
            return

        session = db_api.get_session()
        agent = self.get_agent_by_host(session, agent_host)
        if not agent:
            return

        agent_ip = self.get_agent_ip(agent)
        if not agent_ip:
            LOG.warning(_("Unable to retrieve the agent ip, check the agent "
                          "configuration."))
            return

        segment = context.bound_segment
        if not segment:
            LOG.warning(_("Port %(port)s updated by agent %(agent)s "
                          "isn't bound to any segment"),
                        {'port': port['id'], 'agent': agent})
            return

        network_types = self.get_agent_l2pop_network_types(agent)
        if network_types is None:
            network_types = self.get_agent_tunnel_types(agent)
        if segment['network_type'] not in network_types:
            return

        fdb_entries = self._get_port_fdb_entries(port)

        return agent, agent_host, agent_ip, segment, fdb_entries

    def _update_port_up(self, context):
        port = context.current
        agent_host = context.host
        port_infos = self._get_port_infos(context, port, agent_host)
        if not port_infos:
            return
        agent, agent_host, agent_ip, segment, port_fdb_entries = port_infos

        network_id = port['network_id']

        session = db_api.get_session()
        agent_active_ports = self.get_agent_network_active_port_count(
            session, agent_host, network_id)

        other_fdb_entries = {network_id:
                             {'segment_id': segment['segmentation_id'],
                              'network_type': segment['network_type'],
                              'ports': {agent_ip: []}}}

        if agent_active_ports == 1 or (
                self.get_agent_uptime(agent) < cfg.CONF.l2pop.agent_boot_time):
            # First port activated on current agent in this network,
            # we have to provide it with the whole list of fdb entries
            agent_fdb_entries = {network_id:
                                 {'segment_id': segment['segmentation_id'],
                                  'network_type': segment['network_type'],
                                  'ports': {}}}
            ports = agent_fdb_entries[network_id]['ports']

            nondvr_network_ports = self.get_nondvr_network_ports(session,
                                                                 network_id)
            for network_port in nondvr_network_ports:
                binding, agent = network_port
                if agent.host == agent_host:
                    continue

                ip = self.get_agent_ip(agent)
                if not ip:
                    LOG.debug(_("Unable to retrieve the agent ip, check "
                                "the agent %(agent_host)s configuration."),
                              {'agent_host': agent.host})
                    continue

                agent_ports = ports.get(ip, [const.FLOODING_ENTRY])
                agent_ports += self._get_port_fdb_entries(binding.port)
                ports[ip] = agent_ports

            if cfg.CONF.l2pop.cascaded_gateway == 'no_gateway':
                remote_ports = self.get_remote_ports(session, network_id)
            else:
                remote_ports = {}
            for binding in remote_ports:
                profile = binding['profile']
                ip = self.get_host_ip_from_binding_profile_str(profile)
                if not ip:
                    LOG.debug(_("Unable to retrieve the agent ip, check "
                                "the agent %(agent_host)s configuration."),
                              {'agent_host': agent.host})
                    continue

                agent_ports = ports.get(ip, [const.FLOODING_ENTRY])
                agent_ports += self._get_port_fdb_entries(binding.port)
                ports[ip] = agent_ports
            dvr_network_ports = self.get_dvr_network_ports(session, network_id)
            for network_port in dvr_network_ports:
                binding, agent = network_port
                if agent.host == agent_host:
                    continue

                ip = self.get_agent_ip(agent)
                if not ip:
                    LOG.debug("Unable to retrieve the agent ip, check "
                              "the agent %(agent_host)s configuration.",
                              {'agent_host': agent.host})
                    continue

                agent_ports = ports.get(ip, [const.FLOODING_ENTRY])
                ports[ip] = agent_ports

            # And notify other agents to add flooding entry
            other_fdb_entries[network_id]['ports'][agent_ip].append(
                const.FLOODING_ENTRY)

            if ports.keys():
                self.L2populationAgentNotify.add_fdb_entries(
                    self.rpc_ctx, agent_fdb_entries, agent_host)

        # Notify other agents to add fdb rule for current port
        if port['device_owner'] != const.DEVICE_OWNER_DVR_INTERFACE:
            other_fdb_entries[network_id]['ports'][agent_ip] += (
                port_fdb_entries)

        self.L2populationAgentNotify.add_fdb_entries(self.rpc_ctx,
                                                     other_fdb_entries)

    def _update_port_down(self, context, port, agent_host):
        port_infos = self._get_port_infos(context, port, agent_host)
        if not port_infos:
            return
        agent, agent_host, agent_ip, segment, port_fdb_entries = port_infos

        network_id = port['network_id']

        session = db_api.get_session()
        agent_active_ports = self.get_agent_network_active_port_count(
            session, agent_host, network_id)

        other_fdb_entries = {network_id:
                             {'segment_id': segment['segmentation_id'],
                              'network_type': segment['network_type'],
                              'ports': {agent_ip: []}}}
        if agent_active_ports == 0:
            # Agent is removing its last activated port in this network,
            # other agents needs to be notified to delete their flooding entry.
            other_fdb_entries[network_id]['ports'][agent_ip].append(
                const.FLOODING_ENTRY)
        # Notify other agents to remove fdb rules for current port
        if port['device_owner'] != const.DEVICE_OWNER_DVR_INTERFACE:
            fdb_entries = port_fdb_entries
            other_fdb_entries[network_id]['ports'][agent_ip] += fdb_entries

        return other_fdb_entries

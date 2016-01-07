import socket
import traceback
import json
import random
import string

from nova.virt import driver
# from nova.virt.hws.reference_service import NovaService
from nova.openstack.common import jsonutils
from nova.compute import power_state
from nova import exception
from nova.openstack.common import loopingcall
from nova.openstack.common import log as logging

from nova.virt.hws.hws_service.client import HWSClient
from nova.virt.hws.database_manager import DatabaseManager
from oslo.config import cfg

LOG = logging.getLogger(__name__)

VIR_DOMAIN_NOSTATE = 0
VIR_DOMAIN_RUNNING = 1
VIR_DOMAIN_BLOCKED = 2
VIR_DOMAIN_PAUSED = 3
VIR_DOMAIN_SHUTDOWN = 4
VIR_DOMAIN_SHUTOFF = 5
VIR_DOMAIN_CRASHED = 6
VIR_DOMAIN_PMSUSPENDED = 7

LIBVIRT_POWER_STATE = {
    VIR_DOMAIN_NOSTATE: power_state.NOSTATE,
    VIR_DOMAIN_RUNNING: power_state.RUNNING,
    # NOTE(maoy): The DOMAIN_BLOCKED state is only valid in Xen.
    # It means that the VM is running and the vCPU is idle. So,
    # we map it to RUNNING
    VIR_DOMAIN_BLOCKED: power_state.RUNNING,
    VIR_DOMAIN_PAUSED: power_state.PAUSED,
    # NOTE(maoy): The libvirt API doc says that DOMAIN_SHUTDOWN
    # means the domain is being shut down. So technically the domain
    # is still running. SHUTOFF is the real powered off state.
    # But we will map both to SHUTDOWN anyway.
    # http://libvirt.org/html/libvirt-libvirt.html
    VIR_DOMAIN_SHUTDOWN: power_state.SHUTDOWN,
    VIR_DOMAIN_SHUTOFF: power_state.SHUTDOWN,
    VIR_DOMAIN_CRASHED: power_state.CRASHED,
    VIR_DOMAIN_PMSUSPENDED: power_state.SUSPENDED,
}

hws_opts = [
    cfg.StrOpt('project_id',
               help='project_id'),
    cfg.StrOpt('flavor_id',
               help='flavor id'),
    cfg.StrOpt('vpc_id',
               help='vpc_id'),
    cfg.StrOpt('subnet_id',
               help='subnet_id'),
    cfg.StrOpt('image_id',
               help='image_id'),
    cfg.StrOpt('gong_yao',
               help='gong yao'),
    cfg.StrOpt('si_yao',
               help='si yao')
    ]

CONF = cfg.CONF
hws_group = 'hws'
CONF.register_opts(hws_opts, hws_group)

class HwsComputeDriver(driver.ComputeDriver):

    def __init__(self, virtapi):
        super(HwsComputeDriver, self).__init__(virtapi)
        # self.nova_client = NovaService()
        gong_yao = CONF.hws.gong_yao
        si_yao = CONF.hws.si_yao
        region = "cn-north-1"
        protocol = "https"
        port = "443"
        self.hws_client = HWSClient(gong_yao, si_yao, region, protocol, port)
        self.db_manager = DatabaseManager()

    def _transfer_to_host_server_name(self, instance_uuid):
        """
        Transfer instance uuid to server name with format 'hws-server@<UUID>',
        This server name will be use server name in hws node.

        :param instance_uuid: e.g. '7c615d1c-07d3-4730-bf7a-ef7ad464c8fd'
        :return: e.g. 'hws-server@7c615d1c-07d3-4730-bf7a-ef7ad464c8fd'
        """
        return '@'.join(['hws-server', instance_uuid])

    def _transfer_to_uuid(self, server_name):
        """
        Use to transfer name of server in hws node to local instance uuid.

        :param server_name: e.g. 'hws-server@7c615d1c-07d3-4730-bf7a-ef7ad464c8fd'
        :return: 7c615d1c-07d3-4730-bf7a-ef7ad464c8fd
        """
        return server_name.split('@', 1)[1]

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        """Create a new instance/VM/domain on the virtualization platform.

        Once this successfully completes, the instance should be
        running (power_state.RUNNING).

        If this fails, any partial instance should be completely
        cleaned up, and the virtualization platform should be in the state
        that it was before this call began.

        :param context: security context
        :param instance: nova.objects.instance.Instance
                         This function should use the data there to guide
                         the creation of the new instance.
                         Instance(
                             access_ip_v4=None,
                             access_ip_v6=None,
                             architecture=None,
                             auto_disk_config=False,
                             availability_zone='az31.shenzhen--aws',
                             cell_name=None,
                             cleaned=False,
                             config_drive='',
                             created_at=2015-08-31T02:44:36Z,
                             default_ephemeral_device=None,
                             default_swap_device=None,
                             deleted=False,
                             deleted_at=None,
                             disable_terminate=False,
                             display_description='server@daa5e17c-cb2c-4014-9726-b77109380ca6',
                             display_name='server@daa5e17c-cb2c-4014-9726-b77109380ca6',
                             ephemeral_gb=0,
                             ephemeral_key_uuid=None,
                             fault=<?>,
                             host='42085B38-683D-7455-A6A3-52F35DF929E3',
                             hostname='serverdaa5e17c-cb2c-4014-9726-b77109380ca6',
                             id=49,
                             image_ref='6004b47b-d453-4695-81be-cd127e23f59e',
                             info_cache=InstanceInfoCache,
                             instance_type_id=2,
                             kernel_id='',
                             key_data=None,
                             key_name=None,
                             launch_index=0,
                             launched_at=None,
                             launched_on='42085B38-683D-7455-A6A3-52F35DF929E3',
                             locked=False,
                             locked_by=None,
                             memory_mb=512,
                             metadata={},
                             node='h',
                             numa_topology=None,
                             os_type=None,
                             pci_devices=<?>,
                             power_state=0,
                             progress=0,
                             project_id='52957ad92b2146a0a2e2b3279cdc2c5a',
                             ramdisk_id='',
                             reservation_id='r-d1dkde4x',
                             root_device_name='/dev/sda',
                             root_gb=1,
                             scheduled_at=None,
                             security_groups=SecurityGroupList,
                             shutdown_terminate=False,
                             system_metadata={
                                 image_base_image_ref='6004b47b-d453-4695-81be-cd127e23f59e',
                                 image_container_format='bare',
                                 image_disk_format='qcow2',
                                 image_min_disk='1',
                                 image_min_ram='0',
                                 instance_type_ephemeral_gb='0',
                                 instance_type_flavorid='1',
                                 instance_type_id='2',
                                 instance_type_memory_mb='512',
                                 instance_type_name='m1.tiny',
                                 instance_type_root_gb='1',
                                 instance_type_rxtx_factor='1.0',
                                 instance_type_swap='0',
                                 instance_type_vcpu_weight=None,
                                 instance_type_vcpus='1'
                                 },
                             task_state='spawning',
                             terminated_at=None,
                             updated_at=2015-08-31T02:44:38Z,
                             user_data=u'<SANITIZED>,
                             user_id='ea4393b196684c8ba907129181290e8d',
                             uuid=92d22a62-c364-4169-9795-e5a34b5f5968,
                             vcpus=1,
                             vm_mode=None,
                             vm_state='building')
        :param image_meta: image object returned by nova.image.glance that
                           defines the image from which to boot this instance
                           e.g.
                           {
                               u'status': u'active',
                               u'deleted': False,
                               u'container_format': u'bare',
                               u'min_ram': 0,
                               u'updated_at': u'2015-08-17T07:46:48.708903',
                               u'min_disk': 0,
                               u'owner': u'52957ad92b2146a0a2e2b3279cdc2c5a',
                               u'is_public': True,
                               u'deleted_at': None,
                               u'properties': {},
                               u'size': 338735104,
                               u'name': u'emall-backend',
                               u'checksum': u'0f2294c98c7d113f0eb26ad3e76c86fa',
                               u'created_at': u'2015-08-17T07:46:20.581706',
                               u'disk_format': u'qcow2',
                               u'id': u'6004b47b-d453-4695-81be-cd127e23f59e'
                            }
        :param injected_files: User files to inject into instance.
        :param admin_password: Administrator password to set in instance.
        :param network_info:
           :py:meth:`~nova.network.manager.NetworkManager.get_instance_nw_info`
        :param block_device_info: Information about block devices to be
                                  attached to the instance.
        """

        flavor = CONF.hws.flavor_id
        LOG.info('FLAVOR: %s' % flavor)
        image_id = CONF.hws.image_id
        vpc_id = CONF.hws.vpc_id
        subnet_id = CONF.hws.subnet_id
        subnet_id_list = [subnet_id]
        server_name = self._get_display_name(instance)
        # project_id = instance.project_id
        project_id = CONF.hws.project_id
        root_volume_type = "SATA"
        az = 'cn-north-1a'
        try:
            created_job = self.hws_client.ecs.create_server(project_id, image_id, flavor,
                                                            server_name, vpc_id, subnet_id_list, root_volume_type,
                                                            availability_zone=az)
            job_status = created_job["status"]

            if job_status != 200:
                job_info = json.dumps(created_job)
                error_info = 'HWS Create Server Error, EXCEPTION: %s' % created_job
                raise Exception(error_info)

        except Exception:
            raise exception.VirtualInterfaceCreateException(traceback.format_exc())

        job_id = created_job['body']['job_id']

        def _wait_for_boot():
            """Called at an interval until the VM is running."""
            job_current_info = self.hws_client.ecs.get_job_detail(project_id, job_id)
            if job_current_info and job_current_info['status'] == 200:
                job_status_ac = job_current_info['body']['status']
                if job_status_ac == 'SUCCESS':
                    server_id = job_current_info['body']['entities']['sub_jobs'][0]["entities"]['server_id']
                    LOG.info('Add hws server id: %s' % server_id)
                    if server_id:
                        LOG.info('HWS add server id mapping, cascading id: %s, cascaded id: %s' %
                                 (instance.uuid, server_id))
                        self.db_manager.add_server_id_mapping(instance.uuid, server_id)
                    else:
                        error_info = 'No server id found for cascading id: %s, server: %s' % (instance.uuid, server_name)
                        LOG.error(error_info)
                        raise Exception('HWS Create Server Error, EXCEPTION: %s' % error_info)
                    raise loopingcall.LoopingCallDone()
                elif job_status_ac == 'FAIL':
                    error_info = json.dumps(job_current_info)
                    LOG.error('HWS Create Server Error, EXCEPTION: %s' % error_info)
                    raise Exception(error_info)
                elif job_status_ac == "RUNNING":
                    LOG.debug('Job for creating server: %s is still RUNNING.' % server_name)
                    pass
                else:
                    raise Exception(job_current_info)
            elif job_current_info and job_current_info['status'] == 'error':
                try:
                    self._deal_java_error(job_current_info)
                except Exception, e:
                    pass
            elif not job_current_info:
                pass
            else:
                error_info = json.dumps(job_current_info)
                # log.error('HWS Create Server Error, EXCEPTION: %s' % error_info)
                raise Exception(error_info)

        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_boot)
        timer.start(interval=5).wait()

    def _get_display_name(self, instance):
        original_display_name = instance.display_name
        display_name = ""
        if len(original_display_name) < 64:
            display_name = original_display_name
        else:
            display_name = self._get_random_name(8)

        return display_name

    def _get_random_name(self, lenth):
        return ''.join(random.sample(string.ascii_letters + string.digits, lenth))

    def attach_volume(self, context, connection_info, instance, mountpoint,
                    disk_bus=None, device_type=None, encryption=None):
        pass

    def destroy(self, context, instance, network_info, block_device_info=None,
                destroy_disks=True, migrate_data=None):
        try:
            cascading_server_id = instance.uuid
            cascaded_server_id = self.db_manager.get_cascaded_server_id(cascading_server_id)
            if cascaded_server_id:
                project_id = CONF.hws.project_id
                cascaded_server_detail = self.hws_client.ecs.get_detail(project_id, cascaded_server_id)
                #{u'body': {u'itemNotFound': {u'message': u'Instance could not be found', u'code': 404}}, u'status': 404}
                if cascaded_server_detail['status'] == 404:
                    LOG.info('cascaded server is not exist in HWS, so return Delete Server SUCCESS.')
                    return

                delete_server_list = []
                delete_server_list.append(cascaded_server_id)
                delete_job_result = self.hws_client.ecs.delete_server(project_id, delete_server_list, True, True)
                self._deal_java_error(delete_job_result)
            else:
                # if there is no mapped cascaded server id, means there is no cascaded server
                # then we can directly return server deleted success.
                execute_info = "cascaded server is not exist for cascading id: , return delete success.%s" % cascading_server_id
                LOG.info(execute_info)

                return
        except Exception:
            raise exception.NovaException(traceback.format_exc())
        delete_job_id = delete_job_result['body']['job_id']

        def _wait_for_destroy():
            job_current_info = self.hws_client.ecs.get_job_detail(project_id, delete_job_id)
            if job_current_info and job_current_info['status'] == 200:
                job_status_ac = job_current_info['body']['status']
                if job_status_ac == 'SUCCESS':
                    self.db_manager.delet_server_id_by_cascading_id(cascading_server_id)
                    raise loopingcall.LoopingCallDone()
                elif job_status_ac == 'FAIL':
                    error_info = json.dumps(job_current_info)
                    LOG.error('HWS Delete Server Error, EXCEPTION: %s' % error_info)
                    raise Exception(error_info)
                elif job_status_ac == "RUNNING":
                    LOG.debug('Job for delete server: %s is still RUNNING.' % cascading_server_id)
                    pass
                else:
                    raise Exception(job_current_info)
            elif job_current_info and job_current_info['status'] == 'error':
                try:
                    self._deal_java_error(job_current_info)
                except Exception, e:
                    # if it is java gateway error, we will always wait for it success.
                    # it maybe network disconnect error or others issue.
                    LOG.info('Java gateway issue, go on to wait for deleting server success.')
                    pass
            elif not job_current_info:
                pass
            else:
                error_info = json.dumps(job_current_info)
                LOG.error('HWS Delete Server Error, EXCEPTION: %s' % error_info)
                raise Exception(error_info)

        timer = loopingcall.FixedIntervalLoopingCall(_wait_for_destroy)
        timer.start(interval=5).wait()


    def detach_volume(self, connection_info, instance, mountpoint,
                      encryption=None):
        """Detach the disk attached to the instance."""
        pass



    def get_available_nodes(self, refresh=False):
        """Returns nodenames of all nodes managed by the compute service.

        This method is for multi compute-nodes support. If a driver supports
        multi compute-nodes, this method returns a list of nodenames managed
        by the service. Otherwise, this method should return
        [hypervisor_hostname].
        """
        hostname = socket.gethostname()
        return [hostname]

    def _get_host_stats(self, hostname):
        return {
            'vcpus': 32,
            'vcpus_used': 0,
            'memory_mb': 164403,
            'memory_mb_used': 69005,
            'local_gb': 5585,
            'local_gb_used': 3479,
            'host_memory_total': 164403,
            'disk_total':50000,
            'host_memory_free': 164403,
            'disk_used': 0,
            'hypervisor_type':'hws',
            'hypervisor_version':'5005000',
            'hypervisor_hostname':hostname,
            'cpu_info':'{"model": ["Intel(R) Xeon(R) CPU E5-2670 0 @ 2.60GHz"],'
                       '"vendor": ["Huawei Technologies Co., Ltd."], '
                       '"topology": {"cores": 16, "threads": 32}}',
            'supported_instances':jsonutils.dumps([["i686", "ec2", "hvm"], ["x86_64", "ec2", "hvm"]]),
            'numa_topology': None,
        }

    def get_available_resource(self, nodename):

        host_stats = self._get_host_stats(nodename)

        return {'vcpus': host_stats['vcpus'],
               'memory_mb': host_stats['host_memory_total'],
               'local_gb': host_stats['disk_total'],
               'vcpus_used': 0,
               'memory_mb_used': host_stats['host_memory_total'] -
                                 host_stats['host_memory_free'],
               'local_gb_used': host_stats['disk_used'],
               'hypervisor_type': host_stats['hypervisor_type'],
               'hypervisor_version': host_stats['hypervisor_version'],
               'hypervisor_hostname': host_stats['hypervisor_hostname'],
               'cpu_info': jsonutils.dumps(host_stats['cpu_info']),
               'supported_instances': jsonutils.dumps(
                   host_stats['supported_instances']),
               'numa_topology': None,
               }

    def get_info(self, instance):
        # STATUS = power_state.NOSTATE
        #
        # try:
        #     server_name = self._transfer_to_host_server_name(instance.uuid)
        #     servers = self.nova_client.list(search_opts={'name':server_name})
        #
        #     if servers and len(servers) == 1:
        #         STATUS = servers[0]._info['OS-EXT-STS:power_state']
        # except Exception:
        #     msg = traceback.format_exc()
        #     raise exception.NovaException(msg)
        STATUS = 1
        return {'state': STATUS,
                'max_mem': 0,
                'mem': 0,
                'num_cpu': 1,
                'cpu_time': 0}

    def get_instance_macs(self, instance):
        """
        No need to implement.
        :param instance:
        :return:
        """
        pass

    def get_volume_connector(self, instance):
        pass

    def init_host(self, host):
        pass

    def list_instances(self):
        """List VM instances from all nodes."""
        instances = []
        project_id = CONF.hws.project_id
        list_result = self.hws_client.ecs.list(project_id)
        servers = list_result['body']['servers']
        for server in servers:
            server_id = server['id']
            instances.append(server_id)

        return instances

    def power_off(self, instance, timeout=0, retry_interval=0):
        project_id = CONF.hws.project_id
        cascaded_server_id = self._get_cascaded_server_id(instance)
        if cascaded_server_id:
            stop_result = self.hws_client.ecs.stop_server(project_id, cascaded_server_id)
            self._deal_java_error(stop_result)
            LOG.info('Stop Server: %s, result is: %s' % (instance.display_name, stop_result))
        else:
            error_info = 'cascaded server id is not exist for cascading server: %s.' % instance.display_name
            LOG.error(error_info)
            raise Exception(error_info)

    def power_on(self, context, instance, network_info,
                 block_device_info=None):
        project_id = CONF.hws.project_id
        cascaded_server_id = self._get_cascaded_server_id(instance)
        if cascaded_server_id:
            start_result = self.hws_client.ecs.start_server(project_id, cascaded_server_id)
            self._deal_java_error(start_result)
            LOG.info('Start Server: %s, result is: %s' % (instance.display_name, start_result))
        else:
            error_info = 'cascaded server id is not exist for cascading server: %s.' % instance.display_name
            LOG.error(error_info)
            raise Exception(error_info)

    def reboot(self, context, instance, network_info, reboot_type,
               block_device_info=None, bad_volumes_callback=None):
        project_id = CONF.hws.project_id
        cascaded_server_id = self._get_cascaded_server_id(instance)
        if cascaded_server_id:
            reboot_result = self.hws_client.ecs.reboot_hard(project_id, cascaded_server_id)
            self._deal_java_error(reboot_result)
            LOG.info('Start Server: %s, result is: %s' % (instance.display_name, reboot_result))
        else:
            error_info = 'cascaded server id is not exist for cascading server: %s.' % instance.display_name
            LOG.error(error_info)
            raise Exception(error_info)

    def resume_state_on_host_boot(self, context, instance, network_info,
                                  block_device_info=None):
        pass

    def snapshot(self, context, instance, image_id, update_task_state):
        pass

    def _get_cascaded_server_id(self, instance):
        cascading_server_id = instance.uuid
        cascaded_server_id = self.db_manager.get_cascaded_server_id(cascading_server_id)

        return cascaded_server_id

    def _deal_java_error(self, java_response):
        """
        {
          'status': 'error',
          'body': {
            'message': '<MESSAGE>',
            'exception': '<EXCEPTION>'
          }
        }
        :param java_response: dict
        :return:
        """
        if 'error' == java_response['status']:
            error_message = java_response['body']['message']
            exception = java_response['body']['exception']
            LOG.error('Java error message: %s, exception: %s' % (error_message, exception))
            raise Exception(exception)
        if 200 != java_response['status']:
            error_info = json.dumps(java_response)
            LOG.error(error_info)
            raise Exception(error_info)
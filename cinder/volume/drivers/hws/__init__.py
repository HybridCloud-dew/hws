__author__ = 'Administrator'
import json
import time

from cinder.volume import driver
from hwcloud.database_manager import DatabaseManager
from hwcloud.hws_service.client import HWSClient
from cinder.openstack.common import log as logging

from oslo.config import cfg

hws_opts = [cfg.StrOpt('project_id', help='project_id'),
            cfg.StrOpt('flavor_id', help='flavor id'),
            cfg.StrOpt('vpc_id', help='vpc_id'),
            cfg.StrOpt('subnet_id', help='subnet_id'),
            cfg.StrOpt('image_id', help='image_id'),
            cfg.StrOpt('gong_yao', help='gong yao'),
            cfg.StrOpt('si_yao', help='si yao'),
            cfg.StrOpt('service_region', help='region where resource to create in'),
            cfg.StrOpt('resource_region', help='region where resource to create in'),
            cfg.StrOpt('service_protocol', help='protocol', default='https'),
            cfg.StrOpt('service_port', help='port', default='443'),
            cfg.StrOpt('volume_type', help='default volume_typ', default='SATA')]

CONF = cfg.CONF
hws_group = 'hws'
CONF.register_opts(hws_opts, hws_group)

LOG = logging.getLogger(__name__)

SATA = 'SATA'
SSD = 'SSD'
SAS = 'SAS'
SUPPORT_VOLUME_TYPE = [SATA, SSD, SAS]

class HWSDriver(driver.VolumeDriver):
    VERSION = "1.0"

    def __init__(self, *args, **kwargs):
        super(HWSDriver, self).__init__( *args, **kwargs)
        gong_yao = CONF.hws.gong_yao
        si_yao = CONF.hws.si_yao
        region = CONF.hws.service_region
        protocol = CONF.hws.service_protocol
        port = CONF.hws.service_port
        self.hws_client = HWSClient(gong_yao, si_yao, region, protocol, port)
        self.db_manager = DatabaseManager()
        self.project_id = CONF.hws.project_id
        self.availability_zone = CONF.hws.resource_region
        self.volume_type_default = CONF.hws.volume_type

    def create_volume(self, volume):
        """Create a volume.


        """
        LOG.info('VOLUME: %s' % dir(volume))
        LOG.info('IMAGE ID: %s' % volume.get('image_id'))
        if not volume.get('image_id'):
            volume_name = volume.display_name
            project_id = self.project_id
            size = volume.size
            volume_type = self.volume_type_default

            job_info = self.hws_client.evs.create_volume(project_id, self.availability_zone,
                                                         size, volume_type, name=volume_name)
            self._deal_with_job(job_info, project_id, self._add_volume_mapping_to_db, volume)
        else:
            return {'provider_location': 'HWS CLOUD'}

    def copy_image_to_volume(self, context, volume, image_service, image_id):
        # Not to create volume when call cinder create volume API
        # Only when attache or dettach, or create server by volume, then create volume.
        if not image_id:
            volume_name = volume.display_name
            project_id = self.project_id
            size = volume.size
            volume_type = self.volume_type_default

            image_hws_id = self._get_cascaded_image_id(image_id)

            job_info = self.hws_client.evs.create_volume(project_id, self.availability_zone,
                                                         size, volume_type, name=volume_name, imageRef=image_hws_id)
            self._deal_with_job(job_info, project_id, self._add_volume_mapping_to_db, volume)

    def _get_volume_type(self, volume_type):
        if volume_type not in SUPPORT_VOLUME_TYPE:
            LOG.info('VOLUME TYPE: %s is not support in HWS Clouds, support type is: [%s]. Use SATA as default' %
                     (volume_type, SUPPORT_VOLUME_TYPE))
            volume_type = SATA

        return volume_type

    def _get_cascaded_image_id(self, cascading_image_id):
        cascaded_image_id = self.db_manager.get_cascaded_image_id(cascading_image_id)
        if not cascaded_image_id:
            LOG.error('No image mapping in HWS Cloud.')
            raise Exception('No image mapping in HWS Cloud.')

        return cascaded_image_id

    def _add_volume_mapping_to_db(self, job_detail_of_create_volume, volume):
        """

        :param job_detail_of_create_volume:
        :return:
        """
        hws_volume_id = job_detail_of_create_volume['body']['entities']['volume_id']
        volume_id = volume.id
        self.db_manager.add_volume_mapping(volume_id, hws_volume_id)
        LOG.info('Success to add volume mapping: {%s: %s}' % (volume_id, hws_volume_id))

    def _deal_with_job(self, job_info, project_id,
                       function_deal_with_success=None,
                       function_deal_with_fail=None,
                       object=None):
        if job_info['status'] == 200:
            job_id = job_info['body']['job_id']
            while True:
                time.sleep(5)
                job_detail_info = self.hws_client.evs.get_job_detail(project_id, job_id)
                if job_detail_info:
                    if job_detail_info['status'] == 200:
                        job_status = job_detail_info['body']['status']
                        if job_status == 'RUNNING':
                            LOG.debug('job<%s> is still RUNNING.' % job_id)
                            continue
                        elif job_status == 'FAIL':
                            if function_deal_with_fail:
                                function_deal_with_fail(job_detail_info, object)
                            error_info = 'job<%s> FAIL, ERROR INFO: %s' % (job_id, json.dumps(job_detail_info))
                            raise Exception(error_info)
                        elif job_status == 'SUCCESS':
                            if function_deal_with_success:
                                function_deal_with_success(job_detail_info, object)
                            success_info = 'job<%s> SUCCESS.' % job_id
                            LOG.info(success_info)
                            break
                    elif job_detail_info['status'] == 'error':
                        error_message = job_detail_info['body']['message']
                        exception = job_detail_info['body']['exception']
                        LOG.error('Java error message: %s, exception: %s' % (error_message, exception))
                        continue
                    else:
                        info = json.dumps(job_detail_info)
                        LOG.info('Job info get has some issue: %s, will retry to get again.' % info )
                        continue
                else:
                    retry_info = 'job detail info is empty, will retry to get. JOB DETAIL: %s' % job_detail_info
                    LOG.info(retry_info)
                    continue
        else:
            error_info = json.dumps(job_info)
            LOG.error('Job init FAIL, error info: %s' % error_info)
            raise Exception(error_info)

    def _deal_with_create_volume_fail(self, job_detail_info, volume):
        """
        deal with create volume fail.
        If hws volume is created, but fail, then save id mapping in db. then raise exception.
        if hws volume id is not created, raise exception directly.
        {
            "body": {
                "status": "FAIL",
                "entities": {
                    "volume_id": "1be7a768-59b6-4ef6-b4c0-a4f8039fa626"
                },
                "job_id": "8aace0c751b0a3bd01523529e4f70d35",
                "job_type": "createVolume",
                "begin_time": "2016-01-12T09:28:04.086Z",
                "end_time": "2016-01-12T09:28:32.252Z",
                "error_code": "EVS.2024",
                "fail_reason": "EbsCreateVolumeTask-fail:volume is error!"
            },
            "status": 200
        }
        :param job_detail_info:
        :param volume:
        :return:
        """
        job_id = job_detail_info.get('body').get('job_id')
        error_info = 'job<%s> FAIL, ERROR INFO: %s' % (job_id, json.dumps(job_detail_info))
        if job_detail_info.get('body').get('entities'):
            hws_volume_id = job_detail_info.get('body').get('entities').get('volume_id')
            if hws_volume_id:
                LOG.info('HWS volume is created, id is: %s' % hws_volume_id)
                volume_id = volume.id
                self.db_manager.add_volume_mapping(volume_id, hws_volume_id)
                LOG.debug('Success to add volume mapping: {%s: %s}' % (volume_id, hws_volume_id))
                raise Exception(error_info)

        raise Exception(error_info)

    def delete_volume(self, volume):
        cascading_volume_id = volume.id
        project_id = self.project_id
        cascaded_volume_id = self.db_manager.get_cascaded_volume_id(cascading_volume_id)
        LOG.info('VOLUME_ID: %s' % cascaded_volume_id)

        if cascaded_volume_id:
            volume_get = self.hws_client.evs.get_volume_detail(project_id, cascaded_volume_id)
            if volume_get['status'] == 200:
                job_info = self.hws_client.evs.delete_volume(project_id, cascaded_volume_id)
                self._deal_with_job(job_info,project_id, self._delete_volume_mapping, volume)
            elif volume_get['status'] == 404 and volume_get.get('body').get('itemNotFound'):
                LOG.info('cascaded volume is not exist, so directly return delete success')
                return
            else:
                error_info = 'Delete volume fail, Exception: %s' % json.dumps(volume_get)
                LOG.error(error_info)
                raise Exception(error_info)
        else:
            LOG.info('cascaded volume is not exist, so directly return delete success')
            return

    def _delete_volume_mapping(self, job_detail_info, volume):
        cascading_volume_id = volume.id
        self.db_manager.delete_volume_mapping(cascading_volume_id)
        LOG.info('Delete volume mapping for cascading volume id: %s' % cascading_volume_id)

    def get_volume_stats(self, refresh=False):
        """Get volume stats."""
        # pdb.set_trace()
        if not self._stats:
            backend_name = self.configuration.safe_get('volume_backend_name')
            LOG.debug('*******backend_name is %s' %backend_name)
            if not backend_name:
                backend_name = 'HC_HWS'
            data = {'volume_backend_name': backend_name,
                    'vendor_name': 'Huawei',
                    'driver_version': self.VERSION,
                    'storage_protocol': 'LSI Logic SCSI',
                    'reserved_percentage': 0,
                    'total_capacity_gb': 1000,
                    'free_capacity_gb': 1000}
            self._stats = data
        return self._stats

    def initialize_connection(self, volume, connector):
        """Allow connection to connector and return connection info."""
        LOG.debug('vCloud Driver: initialize_connection')

        driver_volume_type = 'hwclouds_volume'
        data = {}
        data['backend'] = 'hwclouds'
        data['volume_id'] = volume['id']
        data['display_name'] = volume['display_name']

        return {'driver_volume_type': driver_volume_type,
                 'data': data}

    def check_for_setup_error(self):
        """Check configuration file."""
        pass

    def create_cloned_volume(self, volume, src_vref):
        """Create a clone of the specified volume."""
        pass

    def create_export(self, context, volume):
        """Export the volume."""
        pass

    def create_snapshot(self, snapshot):
        pass

    def create_volume_from_snapshot(self, volume, snapshot):
        """Create a volume from a snapshot."""
        pass

    def delete_snapshot(self, snapshot):
        """Delete a snapshot."""
        pass

    def do_setup(self, context):
        """Instantiate common class and log in storage system."""
        pass

    def ensure_export(self, context, volume):
        """Synchronously recreate an export for a volume."""
        pass

    def extend_volume(self, volume, new_size):
        """Extend a volume."""
        pass

    def remove_export(self, context, volume):
        """Remove an export for a volume."""
        pass

    def terminate_connection(self, volume, connector, **kwargs):
        """Disallow connection from connector"""
        LOG.debug('vCloud Driver: terminate_connection')
        pass

    def validate_connector(self, connector):
        """Fail if connector doesn't contain all the data needed by driver."""
        LOG.debug('vCloud Driver: validate_connector')
        pass




__author__ = 'Administrator'

from nova.virt.hws.hws_service.ecs_service import ECSService
from nova.virt.hws.hws_service.evs_service import EVSService
from nova.virt.hws.hws_service.ims_service import IMSService
from nova.virt.hws.hws_service.vpc_service import VPCService

from oslo.config import cfg

hws_opts = [cfg.StrOpt('ecs_host', help='ecs_host'),
            cfg.StrOpt('evs_host', help='evs_host'),
            cfg.StrOpt('ims_host', help='ims_host'),
            cfg.StrOpt('vpc_host', help='vpc_host')
            ]
CONF = cfg.CONF
hws_group = 'hws'
CONF.register_opts(hws_opts, hws_group)

class HWSClient(object):
    def __init__(self, ak, sk, region, protocol, port):
        self.ak = ak
        self.sk = sk
        self.protocol = protocol
        self.port = port
        self.region = region

        self.ecs_host = CONF.hws.ecs_host
        self.evs_host = CONF.hws.evs_host
        self.ims_host = CONF.hws.ims_host
        self.vpc_host = CONF.hws.vpc_host

        self.ecs = ECSService(ak, sk, self.region, self.protocol, self.ecs_host, self.port)
        self.evs = EVSService(ak, sk, self.region, self.protocol, self.evs_host, self.port)
        self.ims = IMSService(ak, sk, self.region, self.protocol, self.ims_host, self.port)
        self.vpc = VPCService(ak, sk, self.region, self.protocol, self.vpc_host, self.port)

if __name__ == '__main__':
    ak = 'FAVX6E6CN0SSJT0QV4PC'
    sk = '9b3ULPelCtzF3UgwOaWar9ss4Wlge1Bc2r3obb0y'
    region = 'cn-north-1'
    protocol = 'https'
    port = '443'
    hws_client = HWSClient(ak, sk, region, protocol, port)
    project_id = '91d957f0b92d48f0b184c26975d2346e'
    server_id = '72194025-ce73-41a4-a6a4-9637cdf6a0b1'

    image_id = '37ca2b35-6fc7-47ab-93c7-900324809c5c'
    flavor_id = 'c1.medium'
    vpc_id = '742cef84-512c-43fb-a469-8e9e87e35459'
    subnet_id = '7bd9410f-38bb-4fbb-aa7a-cf4a22cb20f3'
    subnet_id_list = [subnet_id]
    root_volume_type = 'SATA'
    # my_server = hws_client.ecs.create_server(project_id, image_id,
    #                                      flavor_id, 'my_test_server_02', vpc_id,
    #                                      subnet_id_list, root_volume_type, availability_zone="cn-north-1a")
    # print my_server
    # job_id =  my_server['body']['job_id']
    #
    # job_id = '8aace0c851b0a3c10151f77f2b8443c9'
    # job_status = hws_client.ecs.get_job_detail(project_id,job_id)
    # print job_status

    # servers = hws_client.ecs.list(project_id)
    # print servers

    # server_id = '62ce1e0e-23bb-4c77-90db-491b43aa7a4e'
    # job_status = hws_client.ecs.stop_server(project_id, server_id)
    # print job_status
    # opts = {'name':'nash_server_01'}
    # servers = hws_client.ecs.get_detail(project_id, server_id)
    # print servers

    # job_statcs_ac = job_status['body']['status']
    # print job_status
    # print(job_statcs_ac == "SUCCESS")

    flavors = hws_client.ecs.list_flavors(project_id)
    print flavors
__author__ = 'Administrator'
from urlparse import urljoin

from nova.virt.hws.hws_service.ecs_service import ECSService
from nova.virt.hws.hws_service.evs_service import EVSService
from nova.virt.hws.hws_service.ims_service import IMSService
from nova.virt.hws.hws_service.vpc_service import VPCService
from nova.virt.hws.java_gateway import HWSRestMethod

class HWSClient(object):
    def __init__(self, ak, sk, region, protocol, port):
        self.ak = ak
        self.sk = sk
        self.protocol = protocol
        self.port = port
        self.region = region

        self.ecs_host = 'ecs.cn-north-1.myhwclouds.com.cn'
        self.evs_host = 'evs.cn-north-1.myhwclouds.com.cn'
        self.ims_host = 'ims.cn-north-1.myhwclouds.com.cn'
        self.vpc_host = 'vpc.cn-north-1.myhwclouds.com.cn'

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

    volume_name = 'test_v_1'
    volume_type = "SATA"
    size = 120
    availability_zone= 'cn-north-1a'

    # job_info = hws_client.evs.create_volume(project_id, availability_zone,
    #                                                  size, volume_type, name=volume_name)
    # print job_info
    #{u'body': {u'job_id': u'8aace0c651b0a02301521ab7e58660ca'}, u'status': 200}
    # job_id = job_info['body']['job_id']
    #
    job_id ='8aace0c651b0a02301521ae1f96c6138'
    job_status_info = hws_client.evs.get_job_detail(project_id, job_id)
    print(job_status_info)

    # volumes = hws_client.evs.list(project_id)
    # print volumes
    # hws_client.evs.delete_volume(project_id, '229306f7-e357-47f8-884a-eeb1fe6f131f')
    # volumes = hws_client.evs.list(project_id)
    # print volumes
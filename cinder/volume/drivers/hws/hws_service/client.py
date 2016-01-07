__author__ = 'Administrator'
from cinder.volume.drivers.hws.hws_service.ecs_service import ECSService
from cinder.volume.drivers.hws.hws_service.evs_service import EVSService
from cinder.volume.drivers.hws.hws_service.ims_service import IMSService
from cinder.volume.drivers.hws.hws_service.vpc_service import VPCService

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

    volumes = hws_client.evs.list(project_id)
    print volumes
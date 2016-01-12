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
__author__ = 'Administrator'
from cinder.volume.drivers.hws.hws_service.ecs_service import ECSService
from cinder.volume.drivers.hws.hws_service.evs_service import EVSService
from cinder.volume.drivers.hws.hws_service.ims_service import IMSService
from cinder.volume.drivers.hws.hws_service.vpc_service import VPCService
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
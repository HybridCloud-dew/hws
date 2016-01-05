__author__ = 'Administrator'

from nova.virt.hws.hws_service import HWSService

class EVSService(HWSService):
    def __init__(self, ak, sk, region, protocol, host, port):
        super(EVSService, self).__init__(ak, sk, 'EVS', region, protocol, host, port)

    def list(self):
        pass
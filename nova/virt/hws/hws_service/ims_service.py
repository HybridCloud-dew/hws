__author__ = 'Administrator'

import json

from nova.virt.hws.hws_service import HWSService


class IMSService(HWSService):
    def __init__(self, ak, sk, region, protocol, host, port):
        super(IMSService, self).__init__(ak, sk, 'IMS', region, protocol, host, port)

    def list(self, project_id):
        uri = '/v2/images'
        return json.loads(self.get(uri))
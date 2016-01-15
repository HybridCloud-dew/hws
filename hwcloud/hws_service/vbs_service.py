__author__ = 'Administrator'

import json

from hwcloud.hws_service import HWSService


class VBSService(HWSService):
    def __init__(self, ak, sk, region, protocol, host, port):
        super(VBSService, self).__init__(ak, sk, 'VPC', region, protocol, host, port)

    def create_backup(self, project_id, volume_id, name=None, description=None):
        uri = '/v2/%s/cloudbackups' % project_id
        request_body = {}
        backup = {}
        backup['volume_id'] = volume_id
        if name:
            backup['name'] = name
        if description:
            backup['description'] = description
        request_body['backup'] = backup
        request_body_string = json.dumps(request_body)
        response = self.post(uri, request_body_string)

        return json.loads(response)


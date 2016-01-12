__author__ = 'Administrator'

import json

from nova.virt.hws.hws_service import HWSService

class EVSService(HWSService):
    def __init__(self, ak, sk, region, protocol, host, port):
        super(EVSService, self).__init__(ak, sk, 'EVS', region, protocol, host, port)

    def list(self, project_id):
        uri = '/v2/%s/cloudvolumes' % project_id

        return self.get(uri)

    def create_volume(self, project_id, availability_zone, size, volume_type,
                      backup_id=None, description=None, name=None, imageRef=None, count=None):
        """
        {
            "volume": {
                "backup_id": null,
                "count": 1,
                "availability_zone": "az1.dc1",
                "description": "test_volume_1",
                "size": 120,
                "name": "test_volume_1",
                "imageRef": null,
                "volume_type": "SSD"
            }
        }
        :param project_id:
        :param availability_zone:
        :param size:
        :param volume_type:
        :param backup_id:
        :param description:
        :param name:
        :param imageRef:
        :param count:
        :return: dict
        {
            "job_id": "70a599e0-31e7-49b7-b260-868f441e862b",
        }
        or
        {
            "error": {
                "message": "XXXX",
                "code": "XXX"
            }
        }
        """
        uri = '/v2/%s/cloudvolumes' % project_id
        request_body_dict = {}
        volume = {}
        volume['availability_zone'] = availability_zone
        volume['size'] = size
        volume['volume_type'] = volume_type

        if backup_id:
            volume['backup_id'] = backup_id

        if description:
            volume['description'] = description

        if name:
            volume['name'] = name

        if imageRef:
            volume['imageRef'] = imageRef

        if count:
            volume['count'] = count

        request_body_dict['volume'] = volume
        request_body_string = json.dumps(request_body_dict)

        response = self.post(uri, request_body_string)

        return json.loads(response)

    def delete_volume(self, project_id, volume_id):
        """
        DELETE /v2/{tenant_id}/cloudvolumes/{volume_id}

        :return:
        """
        uri = '/v2/%s/cloudvolumes/%s' % (project_id, volume_id)
        response = self.delete(uri)

        return json.loads(response)

    def get_volume_detail(self, project_id, volume_id):
        uri = "/v2/%s/volumes/%s" % (project_id, volume_id)

        response = self.get(uri)

        return json.loads(response)
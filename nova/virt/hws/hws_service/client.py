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

if __name__ == "__main__":
    ak = 'XI9ATQZEY8E0BYVWZFCU'
    sk = "9WLbxZNSOHm9kVOO3aWuKYHjzcmeIDZ2QqndwD94"
    client = HWSClient(ak, sk, "cn-north-1", "https", "443")
    project_id = "91d957f0b92d48f0b184c26975d2346e"
    # server_id = '8b254fb9-fa69-4b12-bca8-ae91795d76a0'
    # server_detail = client.ecs.get_detail(project_id, server_id)
    # print(server_detail)
    # servers = client.ecs.list(project_id)
    # print servers
    # vpcs = client.vpc.list_vpc(project_id)
    # print vpcs
    # vpc_detail = client.vpc.list_vpc_detail(project_id, "742cef84-512c-43fb-a469-8e9e87e35459")
    # print vpc_detail
    # vpc_id = vpc_detail["body"]["vpc"]["id"]
    # print vpc_id
    # subnets = client.vpc.list_subnet(project_id, {'name':'subnet_04'})
    # print subnets
    # subnet_01 = "7bd9410f-38bb-4fbb-aa7a-cf4a22cb20f3"
    # subnet_01_detail = client.vpc.list_subnet_detail(project_id, subnet_01)
    # print subnet_01_detail


    # vpc_id = '742cef84-512c-43fb-a469-8e9e87e35459'
    # subnet_06 = client.vpc.create_subnet(project_id, 'subnet_06', "172.21.6.0/24",
    #                                      'cn-north-1a', vpc_id,
    #                                      "172.21.6.1", "true", "114.114.114.114", "114.114.115.115")
    # print subnet_06
    #
    # server_01 = client.ecs.create_server()

    # image_id = '37ca2b35-6fc7-47ab-93c7-900324809c5c'
    # flavor_id = 'c1.medium'
    # vpc_id = '742cef84-512c-43fb-a469-8e9e87e35459'
    # subnet_id = '7bd9410f-38bb-4fbb-aa7a-cf4a22cb20f3'
    # subnet_id_list = [subnet_id]
    # root_volume_type = 'SATA'
    # my_server = client.ecs.create_server(project_id, image_id,
    #                                      flavor_id, 'my_test_server_02', vpc_id,
    #                                      subnet_id_list, root_volume_type, availability_zone="cn-north-1a")
    # print my_server
    # job_id =  my_server['body']['job_id']

    # job_id = '8aace0c851b0a3c10151f77f2b8443c9'
    # job_status = client.ecs.get_job_detail(project_id,job_id)
    # job_statcs_ac = job_status['body']['status']
    # print job_status
    # print(job_statcs_ac == "SUCCESS")


    server_id = "e14c8ef2-3129-4c68-b83e-433f9ef04d9a"
    delete_server_list = []
    delete_server_list.append(server_id)
    result = client.ecs.delete_server(project_id, delete_server_list, False, False)
    print result

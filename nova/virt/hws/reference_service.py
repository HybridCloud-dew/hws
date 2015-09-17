import os

from nova.proxy import clients
from nova.proxy import compute_context

class RefService(object):

    def __init__(self, bypass_url=None):
        self.tenant = 'admin'
        self.user = 'cloud_admin'
        self.pwd = 'FusionSphere123'
        self.auth_url = 'https://identity.az41.hws--fusionsphere.huawei.com:443/identity/v2.0'
        self.bypass_url = bypass_url
        self.region_name = 'az41.hws--fusionsphere'

        self.credentials = self.get_credentials_v2()

    def get_credentials_v2(self):
        """
        d = {'version': '2', 'username' : os.environ['OS_USERNAME'], 'api_key' : os.environ['OS_PASSWORD'], 'auth_url' : os.environ['OS_AUTH_URL'], 'project_id' : os.environ['OS_TENANT_NAME']}
        :return:
        """

        d = {}
        d['version'] = '2'
        d['username'] = self.user
        d['password'] = self.pwd
        d['auth_url'] = self.auth_url
        d['tenant'] = self.tenant
        if self.region_name is not None:
            d['region_name'] = self.region_name
        else:
            d['region_name'] = None

        if self.bypass_url is not None:
            d['bypass_url'] = self.bypass_url
        else:
            d['bypass_url'] = None

        return d

class NovaService(RefService):

    def __init__(self):
        super(NovaService, self).__init__()
        self.nova = self.get_nova_sync_client(self.credentials)

    def get_nova_sync_client(self, kwargs):
        """
        kwargs = {
            'username': CONF.nova_admin_username,
            'password': CONF.nova_admin_password,
            'tenant': CONF.nova_admin_tenant_name,
            'auth_url': CONF.keystone_auth_url,
            'region_name': CONF.proxy_region_name
        }

        :param args:
        :return:
        """

        req_context = compute_context.RequestContext(**kwargs)
        openstack_clients = clients.OpenStackClients(req_context)
        return openstack_clients.nova()

    def create(self, name, image, flavor, meta=None, files=None,
               reservation_id=None, min_count=None,
               max_count=None, security_groups=None, userdata=None,
               key_name=None, availability_zone=None,
               block_device_mapping=None, block_device_mapping_v2=None,
               nics=None, scheduler_hints=None,
               config_drive=None, disk_config=None, **kwargs):
        return self.nova.servers.create(name, image, flavor, meta, files,
               reservation_id, min_count,
               max_count, security_groups, userdata,
               key_name, availability_zone,
               block_device_mapping, block_device_mapping_v2,
               nics, scheduler_hints,
               config_drive, disk_config, **kwargs)

    def list(self, detailed=True, search_opts=None, marker=None, limit=None):
        return self.nova.servers.list(detailed, search_opts, marker, limit)

    def delete(self, server):
        return self.nova.servers.delete(server)


# server_name = self._transfer_to_host_server_name(instance.uuid)
# server = self.nova_client.list(search_opts={'name': server_name})
# self.nova_client.delete(server)

# nova_service  = NovaService()
# servers = nova_service.list(search_opts={'name':'hws-server@d755bdac-1b27-4d10-8930-029c2cc0a5f4'})
#
# nova_service.delete(servers[0])

if __name__ == '__main__':
    nova_service  = NovaService()
    servers = nova_service.list(search_opts={'name':'hws-server@d755bdac-1b27-4d10-8930-029c2cc0a5f4'})
    print(servers[0].__dict__)


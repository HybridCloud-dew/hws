#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import ast
import commands
import re
import os

from nova import exception
from nova.openstack.common import jsonutils
from nova.pci import pci_utils

MAX_VENDOR_ID = 0xFFFF
MAX_PRODUCT_ID = 0xFFFF
MAX_FUNC = 0x7
MAX_DOMAIN = 0xFFFF
MAX_BUS = 0xFF
MAX_SLOT = 0x1F
ANY = '*'
VIRTFN_RE = re.compile("virtfn\d+")
SUPPORTED_VENDORS = ["15b3"]


def get_value(v):
    return ast.literal_eval("0x" + v)


def get_pci_dev_info(pci_obj, property, max, hex_value):
    a = getattr(pci_obj, property)
    if a == ANY:
        return
    v = get_value(a)
    if v > max:
        raise exception.PciConfigInvalidWhitelist(
            reason = "invalid %s %s" % (property, a))
    setattr(pci_obj, property, hex_value % v)


class PciAddress(object):
    """Manages the address fields of the whitelist.

    This class checks the address fields of the pci_passthrough_whitelist
    configuration option, validating the address fields.
    Example config are:

        | pci_passthrough_whitelist = {"address":"*:0a:00.*",
        |                         "physical_network":"physnet1"}
        | pci_passthrough_whitelist = {"address":":0a:00.",

    This function class will validate the address fields, check for wildcards,
    and insert wildcards where the field is left blank.
    """
    def __init__(self, pci_addr, is_physical_function):
        self.domain = ANY
        self.bus = ANY
        self.slot = ANY
        self.func = ANY
        self.is_physical_function = is_physical_function
        self._init_address_fields(pci_addr)

    def _check_physical_function(self):
        if ANY in (self.domain, self.bus, self.slot, self.func):
            return
        self.is_physical_function = pci_utils.is_physical_function(self)

    def _init_address_fields(self, pci_addr):
        if self.is_physical_function:
            (self.domain, self.bus, self.slot,
             self.func) = pci_utils.get_pci_address_fields(pci_addr)
            return
        dbs, sep, func = pci_addr.partition('.')
        if func:
            fstr = func.strip()
            if fstr != ANY:
                try:
                    f = get_value(fstr)
                except SyntaxError:
                    raise exception.PciDeviceWrongAddressFormat(
                        address=pci_addr)
                if f > MAX_FUNC:
                    raise exception.PciDeviceInvalidAddressField(
                        address=pci_addr, field="function")
                self.func = "%1x" % f
        if dbs:
            dbs_fields = dbs.split(':')
            if len(dbs_fields) > 3:
                raise exception.PciDeviceWrongAddressFormat(address=pci_addr)
            # If we got a partial address like ":00.", we need to to turn this
            # into a domain of ANY, a bus of ANY, and a slot of 00. This code
            # allows the address bus and/or domain to be left off
            dbs_all = [ANY for x in range(3 - len(dbs_fields))]
            dbs_all.extend(dbs_fields)
            dbs_checked = [s.strip() or ANY for s in dbs_all]
            self.domain, self.bus, self.slot = dbs_checked
            get_pci_dev_info(self, 'domain', MAX_DOMAIN, '%04x')
            get_pci_dev_info(self, 'bus', MAX_BUS, '%02x')
            get_pci_dev_info(self, 'slot', MAX_SLOT, '%02x')
            self._check_physical_function()

    def match(self, pci_addr, pci_phys_addr):
        # Assume this is called given pci_add and pci_phys_addr from libvirt,
        # no attempt is made to verify pci_addr is a VF of pci_phys_addr
        if self.is_physical_function:
            if not pci_phys_addr:
                return False
            domain, bus, slot, func = (
                pci_utils.get_pci_address_fields(pci_phys_addr))
            return (self.domain == domain and self.bus == bus and
                    self.slot == slot and self.func == func)
        else:
            domain, bus, slot, func = (
                pci_utils.get_pci_address_fields(pci_addr))
            conditions = [
                self.domain in (ANY, domain),
                self.bus in (ANY, bus),
                self.slot in (ANY, slot),
                self.func in (ANY, func)
            ]
            return all(conditions)


class PciDeviceSpec(object):
    def __init__(self, dev_spec):
        self.dev_spec = dev_spec
        self._init_dev_details()
        self.dev_count = 0

    def _init_dev_details(self):
        details = jsonutils.loads(self.dev_spec)
        self.vendor_id = details.pop("vendor_id", ANY)
        self.product_id = details.pop("product_id", ANY)
        self.address = details.pop("address", None)
        self.dev_name = details.pop("devname", None)

        self.vendor_id = self.vendor_id.strip()
        get_pci_dev_info(self, 'vendor_id', MAX_VENDOR_ID, '%04x')
        get_pci_dev_info(self, 'product_id', MAX_PRODUCT_ID, '%04x')

        pf = False
        if self.address and self.dev_name:
            raise exception.PciDeviceInvalidDeviceName()
        if not self.address:
            if self.dev_name:
                self.address, pf = pci_utils.get_function_by_ifname(
                    self.dev_name)
                if not self.address:
                    raise exception.PciDeviceNotFoundById(id=self.dev_name)
            else:
                self.address = "*:*:*.*"

        self.address = PciAddress(self.address, pf)
        self.tags = details
        if self.vendor_id == "*" and self.dev_name:
            self.vendor_id = self._get_vendor_id_by_interface(self.dev_name)
        self.valid_vf_address = self._get_valid_vf_address(self.dev_name)

    def _get_vendor_id_by_interface(self, interface):
        vendor_id = ""
        if interface:
            status, output = commands.getstatusoutput(
                "ethtool -i %s | grep bus-info" % interface)
            if not status:
                pf_address = output.split()[1]
                status, output2 = commands.getstatusoutput(
                    "lspci -n -s %s" % pf_address)
                if not status:
                    vendor_info = output2.split()[2]
                    vendor_id = vendor_info.split(':')[0]
        return vendor_id

    def _get_valid_vf_address(self, interface):
        vaild_vf_address = []
        vf_path = "/sys/class/net/%s/device" % interface
        if interface and self.vendor_id in SUPPORTED_VENDORS:
            status, output = commands.getstatusoutput(
                "ip link show %s | grep vf" % interface)
            if not status:
                result = output.split('\n')
                valid_vf_index = []
                for line in result:
                    if "65535" not in line:
                        valid_vf_index.append(line.split()[1])
                device = os.readlink(vf_path)
                pf = device.split('/')[3]
                pf_path = "/sys/bus/pci/devices/%s" % pf
                for id in valid_vf_index:
                    virtfn = pf_path + "/virtfn" + id
                    vaild_vf_address.append(os.readlink(virtfn).split('/')[1])
        return vaild_vf_address

    def match(self, dev_dict):
        conditions = [
            self.vendor_id in (ANY, dev_dict['vendor_id']),
            self.product_id in (ANY, dev_dict['product_id']),
            self.address.match(dev_dict['address'],
                dev_dict.get('phys_function')),
            ]
        if self.vendor_id in SUPPORTED_VENDORS:
            conditions.append(dev_dict['address'] in self.valid_vf_address)
        return all(conditions)

    def match_pci_obj(self, pci_obj):
        if pci_obj.extra_info:
            phy_func = pci_obj.extra_info.get('phys_function')
        else:
            phy_func = None
        return self.match({'vendor_id': pci_obj.vendor_id,
                            'product_id': pci_obj.product_id,
                            'address': pci_obj.address,
                            'phys_function': phy_func})

    def get_tags(self):
        return self.tags

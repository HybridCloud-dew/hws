# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013 OpenStack Foundation
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
#
# @author: Sean M. Collins, sean@coreitpro.com, Comcast #

import abc
import six


class SriovQoSDriver(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def delete_qos_for_device(self, device, pci_slot, **kwargs):
        pass
    
    @abc.abstractmethod
    def device_qos_updated(self, policy, device, pci_slot, **kwargs):
        pass
    
class NoOpSriovQoSDriver(SriovQoSDriver):

    def delete_qos_for_device(self, device, pci_slot, **kwargs):
        pass

    def device_qos_updated(self, policy, device, pci_slot, **kwargs):
        pass

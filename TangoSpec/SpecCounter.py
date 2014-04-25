#!/usr/bin/env python
# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
# This file is part of the Tango SPEC device server
#
# Copyright (c) 2014, European Synchrotron Radiation Facility.
# Distributed under the GNU Lesser General Public License.
# See LICENSE.txt for more info.
#------------------------------------------------------------------------------

"""A TANGO device server for SPEC based on SpecClient."""

from PyTango import Util, Attr, DevState, CmdArgType, AttrWriteType, DebugIt
from PyTango.server import Device, DeviceMeta, attribute, command, server_run
from PyTango.server import device_property
import TgGevent

from SpecClient_gevent.SpecCounter import SpecCounter as _SpecCounter
from SpecClient_gevent.SpecClientError import SpecClientError

class SpecCounter(Device):
    """A TANGO SPEC counter device based on SpecClient."""
    __metaclass__ = DeviceMeta

    SpecCounter = device_property(dtype=str, default_value="",
                                  doc="Name of spec session and counter e.g. host:spec:mon. "
                                      "(if running along with a Spec it can be just the counter name")

    Value = attribute(dtype=float, access=AttrWriteType.READ)

    @property
    def spec_counter(self):
        return self.__spec_counter

    def get_spec_version_name(self):
        return self.__spec_version_name

    def get_spec_counter_name(self):
        return self.__spec_counter_name
    
    @DebugIt()
    def delete_device(self):
        Device.delete_device(self)
        self.__spec_counter = None
        
    @DebugIt()
    def init_device(self):
        Device.init_device(self)

        self.set_change_event("State", True, True)
        self.set_change_event("Status", True, False)
        #self.set_change_event("Value", True, False)

        self.set_state(DevState.INIT)
        self.set_status("Pending connection to " + self.SpecCounter)
        
        self.__spec_counter = None
        self.__spec_counter_name = None
        self.__spec_version_name = None        
        
        try:
            host, session, counter = self.SpecCounter.split(":")
            spec_version = "%s:%s" % (host, session)
        except ValueError:
            util = Util.instance()
            tango_specs = util.get_device_list_by_class("Spec")
            if not tango_specs:
                status = "Wrong SpecCounter property: Not inside a Spec. " \
                         "Need the full SpecCounter"
                self.set_state(DevState.FAULT)
                self.set_status(status)
                self.error_stream(status)
                return
            elif len(tango_specs) > 1:
                status = "Wrong SpecCounter property: More than one Spec " \
                         "in tango server. Need the full SpecCounter"                
                self.set_state(DevState.FAULT)
                self.set_status(status)
                self.error_stream(status)
                return
            else:
                spec_version = tango_specs[0].get_spec().specVersion
                counter = self.SpecCounter

        self.__spec_version_name = spec_version
        self.__spec_counter_name = counter
        
        try:
            self.__spec_counter = TgGevent.get_proxy(_SpecCounter,
                                                     counter,
                                                     spec_version)
            msg = "Connected to counter " + self.SpecCounter
            self.set_state(DevState.ON)
            self.set_status(msg)
            self.info_stream(msg)
        except SpecClientError as spec_error:
            status = "Error connecting to Spec counter: %s" % str(spec_error)
            self.set_state(DevState.FAULT)
            self.set_status(status)
            self.error_stream(status)

    def read_Value(self):
        return self.spec_counter.get_value()

    @command(dtype_in=float, doc_in="count time (s)")
    def Count(self, count_time):
        self.spec_counter.count(count_time)

        
def main():
    server_run((SpecCounter,), verbose=True)

if __name__ == '__main__':
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

#---------------------------------------------------------------------
# This file is part of the Tango SPEC device server
#
# Copyright (c) 2014, European Synchrotron Radiation Facility.
# Distributed under the GNU Lesser General Public License.
# See LICENSE.txt for more info.
#---------------------------------------------------------------------

"""A TANGO counter device for SPEC based on SpecClient."""

import time
import logging

from PyTango import DevState, AttrWriteType, AttrQuality, DebugIt
from PyTango.server import (Device, DeviceMeta, attribute, command,
                            device_property)

from SpecClient_gevent.SpecCounter import SpecCounterA
from SpecClient_gevent.SpecClientError import SpecClientError

from TangoSpec.SpecCommon import (SpecCounterState_2_TangoState,
                                  SpecCounterType_2_str,
                                  switch_state, find_spec_name)


class SpecCounter(Device):
    """A TANGO SPEC counter device based on SpecClient."""
    __metaclass__ = DeviceMeta

    SpecCounter = device_property(dtype=str, default_value="",
                                  doc="Name of spec session and "
                                      "counter e.g. host:spec:mon. "
                                      "(if running along with a Spec "
                                      "it can be just the counter "
                                      "name")

    Value = attribute(dtype=float, access=AttrWriteType.READ)

    @property
    def spec_counter(self):
        return self.__spec_counter

    def get_spec_version_name(self):
        return self.__spec_version_name

    def get_spec_counter_name(self):
        return self.__spec_counter_name

    get_spec_name = get_spec_counter_name

    @DebugIt()
    def delete_device(self):
        Device.delete_device(self)
        self.__spec_counter = None

    @DebugIt()
    def init_device(self):
        self.__log = logging.getLogger(self.get_name())
        Device.init_device(self)
        self.set_change_event("State", True, True)
        self.set_change_event("Status", True, True)
        self.set_change_event("Value", True, False)

        switch_state(self, DevState.INIT,
                     "Pending connection to " + self.SpecCounter)

        self.__spec_counter = None
        self.__spec_counter_name = None
        self.__spec_version_name = None

        spec_info = find_spec_name(self, self.SpecCounter)
        if spec_info is None:
            return
        spec_version, counter = spec_info
        self.__spec_version_name = spec_version
        self.__spec_counter_name = counter

        cb = dict(connected=self.__counterConnected,
                  disconnected=self.__counterDisconnected,
                  counterValueChanged=self.__counterValueChanged,
                  counterStateChanged=self.__counterStateChanged)
        try:
            self.__log.debug("Start creating Spec counter %s", counter)
            self.__spec_counter = SpecCounterA(callbacks=cb)
        except SpecClientError as spec_error:
            status = "Error creating Spec counter {0}".format(counter)
            switch_state(self, DevState.FAULT, status)
        else:
            self.__counterConnect()
        self.__log.debug("End creating Spec counter %s", counter)

    def __getTypeStr(self):
        sc = self.__spec_counter
        if sc:
            ctype = SpecCounterType_2_str[sc.getType()]
        else:
            ctype = 'Unknown'
        return ctype

    def __counterConnect(self):
        counter = self.__spec_counter_name
        try:
            self.__spec_counter.connectToSpec(counter,
                                              self.__spec_version_name,
                                              timeout=.25)
        except SpecClientError as spec_error:
            status = "Error connecting to Spec counter {0}".format(counter)
            switch_state(self, DevState.FAULT, status)

    def __counterConnected(self):
        state = DevState.ON
        if self.get_state() != state:
            ctype = self.__getTypeStr()
            status = "Counter is now {0} ({1})".format(state, ctype)
            switch_state(self, state, status)

    def __counterDisconnected(self):
        state = DevState.OFF
        if self.get_state() != state:
            status = "Counter is now %s".format(state)
            switch_state(self, state, status)

    def __counterStateChanged(self, spec_state):
        old_state = self.get_state()
        state = SpecCounterState_2_TangoState[spec_state]
        ctype = self.__getTypeStr()
        status = "Counter is now {0} ({1})".format(state, ctype)
        # switch tango state and status attributes and send events
        switch_state(self, state, status)

        sc = self.__spec_counter
        if sc:
            # Fire a value event with VALID quality
            if old_state != DevState.RUNNING and state == DevState.RUNNING:
                value = sc.getValue()
                self.push_change_event("Value", value, time.time(),
                                       AttrQuality.ATTR_CHANGING)
            elif old_state == DevState.RUNNING and state != DevState.RUNNING:
                value = sc.getValue()
                self.push_change_event("Value", value)


    def __counterValueChanged(self, value):
        if self.get_state() == DevState.RUNNING:
            self.push_change_event("Value", value, time.time(),
                                   AttrQuality.ATTR_CHANGING)
        else:
            self.push_change_event("Value", value)

    def read_Value(self):
        return self.spec_counter.getValue()

    @command(dtype_in=float, doc_in="count time (s)")
    def Count(self, count_time):
        """
        Count by the specified time (s)

        :param count_time: count time (s)
        """
        self.spec_counter.count(count_time)

    @command
    def Stop(self):
        """
        Stop counting
        """
        self.spec_counter.stop()

    @command(dtype_in=bool, doc_in="enabled (True/False)")
    def setEnabled(self, enabled):
        """
        Enable/Disable counter

        :param enabled: enable or disable
        :type enabled: bool
        """
        self.spec_counter.setEnabled(enabled)

def main():
    from PyTango.server import run
    run((SpecCounter,), verbose=True)

if __name__ == '__main__':
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

#---------------------------------------------------------------------
# This file is part of the Tango SPEC device server
#
# Copyright (c) 2014, European Synchrotron Radiation Facility.
# Distributed under the GNU Lesser General Public License.
# See LICENSE.txt for more info.
#---------------------------------------------------------------------

"""A TANGO device server for SPEC based on SpecClient."""

import time
import logging

from PyTango import DevState, CmdArgType
from PyTango import AttrWriteType, AttrQuality
from PyTango import DebugIt
from PyTango.server import Device, DeviceMeta, attribute, command
from PyTango.server import device_property

from SpecClient_gevent.SpecCounter import SpecCounterA
from SpecClient_gevent.SpecClientError import SpecClientError

from TangoSpec.TgGevent import get_proxy
from TangoSpec.SpecCommon import SpecCounterState_2_TangoState
from TangoSpec.SpecCommon import SpecCounterType_2_str
from TangoSpec.SpecCommon import execute, switch_state, get_spec_names


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

    @DebugIt()
    def delete_device(self):
        Device.delete_device(self)
        self.__spec_counter = None

    @DebugIt()
    def init_device(self):
        self.__log = logging.getLogger(self.get_name())
        Device.init_device(self)
        self.set_change_event("State", True, True)
        self.set_change_event("Status", True, False)
        self.set_change_event("Value", True, False)

        switch_state(self, DevState.INIT,
                     "Pending connection to " + self.SpecCounter)

        self.__spec_counter = None
        self.__spec_counter_name = None
        self.__spec_version_name = None

        try:
            host, session, counter = self.SpecCounter.split(":")
            spec_version = "%s:%s" % (host, session)
        except ValueError:
            specs = get_spec_names()
            if not specs:
                status = "Wrong SpecCounter property: Not inside a " \
                         "Spec. Need the full SpecCounter name"
                switch_state(self, DevState.FAULT, status)
                return
            elif len(specs) > 1:
                status = "Wrong SpecCounter property: More than " \
                         "one Spec in tango server. Need the full " \
                         "SpecCounter name"
                switch_state(self, DevState.FAULT, status)
                return
            else:
                spec_version = specs[0]
                counter = self.SpecCounter

        self.__spec_version_name = spec_version
        self.__spec_counter_name = counter

        cb = dict(connected=self.__counterConnected,
                  disconnected=self.__counterDisconnected,
                  counterValueChanged=self.__counterValueChanged,
                  counterStateChanged=self.__counterStateChanged)
        try:
            self.__log.debug("Start creating Spec counter %s", counter)
            self.__spec_counter = get_proxy(SpecCounterA, callbacks=cb)
            self.__spec_counter.connectToSpec(counter, spec_version)
            self.__log.debug("End creating Spec counter %s", counter)
        except SpecClientError as spec_error:
            status = "Error connecting to Spec counter: {0}".format(spec_error)
            switch_state(self, DevState.FAULT, status)

    def __getTypeStr(self):
        sc = self.__spec_counter
        if sc:
            ctype = SpecCounterType_2_str[sc.getType()]
        else:
            ctype = 'Unknown'
        return ctype

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
                execute(self.push_change_event, "Value", value,
                        time.time(), AttrQuality.ATTR_CHANGING)
            elif old_state == DevState.RUNNING and state != DevState.RUNNING:
                value = sc.getValue()
                execute(self.push_change_event, "Value", value)


    def __counterValueChanged(self, value):
        if self.get_state() == DevState.RUNNING:
            execute(self.push_change_event, "Value", value,
                    time.time(), AttrQuality.ATTR_CHANGING)
        else:
            execute(self.push_change_event, "Value", value)

    def read_Value(self):
        return self.spec_counter.getValue()

    @command(dtype_in=float, doc_in="count time (s)")
    def Count(self, count_time):
        self.spec_counter.count(count_time)

    @command
    def Stop(self):
        self.spec_counter.stop()

    @command(dtype_in=bool, doc_in="enabled (True/False)")
    def setEnabled(self, enabled):
        self.spec_counter.setEnabled(enabled)

def main():
    from PyTango.server import run
    run((SpecCounter,), verbose=True)

if __name__ == '__main__':
    main()

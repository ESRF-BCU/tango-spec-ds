#!/usr/bin/env python
# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
# This file is part of the Tango SPEC device server
#
# Copyright (c) 2014, European Synchrotron Radiation Facility.
# Distributed under the GNU Lesser General Public License.
# See LICENSE.txt for more info.
#------------------------------------------------------------------------------

"""A TANGO motor device for SPEC based on SpecClient."""

import time
from functools import partial

from PyTango import Util, DevState, DispLevel, AttrWriteType, AttrQuality
from PyTango import MultiAttrProp
from PyTango import DebugIt
from PyTango.server import Device, DeviceMeta, attribute, command, server_run
from PyTango.server import device_property

from SpecClient_gevent.SpecMotor import SpecMotorA
from SpecClient_gevent.SpecClientError import SpecClientError

from . import TgGevent
from .SpecCommon import SpecState_2_TangoState, execute, switch_state

#: read-write scalar float attribute helper
float_rw_mem_attr = partial(attribute, dtype=float, memorized=True,
                            access=AttrWriteType.READ_WRITE)

                            
class SpecMotor(Device):
    """A TANGO SPEC motor device based on SpecClient."""
    __metaclass__ = DeviceMeta

    SpecMotor = device_property(dtype=str, default_value="",
                                doc="Name of spec session and motor e.g. host:spec:m0. "
                                    "(if running along with a Spec it can be just the motor name")

    Position = float_rw_mem_attr(doc="motor position")

    DialPosition = attribute(dtype=float, access=AttrWriteType.READ,
                             doc="motor dial position",
                             display_level=DispLevel.EXPERT)

    Sign = attribute(dtype=int, access=AttrWriteType.READ_WRITE,
                     display_level=DispLevel.EXPERT, doc="motor sign")

    Offset = float_rw_mem_attr(display_level=DispLevel.EXPERT, doc="motor offset")

    AccelerationTime = float_rw_mem_attr(unit="s", display_level=DispLevel.EXPERT,
                                         doc="motor acceleration time")

    Backlash = float_rw_mem_attr(display_level=DispLevel.EXPERT,
                                 doc="motor backlash")

    #TODO: steps_per_unit,

    StepSize = float_rw_mem_attr(hw_memorized=True,
                                 doc="motor step size (used by StepDown and StepUp)")

    Limit_Switches = attribute(dtype=(bool,), access=AttrWriteType.READ,
                               max_dim_x=3, display_level=DispLevel.EXPERT,
                               doc="limit switches (home, upper, lower)")

    @property
    def spec_motor(self):
        return self.__spec_motor

    def get_spec_version_name(self):
        return self.__spec_version_name

    def get_spec_motor_name(self):
        return self.__spec_motor_name
    
    @DebugIt()
    def delete_device(self):
        Device.delete_device(self)
        self.__spec_motor = None        
        
    @DebugIt()
    def init_device(self):
        Device.init_device(self)
        self.set_change_event("State", True, True)
        self.set_change_event("Status", True, False)
        self.set_change_event("Position", True, False)

        switch_state(self, DevState.INIT, "Pending connection to " + self.SpecMotor)
        
        self.__spec_motor = None
        self.__spec_motor_name = None
        self.__spec_version_name = None
        self.__step_size = 1
        
        try:
            host, session, motor = self.SpecMotor.split(":")
            spec_version = "%s:%s" % (host, session)
        except ValueError:
            util = Util.instance()
            tango_specs = util.get_device_list_by_class("Spec")
            if not tango_specs:
                status = "Wrong SpecMotor property: Not inside a Spec. " \
                         "Need the full SpecMotor"
                switch_state(self, DevState.FAULT, status)
                return
            elif len(tango_specs) > 1:
                status = "Wrong SpecMotor property: More than one Spec " \
                         "in tango server. Need the full SpecMotor"
                switch_state(self, DevState.FAULT, status)
                return
            else:
                spec_version = tango_specs[0].Spec
                motor = self.SpecMotor

        self.__spec_version_name = spec_version
        self.__spec_motor_name = motor

        try:
            cb=dict(connected=self.__motorConnected,
                    disconnected=self.__motorDisconnected,
                    motorPositionChanged=self.__motorPositionChanged,
                    motorStateChanged=self.__motorStateChanged,
                    motorLimitsChanged=self.__updateLimits)
            self.__spec_motor = TgGevent.get_proxy(SpecMotorA, motor,
                                                   spec_version, callbacks=cb)
        except SpecClientError as spec_error:
            status = "Error connecting to Spec motor: %s" % str(spec_error)
            switch_state(self, DevState.FAULT, status)

    def always_executed_hook(self):
        pass

    def __motorConnected(self):
        switch_state(self, DevState.ON, "Connected to motor " + self.SpecMotor)

    def __motorDisconnected(self):
        switch_state(self, DevState.OFF, "motor disconnected")

    def __motorPositionChanged(self, position):
        state = self.get_state()
        if state == DevState.MOVING:
            execute(self.push_change_event, "Position", position, time.time(),
                    AttrQuality.ATTR_CHANGING)
        else:
            execute(self.push_change_event, "Position", position)

    def __motorStateChanged(self, spec_state):
        old_state = self.get_state()
        state = SpecState_2_TangoState[spec_state]

        # Fire a position event with VALID quality
        if old_state == DevState.MOVING and state != DevState.MOVING:
            position = self.__spec_motor.getPosition()
            execute(self.push_change_event, "Position", position)

        # switch tango state and status attributes and send events
        switch_state(self, state, "Motor is now %s" % (str(state),))


    @DebugIt()
    def __updateLimits(self):
        if not self.__spec_motor:
            return
        limits = self.__spec_motor.getLimits()
        multi_prop = MultiAttrProp()
        multi_prop = self.Position.get_properties(multi_prop)
        multi_prop.min_value = str(limits[0])
        multi_prop.max_value = str(limits[1])
        self.Position.set_properties(multi_prop)
        
    def read_Position(self):
        position = self.__spec_motor.getPosition()
        state = self.get_state()
        if state == DevState.MOVING:
            return position, time.time(), AttrQuality.ATTR_CHANGING
        return position
    
    def write_Position(self, position):
        self.__spec_motor.move(position)

    def read_DialPosition(self):
        return self.__spec_motor.getDialPosition()

    def read_Sign(self):
        return self.__spec_motor.getSign()

    def write_Sign(self, sign):
        self.__spec_motor.setSign(sign)
    
    def read_Offset(self):
        return self.__spec_motor.getOffset()

    def write_Offset(self, offset):
        self.__spec_motor.setOffset(offset)

    def read_AccelerationTime(self):
        return self.__spec_motor.getParameter("acceleration")

    @DebugIt()
    def write_AccelerationTime(self, acceleration_time):
        self.__spec_motor.setParameter("acceleration", acceleration_time)

    def read_Backlash(self):
        return self.__spec_motor.getParameter("backlash")

    @DebugIt()
    def write_Backlash(self, backlash):
        self.__spec_motor.setParameter("backlash", backlash)
                
    def read_StepSize(self):
        return self.__step_size

    @DebugIt()
    def write_StepSize(self, step_size):
        self.__step_size = step_size

    def read_Limit_Switches(self):
        m = self.__spec_motor
        return False, m.getParameter('high_lim_hit'), m.getParameter('low_lim_hit')
        
    @command
    def Stop(self):
        self.__spec_motor.stop()

    @command
    def Abort(self):
        self.__spec_motor.stop()

    @command(dtype_in=float)
    def Move(self, abs_position):
        self.__spec_motor.move(abs_position)

    @command(dtype_in=float)
    def MoveRelative(self, rel_position):
        self.__spec_motor.moveRelative(rel_position)

    @command
    def StepUp(self):
        self.__spec_motor.moveRelative(self.__step_size)

    @command
    def StepDown(self):
        self.__spec_motor.moveRelative(-self.__step_size)


def main():
    server_run((SpecMotor,), verbose=True)

if __name__ == '__main__':
    main()

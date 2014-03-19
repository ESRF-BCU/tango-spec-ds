# -*- coding: utf-8 -*-
#!/usr/bin/env python

#------------------------------------------------------------------------------
# This file is part of the Tango SPEC device server
#
# Copyright (c) 2014, European Synchrotron Radiation Facility.
# Distributed under the GNU Lesser General Public License.
# See LICENSE.txt for more info.
#------------------------------------------------------------------------------

"""A TANGO device server for SPEC based on SpecClient."""

from functools import partial

from PyTango import Util, DevState, AttrWriteType, DebugIt
from PyTango import MultiAttrProp
from PyTango.server import Device, DeviceMeta, attribute, command, server_run
from PyTango.server import device_property
import TgGevent

from SpecClient_gevent import SpecMotor
from SpecClient_gevent.SpecClientError import SpecClientError
    
_SS_2_TS = {
    SpecMotor.NOTINITIALIZED: DevState.UNKNOWN,
    SpecMotor.UNUSABLE: DevState.UNKNOWN,
    SpecMotor.READY: DevState.ON,
    SpecMotor.MOVESTARTED: DevState.MOVING,
    SpecMotor.MOVING: DevState.MOVING,
    SpecMotor.ONLIMIT: DevState.ALARM,
}

#: read-write scalar float attribute helper
float_rw_mem_attr = partial(attribute, dtype=float, memorized=True,
                            access=AttrWriteType.READ_WRITE)

                            
class TangoSpecMotor(Device):
    """A TANGO SPEC motor device based on SpecClient."""
    __metaclass__ = DeviceMeta

    SpecMotor = device_property(dtype=str, default_value="",
                                doc="Name of spec session and motor e.g. host:spec:m0. "
                                    "(if running along with a TangoSpec it can be just the motor name")

    Position = float_rw_mem_attr(doc="motor position")

    DialPosition = attribute(dtype=float, access=AttrWriteType.READ,
                             doc="motor dial position")

    Sign = attribute(dtype=int, access=AttrWriteType.READ_WRITE,
                     doc="motor sign")

    Offset = float_rw_mem_attr(doc="motor offset")

    AccelerationTime = float_rw_mem_attr(unit="s", doc="motor acceleration time")

    Backlash = float_rw_mem_attr(doc="motor backlash")

    #TODO: steps_per_unit,

    StepSize = float_rw_mem_attr(hw_memorized=True,
                                 doc="motor step size (used by StepDown and StepUp")

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

        self.set_state(DevState.INIT)
        self.set_status("Pending connection to " + self.SpecMotor)
        
        self.__spec_motor = None
        self.__spec_motor_name = None
        self.__spec_version_name = None
        self.__step_size = 1
        
        try:
            host, session, motor = self.SpecMotor.split(":")
            spec_version = "%s:%s" % (host, session)
        except ValueError:
            util = Util.instance()
            tango_specs = util.get_device_list_by_class("TangoSpec")
            if not tango_specs:
                status = "Wrong SpecMotor property: Not inside a TangoSpec. " \
                         "Need the full SpecMotor"
                self.set_state(DevState.FAULT)
                self.set_status(status)
                self.error_stream(status)
                return
            elif len(tango_specs) > 1:
                status = "Wrong SpecMotor property: More than one TangoSpec " \
                         "in tango server. Need the full SpecMotor"
                self.set_state(DevState.FAULT)
                self.set_status(status)
                self.error_stream(status)
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
            self.__spec_motor = TgGevent.get_proxy(SpecMotor.SpecMotorA,
                                                   motor, spec_version,
                                                   callbacks=cb)
            # getting the limits triggers the limitsChanged callback.
            # interesting...
            #self.__spec_motor.getLimits()
        except SpecClientError as spec_error:
            status = "Error connecting to Spec motor: %s" % str(spec_error)
            self.set_state(DevState.FAULT)
            self.set_status(status)
            self.error_stream(status)

    def always_executed_hook(self):
        pass

    def __motorConnected(self):
        msg = "Connected to motor " + self.SpecMotor
        self.info_stream(msg)
        self.set_state(DevState.ON)
        self.set_status(msg)

    def __motorDisconnected(self):
        self.info_stream("motor disconnected")

    def __motorPositionChanged(self, position):
        self.debug_stream("motor position changed %s", position)        
        self.push_change_event("Position", position)

    def __motorStateChanged(self, spec_state):
        state = _SS_2_TS[spec_state]
        self.info_stream("motor state changed %s", state)
        self.set_state(state)
        self.set_status("Motor is now %s" % (str(state,)))
        self.push_change_event("State", state)

    @DebugIt()
    def __updateLimits(self, limits=None):
        if not self.__spec_motor:
            return
        limits = limits or self.__spec_motor.getLimits()
        pos_attr = self.get_device_attr().get_attr_by_name("Position")
        multi_prop = MultiAttrProp()
        multi_prop = pos_attr.get_properties(multi_prop)
        multi_prop.min_value = str(limits[0])
        multi_prop.max_value = str(limits[1])
        pos_attr.set_properties(multi_prop)
        
    def read_Position(self):
        return self.__spec_motor.getPosition()

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
    server_run((TangoSpecMotor,), verbose=True)

if __name__ == '__main__':
    main()

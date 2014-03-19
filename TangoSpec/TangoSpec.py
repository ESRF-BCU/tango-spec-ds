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

import json
import numbers
from functools import partial

from PyTango import Util, Attr, DevState, CmdArgType, AttrWriteType, DebugIt
from PyTango.server import Device, DeviceMeta, attribute, command, server_run
from PyTango.server import device_property
import TgGevent

from SpecClient_gevent import Spec
from SpecClient_gevent import SpecCommand
from SpecClient_gevent import SpecVariable
from SpecClient_gevent import SpecEventsDispatcher
from SpecClient_gevent.SpecClientError import SpecClientError

#: read-only spectrum string attribute helper
str_1D_attr = partial(attribute, dtype=[str], access=AttrWriteType.READ,
                      max_dim_x=512)

#TODO:
# 1 - tests!
# 2 - execute long command without timeout
# 3 - read list of available counters from spec (SpecCounterList attribute)

class TangoSpec(Device):
    """A TANGO device server for SPEC based on SpecClient."""
    __metaclass__ = DeviceMeta

    Spec = device_property(dtype=str, default_value="localhost:spec",
                           doc="SPEC session e.g. localhost:spec")

    Motors = device_property(dtype=[str], default_value=[],
                             doc="List of registered SPEC motors to create e.g. tth, energy, phi")

    Counters = device_property(dtype=[str], default_value=[],
                               doc="List of registered SPEC counters to create e.g. mon, det, i0")

    Variables = device_property(dtype=[str], default_value=[],
                                doc="List registered SPEC variables to create e.g. myvar, mayarr, A")

    SpecMotorList = str_1D_attr(doc="List of all SPEC motors")

    MotorList = str_1D_attr(doc="List of tango motors from SPEC")
    
    SpecCounterList = str_1D_attr(doc="List of all SPEC counters")

    CounterList = str_1D_attr(doc="List of tango counters from SPEC")

    VariableList = str_1D_attr(doc="List of SPEC variables")
    
    Output = attribute(dtype=str, access=AttrWriteType.READ)

    def update_output(self, output):
        if isinstance(output, numbers.Number):
            text = "{0:12}".format(output)
        else:
            text = str(output)
        # it seems we can't push event while server
        # is executing a command
        self.push_change_event("Output", text)

    def get_spec(self):
        return self.__spec
        
    @DebugIt()
    def delete_device(self):
        Device.delete_device(self)
        self.__spec_mgr = None
        self.__spec = None
        self.__spec_tty = None
        self.__variables = None        

    @DebugIt()
    def init_device(self):
        Device.init_device(self)
        self.set_change_event("State", True, True)
        self.set_change_event("Status", True, False)
        self.set_change_event("Output", True, False)
        self.set_state(DevState.INIT)
        self.set_status("Initializing spec " + self.Spec)

        spec_name = self.Spec
        self.__spec_mgr = None
        self.__spec = None
        self.__spec_tty = None
        self.__variables = dict()
        self.__executing_commands = dict()
        
        try:
            spec_host, spec_session = spec_name.split(":")
            self.debug_stream("Using spec '%s'", spec_name)
        except ValueError:
            status = "Invalid spec '%s'. Must be in format " \
                     "<host>:<spec session>" % (spec_name,)
            self.set_state(DevState.FAULT)
            self.set_status(status)
            self.error_stream(status)
            return

        # Create asynchronous spec access to get the data
        try:
            self.__spec = TgGevent.get_proxy(Spec.Spec,
                                             spec_name,
                                             timeout=1000)
            self.__spec_tty = TgGevent.get_proxy(SpecVariable.SpecVariableA,
                                                 "output/tty", spec_name,
                                                 prefix=False,
                                                 dispatchMode=SpecEventsDispatcher.FIREEVENT,
                                                 callbacks={"update" : self.update_output})
            self.set_state(DevState.ON)
            self.set_status("Connected to spec " + spec_name)
        except SpecClientError as spec_error:
            status = "Error connecting to Spec: %s" % str(spec_error)
            self.set_state(DevState.FAULT)
            self.set_status(status)                
            self.error_stream(status)
            return

        for variable in self.Variables:
            try:
                self.__addVariable(variable)
            except SpecClientError as spec_error:
                msg = "Error adding variable '%s': %s" % (variable,
                                                          str(spec_error))
                self.set_state(DevState.FAULT)
                self.set_status(self.get_status + "\n" + msg)
                self.error_stream(msg)

    @DebugIt()
    def read_SpecMotorList(self):
        return self.__spec.getMotorsMne()

    @DebugIt()
    def read_MotorList(self):
        util = Util.instance()
        motors = util.get_device_list_by_class("TangoSpecMotor")
        return ["{0} ({1})".format(m.SpecMotor, m.get_name()) for m in motors]

    @DebugIt()
    def read_SpecCounterList(self):
        #TODO
        return ()

    @DebugIt()
    def read_CounterList(self):
        util = Util.instance()
        counters = util.get_device_list_by_class("TangoSpecCounter")
        return ["{0} ({1})".format(c.SpecCounter, c.get_name()) for c in counters]
                
    @DebugIt()
    def read_VariableList(self):
        return sorted(self.__variables)

    @DebugIt()
    def read_Output(self):
        return ""

    @DebugIt()
    def read_Variable(self, attr):
        v_name = attr.get_name()
        self.debug_stream("read variable '%s'", v_name)
        value = self.__variables[v_name][0].getValue()
        attr.set_value(json.dumps(value))

    @DebugIt()
    def write_Variable(self, attr):
        v_name, value = attr.get_name(), attr.get_write_value()
        value = json.loads(value)
        self.info_stream("set %s = %s" % (v_name, value))
        self.__variables[v_name][0].setValue(value)

    # -------------------------------------------------------------------------
    # Tango Commands
    # -------------------------------------------------------------------------

    def _execute_cmd(self, cmd, wait=True):
        try:
            spec_cmd = TgGevent.get_proxy(SpecCommand.SpecCommand, None, self.Spec)
        except SpecClientError, error:
            self.error_stream("Spec %s error : %s"%(self.Spec, error))

        if wait:
            return str(spec_cmd.executeCommand(cmd))
        else:
            spec_cmd.executeCommand(cmd, wait=False)
            self.__executing_commands[id(spec_cmd)]=spec_cmd
            return id(spec_cmd)
        
    @command(dtype_in=str, dtype_out=str)
    def ExecuteCmd(self, command):
        return self._execute_cmd(command)

    @command(dtype_in=str, dtype_out=int)
    def ExecuteCmdA(self, command):
        return self._execute_cmd(command, wait=False)    

    @command(dtype_in=int, dtype_out=str)
    def GetReply(self, cmd_id):
        spec_cmd = self.__executing_commands[cmd_id]
        del self.__executing_commands[cmd_id]
        reply = spec_cmd.waitReply()
        if reply.error:
            raise RuntimeError(reply.error)
        else:
            return str(reply.data)

    @command(dtype_in=int, dtype_out=bool)
    def IsReplyArrived(self, cmd_id):
        if not cmd_id in self.__executing_commands:
            return True
        spec_cmd = self.__executing_commands[cmd_id]
        return spec_cmd.isReplyArrived()

    @command(dtype_in=str, doc_in="spec variable name")
    def AddVariable(self, variable):
        if variable in self.__variables:
            raise Exception("Variable '%s' is already defined as an attribute!" %
                            (variable,))

        try:
            self.__addVariable(variable)
        except SpecClientError as error:
            self.error_stream("Error adding variable '%s': %s",
                              variable, str(error))
            raise
            
        # update property in the database
        util = Util.instance()
        db = util.get_database()
        db.put_device_property(self.get_name(),
                               {"Variables" : sorted(self.__variables)})

    @command(dtype_in=str, doc_in="spec variable name")
    def RemoveVariable(self, variable):
        if variable not in self.__variables:
            raise Exception("Variable '%s' is not defined as an attribute!" %
                            (variable,))

        del self.__variables[variable]

        # update property in the database
        util = Util.instance()
        db = util.get_database()
        db.put_device_property(self.get_name(),
                               {"Variables" : sorted(self.__variables)})

        self.remove_attribute(variable)
        
    @command(dtype_in=[str], doc_in="spec motor name [, tango motor device name]")
    def AddMotor(self, motor_info):
        util = Util.instance()

        motor_name = motor_info[0]
        if len(motor_info) > 1:
            dev_name = motor_info[1]
        else:
            dev_name = self.get_name().rsplit("/", 1)[0] + "/" + motor_name
        
        def cb(name):
            db = util.get_database()
            db.put_device_property(dev_name, dict(SpecMotor=motor_name))
            
        util.create_device("TangoSpecMotor", dev_name, cb=cb)

    @command(dtype_in=str, doc_in="spec motor name")
    def RemoveMotor(self, motor_name):
        util = Util.instance()
        tango_spec_motors = util.get_device_list_by_class("TangoSpecMotor")
        for tango_spec_motor in tango_spec_motors:
            if tango_spec_motor.get_spec_motor_name() == motor_name:
                tango_spec_motor_name = tango_spec_motor.get_name()
                util.delete_device("TangoSpecMotor", tango_spec_motor_name)
                break
        else:
            raise KeyError("No motor with name '%s'" % motor_name)

    @command(dtype_in=[str], doc_in="spec counter name [, tango counter device name]")
    def AddCounter(self, counter_info):
        util = Util.instance()

        counter_name = counter_info[0]
        if len(counter_info) > 1:
            dev_name = counter_info[1]
        else:
            dev_name = self.get_name().rsplit("/", 1)[0] + "/" + counter_name
        
        def cb(name):
            db = util.get_database()
            db.put_device_property(dev_name, dict(SpecCounter=counter_name))
            
        util.create_device("TangoSpecCounter", dev_name, cb=cb)

    @command(dtype_in=str, doc_in="spec counter name")
    def RemoveCounter(self, counter_name):
        util = Util.instance()
        tango_spec_counters = util.get_device_list_by_class("TangoSpecCounter")
        for tango_spec_counter in tango_spec_counters:
            if tango_spec_counter.get_spec_counter_name() == counter_name:
                tango_spec_counter_name = tango_spec_counter.get_name()
                util.delete_device("TangoSpecCounter", tango_spec_counter_name)
                break
        else:
            raise KeyError("No counter with name '%s'" % counter_name)
        

    def __addVariable(self, variable):

        def update(value):
            self.debug_stream("update variable '%s'", variable)
            self.push_change_event(variable, json.dumps(value))
                
        v = TgGevent.get_proxy(SpecVariable.SpecVariableA,
                               variable, self.Spec,
                               dispatchMode=SpecEventsDispatcher.FIREEVENT,
                               callbacks={"update": update})
        self.__variables[variable] = v, update

        v_attr = Attr(variable, CmdArgType.DevString, AttrWriteType.READ_WRITE)
        v_attr.set_change_event(True, False)
        self.add_attribute(v_attr, self.read_Variable, self.write_Variable)


def main():
    from TangoSpecMotor import TangoSpecMotor
    from TangoSpecCounter import TangoSpecCounter
    classes = TangoSpec, TangoSpecCounter, TangoSpecMotor
    server_run(classes, verbose=True)

if __name__ == '__main__':
    main()

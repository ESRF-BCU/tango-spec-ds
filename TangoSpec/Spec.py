#!/usr/bin/env python
# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
# This file is part of the Tango SPEC device server
#
# Copyright (c) 2014, European Synchrotron Radiation Facility.
# Distributed under the GNU Lesser General Public License.
# See LICENSE.txt for more info.
#------------------------------------------------------------------------------

"""A TANGO_ device server for SPEC_ based on SpecClient."""

import json
import logging
import numbers
from functools import partial

from PyTango import Util, Attr, Except, DevFailed
from PyTango import DevState, CmdArgType, AttrWriteType, DispLevel, DebugIt
from PyTango.server import Device, DeviceMeta, attribute, command
from PyTango.server import device_property

from SpecClient_gevent import Spec as _Spec
from SpecClient_gevent import SpecCommand
from SpecClient_gevent import SpecVariable
from SpecClient_gevent import SpecEventsDispatcher
from SpecClient_gevent.SpecClientError import SpecClientError

from . import TgGevent
from .SpecCommon import execute, switch_state

#: read-only spectrum string attribute helper
str_1D_attr = partial(attribute, dtype=[str], access=AttrWriteType.READ,
                      max_dim_x=512)


# Helper methods for old spec clients:

def getCountersMneNames(spec):
    """Return counters mnemonics and names list."""
    if spec.connection is not None and spec.connection.isSpecConnected():
        get_counter_mnemonics = SpecCommand.SpecCommand('local ca[]; for (i=0; i<COUNTERS; i++) { ca[i][cnt_mne(i)]=cnt_name(i) }; return ca', spec.connection)

        counterMne = get_counter_mnemonics()
        counterList = [None]*len(counterMne)
        for counter_index, counter_dict in counterMne.iteritems():
            mne, name = counter_dict.items()[0]
            counterList[int(counter_index)]={"mne": mne, "name": name }
        return counterList
    else:
        return []

def getCountersMne(spec):
   """Return counter mnemonics list."""
   counterMneList = []
   for counter_dict in getCountersMneNames(spec):
       counterMneList.append(counter_dict["mne"])
   return counterMneList

def getCountersNames(spec):
   """Return counters names list."""
   counterNamesList = []
   for counter_dict in getCountersMneNames(spec):
       counterNamesList.append(counter_dict["name"])
       return counterNamesList


#TODO:
# 1 - tests!
# 2 - read list of available counters from spec (SpecCounterList attribute)

class Spec(Device):
    """A TANGO_ device server for SPEC_ based on SpecClient."""
    __metaclass__ = DeviceMeta

    Spec = device_property(dtype=str, default_value="localhost:spec",
                           doc="SPEC session e.g. localhost:spec")

    Motors = device_property(dtype=[str], default_value=[],
                             doc="List of registered SPEC motors to create e.g. tth, energy, phi")

    Counters = device_property(dtype=[str], default_value=[],
                               doc="List of registered SPEC counters to create e.g. mon, det, i0")

    Variables = device_property(dtype=[str], default_value=[],
                                doc="List registered SPEC variables to create e.g. myvar, mayarr, A")

    ## Attribute containning the list of all SPEC_ motors
    SpecMotorList = str_1D_attr(doc="List of all SPEC motors")

    ## Attribute containning the list of SPEC_ motors exported to TANGO_
    MotorList = str_1D_attr(doc="List of tango motors from SPEC")

    ## Attribute containning the list of all SPEC_ counters
    SpecCounterList = str_1D_attr(doc="List of all SPEC counters")

    ## Attribute containning the list of SPEC_ counters exported to TANGO_
    CounterList = str_1D_attr(doc="List of tango counters from SPEC")

    ## Attribute containning the list of SPEC_ variables exported to TANGO_
    VariableList = str_1D_attr(doc="List of SPEC variables")

    Output = attribute(dtype=str, access=AttrWriteType.READ)

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
        self.__log = logging.getLogger(self.get_name())
        Device.init_device(self)

        spec_name = self.Spec
        self.__spec_mgr = None
        self.__spec = None
        self.__spec_tty = None
        self.__variables = dict()
        self.__executing_commands = dict()

        self.set_change_event("State", True, True)
        self.set_change_event("Status", True, False)
        self.set_change_event("Output", True, False)
        self.set_change_event("MotorList", True, False)
        self.set_change_event("CounterList", True, False)
        self.set_change_event("VariableList", True, False)

        switch_state(self, DevState.INIT, "Initializing spec " + self.Spec)

        try:
            spec_host, spec_session = spec_name.split(":")
            self.debug_stream("Using spec '%s'", spec_name)
        except ValueError:
            status = "Invalid spec '%s'. Must be in format " \
                     "<host>:<spec session>" % (spec_name,)
            switch_state(self, DevState.FAULT, status)
            return

        # Create asynchronous spec access to get the data
        try:
            self.__log.debug("Start creating SPEC object")
            self.__spec = TgGevent.get_proxy(_Spec.Spec,
                                             spec_name,
                                             timeout=1000)
            self.__log.debug("Created SPEC object")
            self.__spec_tty = TgGevent.get_proxy(SpecVariable.SpecVariableA,
                                                 "output/tty", spec_name,
                                                 prefix=False,
                                                 dispatchMode=SpecEventsDispatcher.FIREEVENT,
                                                 callbacks={"update" : self.update_output})
            self.__log.debug("Created SPEC tty channel")
            switch_state(self, DevState.ON, "Connected to spec " + spec_name)
        except SpecClientError as spec_error:
            status = "Error connecting to Spec: %s" % str(spec_error)
            switch_state(self, DevState.FAULT, status)
            return

        for variable in self.Variables:
            try:
                self.__addVariable(variable)
                self.__log.debug("Added variable %s", variable)
            except SpecClientError as spec_error:
                msg = "Error adding variable '%s': %s" % (variable,
                                                          str(spec_error))
                switch_state(self, DevState.FAULT, self.get_status + "\n" + msg)

    def update_output(self, output):
        if isinstance(output, numbers.Number):
            text = "{0:12}".format(output)
        else:
            text = str(output)
        # it seems we can't push event while server
        # is executing a command
        execute(self.push_change_event , "Output", text)

    @DebugIt()
    def read_SpecMotorList(self):
        return self.__spec.getMotorsMne()

    @DebugIt()
    def read_MotorList(self):
        return self.__get_MotorList()

    @DebugIt()
    def read_SpecCounterList(self):
        if hasattr(self.__spec, "getCountersMne"):
            counter_names = self.__spec.getCountersMne()
        else:
            counter_names = getCountersMne(self.__spec)
        return counter_names

    @DebugIt()
    def read_CounterList(self):
        return self.__get_CounterList()

    @DebugIt()
    def read_VariableList(self):
        return self.__get_VariableList()

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
        except SpecClientError as error:
            status = "Spec %s error: %s" % (self.Spec, error)
            switch_state(self, DevState.FAULT, status)

        if wait:
            return str(spec_cmd.executeCommand(cmd))
        else:
            task = spec_cmd.executeCommand(cmd, wait=False)
            self.__executing_commands[id(spec_cmd)]=task
            return id(spec_cmd)

    @command(dtype_in=str, dtype_out=str)
    def ExecuteCmd(self, command):
        """
        Execute a SPEC_ command synchronously.
        Use :meth:`~Spec.ExecuteCmdA` instead if you intend to run
        commands that take some time.

        :param command:
            the command to be executed (ex: ``"wa"`` )
        :type command: str
        """
        return self._execute_cmd(command)

    @command(dtype_in=str, dtype_out=int)
    def ExecuteCmdA(self, command):
        """
        Execute a SPEC_ command asynchronously.

        :param command:
            the command to be executed (ex: ``"ascan energy 0.1 10 20 0.1"`` )
        :type command: str
        :return: an identifier for the command.
        :rtype: int
        """
        return self._execute_cmd(command, wait=False)

    @command(dtype_in=int, dtype_out=str)
    def GetReply(self, cmd_id):
        """
        Returns the reply of the SPEC_ command given by the cmd_id, previously
        requested through :meth:`~Spec.ExecuteCmdA`.
        It waits if the command is not finished

        :param cmd_id: command identifier
        :type cmd_id: int
        :return: the reply for the requested command
        :rtype: str
        """
        task = self.__executing_commands.pop(cmd_id)
        task.join()
        if task.successful():
            return str(task.value)
        else:
            raise task.exception

    @command(dtype_in=int, dtype_out=bool)
    def IsReplyArrived(self, cmd_id):
        """
        Determines if a command executed previously with the given cmd_id is
        finished.

        :param cmd_id: command identifier
        :type cmd_id: int
        :return: True if the command response as arrived or False otherwise
        :rtype: bool
        """
        if not cmd_id in self.__executing_commands:
            return True
        task = self.__executing_commands[cmd_id]
        return task.ready()

    @command(dtype_in=str, doc_in="spec variable name")
    def AddVariable(self, variable_name):
        """
        Export a SPEC_ variable to Tango by adding a new attribute to this
        device with the same name as the variable.

        :param variable_name:
            SPEC_ variable name to be exported as a TANGO_ attribute
        :type variable_name: str
        :throws PyTango.DevFailed:
            If the variable is already exposed in this TANGO_ DS.
        """
        if variable_name in self.__variables:
            raise Exception("Variable '%s' is already defined as an attribute!" %
                            (variable_name,))

        try:
            self.__addVariable(variable_name)
        except SpecClientError as error:
            status = "Error adding variable '%s': %s" % (variable_name, str(error))
            switch_state(self, DevState.FAULT, status)
            raise

        # update property in the database
        db = Util.instance().get_database()
        variables = self.__get_VariableList()
        db.put_device_property(self.get_name(), {"Variables" : variables})

        execute(self.push_change_event, "VariableList", variables)

    @command(dtype_in=str, doc_in="spec variable name")
    def RemoveVariable(self, variable_name):
        """
        Unexposes the given variable from this TANGO_ DS.

        :param variable_name: the name of the SPEC_ variable to be removed
        :type variable_name: str
        :throws PyTango.DevFailed:
            If the variable is not exposed in this TANGO_ DS
        """
        if variable_name not in self.__variables:
            raise Exception("Variable '%s' is not defined as an attribute!" %
                            (variable_name,))

        self.__removeVariable(variable_name)

        # update property in the database
        db = Util.instance().get_database()
        variables = self.__get_VariableList()
        db.put_device_property(self.get_name(), {"Variables" : variables})

        execute(self.push_change_event, "VariableList", variables)

    @command(dtype_in=[str],
             doc_in="spec motor name [, tango device name [, tango alias name]]")
    def AddMotor(self, motor_info):
        """
        Adds a new SpecMotor to this DS.

        *motor_info* must be a sequence of strings with the following options::

            spec_motor_name [, tango_device_name [, tango_alias_name]]

        Examples::

            spec = PyTango.DeviceProxy("ID00/spec/fourc")
            spec.AddMotor(("th",))
            spec.AddMotor(("tth", "ID00/fourc/tth", "theta2"))

        :param spec_motor_name:
            name of the spec motor to export to TANGO_
        :param tango_device_name:
            optional tango name to give to the new TANGO_ motor device
            [default: <tangospec_domain>/<tangospec_family>/<spec_motor_name>]
        :param tango_alias_name:
            optional alias to give to the new tango motor device
            [default: <spec_motor_name>]. Note: if the alias
            exists it will **not** be overwritten.
        :throws PyTango.DevFailed:
            If SPEC_ motor does not exist or if motor is already exported
        """
        util = Util.instance()

        motor_name = motor_info[0]

        if not motor_name in self.__spec.getMotorsMne():
            Except.throw_exception("Spec_UnknownMotor",
                                   "Unknown motor '%s'" % motor_name,
                                   "Spec::AddMotor")

        dev_name = self.get_name().rsplit("/", 1)[0] + "/" + motor_name
        if len(motor_info) > 1:
            dev_name = motor_info[1]

        motor_alias = motor_name
        if len(motor_info) > 2:
            motor_alias = motor_info[2]

        def cb(name):
            db = util.get_database()
            db.put_device_property(dev_name, dict(SpecMotor=motor_name))
            try:
                db.get_device_alias(motor_alias)
            except DevFailed:
                db.put_device_alias(dev_name, motor_alias)

        util.create_device("SpecMotor", dev_name, cb=cb)

        execute(self.push_change_event, "MotorList", self.__get_MotorList())

    @command(dtype_in=str, doc_in="spec motor name")
    def RemoveMotor(self, motor_name):
        """
        Removes the given SpecMotor from this DS.

        :param motor_name: SPEC_ motor name to be removed
        :type motor_name: str

        Examples::

            spec = PyTango.DeviceProxy("ID00/spec/fourc")
            spec.RemoveMotor("th")
        """
        util = Util.instance()
        tango_spec_motors = util.get_device_list_by_class("SpecMotor")
        for tango_spec_motor in tango_spec_motors:
            if tango_spec_motor.get_spec_motor_name() == motor_name:
                tango_spec_motor_name = tango_spec_motor.get_name()
                util.delete_device("SpecMotor", tango_spec_motor_name)
                break
        else:
            raise KeyError("No motor with name '%s'" % motor_name)

        execute(self.push_change_event, "MotorList", self.__get_MotorList())

    @command(dtype_in=[str],
             doc_in="spec counter name [, tango device name [, tango alias name]]")
    def AddCounter(self, counter_info):
        """
        Adds a new SpecCounter to this DS.

        *counter_info* must be a sequence of strings with the following options::

            spec_counter_name [, tango_device_name [, tango_alias_name]]

        Examples::

            spec = PyTango.DeviceProxy("ID00/spec/fourc")
            spec.AddCounter(("sec",))
            spec.AddCounter(("det", "ID00/fourc/detector", "detector"))

        :param spec_counter_name:
            name of the spec counter to export to TANGO_
        :param tango_device_name:
            optional tango name to give to the new TANGO_ counter device
            [default: <tangospec_domain>/<tangospec_family>/<spec_counter_name>]
        :param tango_alias_name:
            optional alias to give to the new tango counter device
            [default: <spec_counter_name>]. Note: if the alias
            exists it will **not** be overwritten.
        :throws PyTango.DevFailed:
            If SPEC_ counter does not exist or if counter is already exported
        """        
        util = Util.instance()

        counter_name = counter_info[0]

        if not counter_name in self.__spec.getCountersMne():
            Except.throw_exception("Spec_UnknownCounter",
                                   "Unknown counter '%s'" % counter_name,
                                   "Spec::AddCounter")

        dev_name = self.get_name().rsplit("/", 1)[0] + "/" + counter_name
        if len(counter_info) > 1:
            dev_name = counter_info[1]

        counter_alias = counter_name
        if len(counter_info) > 2:
            counter_alias = counter_info[2]

        def cb(name):
            db = util.get_database()
            db.put_device_property(dev_name, dict(SpecCounter=counter_name))
            try:
                db.get_device_alias(counter_alias)
            except DevFailed:
                db.put_device_alias(dev_name, counter_alias)

        util.create_device("SpecCounter", dev_name, cb=cb)

        execute(self.push_change_event, "CounterList", self.__get_CounterList())

    @command(dtype_in=str, doc_in="spec counter name")
    def RemoveCounter(self, counter_name):
        util = Util.instance()
        tango_spec_counters = util.get_device_list_by_class("SpecCounter")
        for tango_spec_counter in tango_spec_counters:
            if tango_spec_counter.get_spec_counter_name() == counter_name:
                tango_spec_counter_name = tango_spec_counter.get_name()
                util.delete_device("SpecCounter", tango_spec_counter_name)
                break
        else:
            raise KeyError("No counter with name '%s'" % counter_name)

        execute(self.push_change_event, "CounterList", self.__get_CounterList())

    #
    # Helper methods
    #

    def __execute(self, f, *args, **kwargs):
        self.__tango_worker.execute(f, *args, **kwargs)

    def __get_MotorList(self):
        util = Util.instance()
        motors = util.get_device_list_by_class("SpecMotor")
        return ["{0} {1}".format(m.get_spec_motor_name(), m.get_name()) for m in motors]

    def __get_CounterList(self):
        util = Util.instance()
        counters = util.get_device_list_by_class("SpecCounter")
        return ["{0} {1}".format(c.get_spec_counter_name(), c.get_name()) for c in counters]

    def __get_VariableList(self):
        return sorted(self.__variables)

    def __addVariable(self, variable):
        def update(value):
            self.debug_stream("update variable '%s'", variable)
            execute(self.push_change_event, variable, json.dumps(value))

        v = TgGevent.get_proxy(SpecVariable.SpecVariableA,
                               variable, self.Spec,
                               dispatchMode=SpecEventsDispatcher.FIREEVENT,
                               callbacks={"update": update})
        self.__variables[variable] = v, update

        v_attr = Attr(variable, CmdArgType.DevString, AttrWriteType.READ_WRITE)
        v_attr.set_change_event(True, False)
        v_attr.set_disp_level(DispLevel.EXPERT)
        self.add_attribute(v_attr, self.read_Variable, self.write_Variable)

    def __removeVariable(self, variable):
        del self.__variables[variable]
        self.remove_attribute(variable)


def run(**kwargs):
    """Runs the Spec device server"""
    logging.basicConfig(level=logging.DEBUG,
                        format="%(threadName)10s %(asctime)s "
                        "%(levelname)5s %(name)s: %(message)s")

    from PyTango.server import run
    from .SpecMotor import SpecMotor
    from .SpecCounter import SpecCounter
    classes = Spec, SpecCounter, SpecMotor
    run(classes, **kwargs)


if __name__ == '__main__':
    run()

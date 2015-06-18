#!/usr/bin/env python
# -*- coding: utf-8 -*-

#---------------------------------------------------------------------
# This file is part of the Tango SPEC device server
#
# Copyright (c) 2014, European Synchrotron Radiation Facility.
# Distributed under the GNU Lesser General Public License.
# See LICENSE.txt for more info.
#---------------------------------------------------------------------

"""A TANGO_ device server for SPEC_ based on SpecClient."""

import re
import json
import logging
import numbers
from functools import partial

from PyTango import requires_pytango

requires_pytango("8.1.7", software_name="TangoSpec")

from PyTango import GreenMode
from PyTango import DevState, Util, Attr, Except, DevFailed
from PyTango import CmdArgType, AttrWriteType, DispLevel, DebugIt
from PyTango.server import Device, DeviceMeta, attribute, command
from PyTango.server import device_property

from SpecClient_gevent import Spec as _Spec
from SpecClient_gevent import SpecCommand
from SpecClient_gevent import SpecVariable
from SpecClient_gevent import SpecEventsDispatcher
from SpecClient_gevent.SpecClientError import SpecClientError

from TangoSpec.SpecCommon import execute, switch_state

#: read-only spectrum string attribute helper
str_1D_attr = partial(attribute, dtype=[str], access=AttrWriteType.READ,
                      max_dim_x=512)

_SpecCmdLineRE = re.compile("\\n*(?P<line>\d+)\.(?P<session>\w+)\>\s*")


class Spec(Device):
    """A TANGO_ device for SPEC_ based on SpecClient."""
    __metaclass__ = DeviceMeta

    Spec = device_property(dtype=str, default_value="localhost:spec",
        doc="SPEC session (examples: localhost:spec, mach101:fourc)")

    AutoDiscovery = device_property(dtype=bool, default_value=False,
        doc="Enable/disable auto discovery")

    OutputBufferMaxLength = device_property(dtype=int,
        default_value=1000, doc="maximum output buffer length")

    CommandHistoryMaxLength = device_property(dtype=int,
        default_value=1000, doc="maximum command history length")

    Motors = device_property(dtype=[str], default_value=[],
        doc="List of registered SPEC motors to create "
            "(examples: tth, energy, phi)")

    Counters = device_property(dtype=[str], default_value=[],
        doc="List of registered SPEC counters to create "
            "(examples: mon, det, i0). "
            "Internal property. Not to be set by user")

    Variables = device_property(dtype=[str], default_value=[],
        doc="List registered SPEC variables to create "
            "(examples: myvar, mayarr, A). "
            "Internal property. Not to be set by user")

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

    ## Spec output
    Output = attribute(dtype=str, access=AttrWriteType.READ)

    ## Command history
    CommandHistory = str_1D_attr(doc="List of spec commands executed from "
                                 "this server")

    ## Version: TangoSpec version
    Version = attribute(dtype=str, access=AttrWriteType.READ)
    
    def __init__(self, *args, **kwargs):
        self.__cmd_line = False
        self.__remove_line = False
        self.__constructing = True
        Device.__init__(self, *args, **kwargs)

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
        dbg = self.__log.debug
        exc = self.__log.exception
        err = self.__log.error
        Device.init_device(self)

        spec_name = self.Spec
        self.__spec_mgr = None
        self.__spec = None
        self.__spec_tty = None
        self.__output = []
        self.__variables = dict()
        self.__executing_commands = dict()
        self.__command_history = []

        self.set_change_event("State", True, True)
        self.set_change_event("Status", True, False)
        self.set_change_event("Output", True, False)
        self.set_change_event("MotorList", True, False)
        self.set_change_event("CounterList", True, False)
        self.set_change_event("VariableList", True, False)
        self.set_change_event("CommandHistory", True, False)

        switch_state(self, DevState.INIT, "Initializing spec " + self.Spec)

        try:
            spec_host, spec_session = spec_name.split(":")
            dbg("Using spec %s:%s", spec_host, spec_session)
        except ValueError:
            err("Error parsing SPEC name")
            dbg("Details:", exc_info=1)
            status = "Invalid spec '%s'. Must be in format " \
                     "<host>:<spec session>" % (spec_name,)
            switch_state(self, DevState.FAULT, status)
            self.__constructing = False
            return

        # Create asynchronous spec access to get the data
        try:
            dbg("Creating SPEC object...")
            self.__spec = _Spec.Spec()
            self.__spec.connectToSpec(spec_name, timeout=.25)
            dbg("Finished creating SPEC object")
        except SpecClientError as spec_error:
            err("Error creating SPEC object")
            dbg("Details:", exc_info=1)
            status = "Error connecting to Spec {0} output".format(spec_name)
            switch_state(self, DevState.FAULT, status)
            self.__constructing = False
            return

        cb = dict(update=self.__onUpdateOutput)
        try:
            dbg("Creating SPEC tty channel...")
            self.__spec_tty = SpecVariable.SpecVariableA(callbacks=cb)
            self.__spec_tty.connectToSpec("output/tty", spec_name,
                                          dispatchMode=SpecEventsDispatcher.FIREEVENT,
                                          prefix=False)
            dbg("Finished creating SPEC tty channel")
            switch_state(self, DevState.ON, "Connected to spec " + spec_name)
        except SpecClientError as spec_error:
            err("Error creating SPEC tty channel")
            dbg("Details:", exc_info=1)
            status = "Error connecting to Spec {0} output".format(spec_name)
            switch_state(self, DevState.FAULT, status)
            self.__constructing = False
            return

        for variable in self.Variables:
            self.__addVariableInit(variable)

        if self.AutoDiscovery and not self.__constructing:
            self.Reconstruct()
        self.__constructing = False
        dbg("Finished creating Spec %s", spec_name)

    def __addVariableInit(self, variable):
        variable_info = variable.split()
        try:
            self.__addVariable(*variable_info)
        except SpecClientError as spec_error:
            self.__log.error("Error creating variable %s", variable_info[0])
            self.__log.debug("Details:", exc_info=1)
            msg = "Error adding variable '%s': %s" % (variable_info[0],
                                                      str(spec_error))
            switch_state(self, DevState.FAULT, self.get_status + "\n" + msg)

    def __onUpdateOutput(self, output):
        if isinstance(output, numbers.Number):
            text = "{0:12}\n".format(output)
        else:
            text = str(output)

        if self.__remove_line:
            self.__remove_line = False
            if "\n" not in text and self.__output:
                self.__output.pop()

        # ignore new line after prompt
        if self.__cmd_line and text == "\n":
            self.__cmd_line = False
            return

        self.__cmd_line = _SpecCmdLineRE.match(text)

        if text.endswith("\r"):
            self.__remove_line = True

        self.__output.append(text)
        while len(self.__output) > self.OutputBufferMaxLength:
            self.__output.pop(0)
        self.push_change_event("Output", text)

    @DebugIt()
    def read_SpecMotorList(self):
        return self.__spec.getMotorsMne()

    @DebugIt()
    def read_MotorList(self):
        return self.__get_MotorList()

    @DebugIt()
    def read_SpecCounterList(self):
        return self.__spec.getCountersMne()

    @DebugIt()
    def read_CounterList(self):
        return self.__get_CounterList()

    @DebugIt()
    def read_VariableList(self):
        return self.__get_VariableList()

    @DebugIt()
    def read_Output(self):
        return "".join(self.__output)

    @DebugIt()
    def read_Variable(self, attr):
        v_name = attr.get_name()
        self.__log.debug("read variable %s", v_name)
        value = self.__variables[v_name][0].getValue()
        attr.set_value(json.dumps(value))

    @DebugIt()
    def write_Variable(self, attr):
        v_name, value = attr.get_name(), attr.get_write_value()
        value = json.loads(value)
        self.__log.debug("set %s = %s", v_name, value)
        self.__variables[v_name][0].setValue(value)

    def read_CommandHistory(self):
        return self.__command_history

    def read_Version(self):
        import TangoSpec
        return TangoSpec.__version__

    # ----------------------------------------------------------------
    # Tango Commands
    # ----------------------------------------------------------------

    def _execute_cmd(self, cmd, wait=True):
        try:
            spec_cmd = SpecCommand.SpecCommand(None, self.Spec)
        except SpecClientError as error:
            status = "Spec %s error: %s" % (self.Spec, error)
            switch_state(self, DevState.FAULT, status)

        if wait:
            result = str(spec_cmd.executeCommand(cmd))
        else:
            task = spec_cmd.executeCommand(cmd, wait=False)
            self.__executing_commands[id(spec_cmd)] = task, cmd, spec_cmd
            result = id(spec_cmd)

        self.__appendCommandHistory(cmd)
        return result

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
        task, _, _ = self.__executing_commands.pop(cmd_id)
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
        task, _, _ = self.__executing_commands[cmd_id]
        return task.ready()

    @command(dtype_in=int, dtype_out=None)
    def AbortCmd(self, cmd_id):
        """
        Aborts the command in execution given by the cmd_id, previously
        requested through :meth:`~Spec.ExecuteCmdA`.

        :param cmd_id: command identifier
        :type cmd_id: int
        """
        try:
            task, cmd_name, spec_cmd = self.__executing_commands[cmd_id]
        except KeyError:
            raise ValueError("Command not being run")
        self.__log.debug("Abort command %s", cmd_name)
        spec_cmd.abort()

    @command(dtype_in=(str,),
             doc_in="spec variable name [, tango attribute name]")
    def AddVariable(self, var_info):
        """
        Export a SPEC_ variable to Tango by adding a new attribute
        to this device with the same name as the variable.

        :param var_info:
            sequence of strings with the following syntax:
            spec variable name [, tango attribute name]
        :type variable_info: sequence<str>
        :throws PyTango.DevFailed:
            If the variable is already exposed in this TANGO_ DS.
        """
        if len(var_info) < 2:
            var_info = 2*var_info
        var_name, var_tango_name = var_info
        self.__log.info("Adding new spec variable %s as %s...", var_name,
                        var_tango_name)
        if var_name in self.__variables:
            raise Exception("Variable '%s' is already defined as an attribute!" %
                            (var_name,))

        try:
            self.__addVariable(*var_info)
        except SpecClientError as error:
            status = "Error adding variable '%s': %s" % (var_name, str(error))
            switch_state(self, DevState.FAULT, status)
            raise

        # update property in the database
        db = Util.instance().get_database()
        variables = self.__get_VariableList()
        db.put_device_property(self.get_name(), {"Variables" : variables})

        self.push_change_event("VariableList", variables)
        self.__log.info("Finished adding new variable")

    @command(dtype_in=str, doc_in="spec variable name")
    def RemoveVariable(self, var_name):
        """
        Unexposes the given variable from this device.

        :param var_name:
            the name of the TANGO_ attribute corresponding to a SPEC_ variable
        :type var_name: str
        :throws PyTango.DevFailed:
            If the variable is not exposed in this TANGO_ DS
        """
        self.__log.info("Removing variable %s...", var_name)
        for tango_var_name, (var, _) in self.__variables.items():
            if var.varName == var_name:
                break
        else:
            raise Exception("Variable '%s' is not defined as an attribute!" %
                            (var_name,))

        del self.__variables[tango_var_name]
        self.remove_attribute(tango_var_name)

        # update property in the database
        db = Util.instance().get_database()
        variables = self.__get_VariableList()
        db.put_device_property(self.get_name(), {"Variables" : variables})

        self.push_change_event("VariableList", variables)
        self.__log.info("Finished removing variable")

    @command(dtype_in=[str],
             doc_in="spec motor name [, tango device name [, tango alias name]]")
    def AddMotor(self, motor_info):
        """
        Adds a new SpecMotor to this DS.

        :param motor_info:
            sequence of strings with the following syntax:
            spec_motor_name [, tango_device_name [, tango_alias_name]]
        :type motor_info: sequence<str>

        Examples::

            spec = PyTango.DeviceProxy("ID00/spec/fourc")
            spec.AddMotor(("th",))
            spec.AddMotor(("tth", "ID00/fourc/tth", "theta2"))

        spec_motor_name
            name of the spec motor to export to TANGO_
        tango_device_name
            optional tango name to give to the new TANGO_ motor device
            [default: <tangospec_domain>/<tangospec_family>/<spec_motor_name>]
        tango_alias_name
            optional alias to give to the new tango motor device
            [default: <spec_motor_name>]. Note: if the alias
            exists it will **not** be overwritten.

        :throws PyTango.DevFailed:
            If SPEC_ motor does not exist or if motor is already exported
        """
        self.__addElement("Motor", motor_info)

    @command(dtype_in=str, doc_in="spec motor name")
    def RemoveMotor(self, motor_name):
        """
        Removes the given SpecMotor from this DS.

        :param motor_name: SPEC_ motor name to be removed
        :type motor_name: str

        Examples::

            spec = PyTango.DeviceProxy("ID00/spec/fourc")
            spec.RemoveMotor("th")

        :throws PyTango.DevFailed:
            If motor does not exist
        """
        self.__removeElement("Motor", motor_name)

    @command(dtype_in=[str],
             doc_in="spec counter name [, tango device name [, tango alias name]]")
    def AddCounter(self, counter_info):
        """
        Adds a new SpecCounter to this DS.

        :param counter_info:
            sequence of strings with the following syntax:
            spec_counter_name [, tango_device_name [, tango_alias_name]]
        :type counter_info: sequence<str>

        Examples::

            spec = PyTango.DeviceProxy("ID00/spec/fourc")
            spec.AddCounter(("sec",))
            spec.AddCounter(("det", "ID00/fourc/detector", "detector"))

        spec_counter_name
            name of the spec counter to export to TANGO_
        tango_device_name
            optional tango name to give to the new TANGO_ counter device
            [default: <tangospec_domain>/<tangospec_family>/<spec_counter_name>]
        tango_alias_name
            optional alias to give to the new tango counter device
            [default: <spec_counter_name>]. Note: if the alias
            exists it will **not** be overwritten.

        :throws PyTango.DevFailed:
            If SPEC_ counter does not exist or if counter is already exported
        """
        self.__addElement("Counter", counter_info)

    @command(dtype_in=str, doc_in="spec counter name")
    def RemoveCounter(self, counter_name):
        """
        Removes the given SpecCounter from this DS.

        :param counter_name: SPEC_ counter name to be removed
        :type counter_name: str

        Examples::

            spec = PyTango.DeviceProxy("ID00/spec/fourc")
            spec.RemoveCounter("th")

        :throws PyTango.DevFailed:
            If counter does not exist
        """
        self.__removeElement("Counter", counter_name)


    @command
    def Reconstruct(self):
        """
        Exposes to Tango all counters and motors that where found
        in SPEC.
        """
        reconstruct(self)

    #
    # Helper methods
    #

    def __execute(self, f, *args, **kwargs):
        self.__tango_worker.execute(f, *args, **kwargs)

    def __addElement(self, etype, element_info):
        dev_type = "Spec" + etype
        etype_lower = etype.lower()
        spec_name = element_info[0]
        self.__log.info("Adding new %s '%s'...", etype_lower, spec_name)

        get_f_name = "get{0}sMne".format(etype)
        spec_elements = getattr(self.__spec, get_f_name)()

        devices = Util.instance().get_device_list_by_class(dev_type)
        for device in devices:
            if device.get_spec_name() == spec_name:
                raise ValueError("{0} '{1}' already registered".format(etype,
                    spec_name))

        if not spec_name in spec_elements:
            Except.throw_exception("Spec_Unknown{0}".format(etype),
                "Unknown {0} '{1}'".format(etype_lower, spec_name),
                "Spec.Add{0}".format(etype))

        dev_name = self.get_name().rsplit("/", 1)[0] + "/" + spec_name
        if len(element_info) > 1:
            dev_name = element_info[1]

        element_alias = spec_name
        if len(element_info) > 2:
            element_alias = element_info[2]

        execute(self.__addElementTango, etype, spec_name, dev_name,
                element_alias)
        self.__log.info("Finished adding %s '%s'", etype_lower, spec_name)

    def __addElementTango(self, etype, spec_name, dev_name, dev_alias):
        dev_type, attr = "Spec" + etype, etype + "List"
        def cb(name):
            db = Util.instance().get_database()
            db.put_device_property(dev_name, {dev_type: spec_name})
            try:
                old_dev_name = db.get_device_alias(dev_alias)
                self.__log.warning("%s already associated with device %s. "\
                                   "Tango alias will NOT be created",
                                   dev_alias, old_dev_name)
            except DevFailed:
                db.put_device_alias(dev_name, dev_alias)

        Util.instance().create_device(dev_type, dev_name, cb=cb)
        self.push_change_event(attr, self.__get_ElementList(etype))

    def __removeElement(self, etype, element_name):
        etype_lower = etype.lower()
        dev_type = "Spec" + etype
        self.__log.info("Removing %s '%s'...", etype_lower, element_name)
        devices = Util.instance().get_device_list_by_class(dev_type)
        for device in devices:
            if device.get_spec_name() == element_name:
                dev_name = device.get_name()
                execute(self.__removeElementTango, etype, dev_name)
                break
        else:
            raise KeyError("No {0} with name '{1}".format(etype_lower,
                                                          element_name))
        self.__log.info("Finished removing %s '%s'", etype_lower, element_name)

    def __removeElementTango(self, etype, dev_name):
        dev_type, attr = "Spec" + etype, etype + "List"
        Util.instance().delete_device(dev_type, dev_name)
        self.push_change_event(attr, self.__get_ElementList(etype))

    def __get_ElementList(self, etype):
        elements = Util.instance().get_device_list_by_class("Spec" + etype)
        return ["{0} {1}".format(element.get_spec_name(), element.get_name())
                for element in elements]

    def __get_MotorList(self):
        return self.__get_ElementList("Motor")

    def __get_CounterList(self):
        return self.__get_ElementList("Counter")

    def __get_VariableList(self):
        vl = []
        for var_tango_name in sorted(self.__variables):
            var, _ = self.__variables[var_tango_name]
            vl.append("{0} {1}".format(var.varName, var_tango_name))
        return vl

    def __addVariable(self, var_name, var_tango_name=None):
        if var_tango_name is None:
            var_tango_name = var_name
        self.__log.debug("Adding variable %s as %s", var_name, var_tango_name)
        multi_attr = self.get_device_attr()
        has_attr = True
        try:
            multi_attr.get_attr_by_name(var_tango_name)
        except:
            has_attr = False

        if not has_attr:
            self.__log.debug("Creating attribute %s for variable %s",
                             var_tango_name, var_name)
            doc = "spec variable '{0}' (string in JSON format)".format(var_name)
            attr = attribute(name=var_tango_name, dtype=str,
                             access=AttrWriteType.READ_WRITE, doc=doc,
                             fget=self.read_Variable, fset=self.write_Variable,
                             display_level=DispLevel.EXPERT)
            self.__log.debug("Registering attribute for variable '%s'...",
                             var_name)
            self.add_attribute(attr)
            attr_obj = self.get_device_attr().get_attr_by_name(var_tango_name)
            attr_obj.set_change_event(True, False)

        self.__log.debug("Connecting to spec for variable '%s'...", var_name)
        def update(value):
            self.__log.debug("start update variable '%s' value...", var_name)
            self.push_change_event(var_tango_name, json.dumps(value))
            self.__log.debug("finish update variable '%s' value", var_name)
        cb = dict(update=update)
        v = SpecVariable.SpecVariableA(callbacks=cb)
        self.__variables[var_tango_name] = v, update
        v.connectToSpec(var_name, self.Spec,
                        dispatchMode=SpecEventsDispatcher.FIREEVENT)

    def __appendCommandHistory(self, cmd):
        """
        Append command to the history if current command is different from
        last command. Fires an event on the CommandHistory attribute with
        the last command executed
        """
        history = self.__command_history
        if history and history[-1] == cmd:
            return
        history.append(cmd)
        while len(history) > self.CommandHistoryMaxLength:
            history.pop(0)
        self.push_change_event("CommandHistory", [cmd])



def __findClassDevices(tg_class, prop=None):
    if prop is None:
        prop = tg_class
    util = Util.instance()
    db = util.get_database()
    dev_classes = db.get_device_class_list(util.get_ds_name())
    devs = dict(zip(dev_classes[1::2], dev_classes[::2]))
    tango_devs = dict()
    tg_class_devs = devs.get(tg_class, ())
    for dev_name in tg_class_devs:
        mne = db.get_device_property(dev_name, prop)[prop][0]
        tango_devs[dev_name] = mne
        return tango_devs


def reconstruct(spec_dev):
    """
    Exposes to Tango all counters and motors that where found in SPEC.
    """
    log = logging.getLogger(spec_dev.get_name())
    log.debug("Reconstructing...")
    spec = spec_dev.get_spec()
    util = Util.instance()
    get_class_devs = util.get_device_list_by_class
    motor_devs = set([m.SpecMotor for m in get_class_devs("SpecMotor")])
    counter_devs = set([m.SpecCounter for m in get_class_devs("SpecCounter")])

    spec_motors = set(spec.getMotorsMne())
    new_motors = spec_motors.difference(motor_devs)
    del_motors = motor_devs.difference(spec_motors)
    if new_motors:
        log.debug("new motors: %s", ", ".join(new_motors))
    else:
        log.debug("no new motors to be added")
    if del_motors:
        log.debug("remove motors: %s", ", ".join(del_motors))
    else:
        log.debug("no motors to be removed")
    for motor in new_motors:
        spec_dev.AddMotor([motor])
    for motor in del_motors:
        spec_dev.RemoveMotor(motor)

    spec_counters = set(spec.getCountersMne())
    new_counters = spec_counters.difference(counter_devs)
    del_counters = counter_devs.difference(spec_counters)
    if new_counters:
        log.debug("new counters: %s", ", ".join(new_counters))
    else:
        log.debug("no new counters to be added")
    if del_counters:
        log.debug("remove counters: %s", ", ".join(del_counters))
    else:
        log.debug("no counters to be removed")
    for counter in new_counters:
        spec_dev.AddCounter([counter])
    for counter in del_counters:
        spec_dev.RemoveCounter(counter)


def reconstruct_init():
    util = Util.instance()
    spec_devs = util.get_device_list_by_class("Spec")
    if not spec_devs:
        return
    spec_dev = spec_devs[0]
    if not spec_dev.AutoDiscovery:
        return
    reconstruct(spec_dev)


def run(**kwargs):
    """Runs the Spec device server"""
    from PyTango.server import run
    from .SpecMotor import SpecMotor
    from .SpecCounter import SpecCounter
    classes = Spec, SpecCounter, SpecMotor
    orig_post_init_cb = kwargs.get('post_init_callback')
    if orig_post_init_cb:
        def post_init_cb():
            orig_post_init_cb()
            reconstruct_init()
    else:
        post_init_cb = reconstruct_init
    kwargs['post_init_callback'] = post_init_cb
    kwargs['green_mode'] = GreenMode.Gevent
    run(classes, **kwargs)


if __name__ == '__main__':
    run(verbose=True)

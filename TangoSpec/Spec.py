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

from PyTango import DevState, Util, Attr, Except, DevFailed
from PyTango import CmdArgType, AttrWriteType, DispLevel, DebugIt
from PyTango.server import Device, DeviceMeta, attribute, command
from PyTango.server import device_property

from SpecClient_gevent import Spec as _Spec
from SpecClient_gevent import SpecCommand
from SpecClient_gevent import SpecVariable
from SpecClient_gevent import SpecEventsDispatcher
from SpecClient_gevent.SpecClientError import SpecClientError

from TangoSpec.TgGevent import get_proxy
from TangoSpec.SpecCommon import execute, switch_state

#: read-only spectrum string attribute helper
str_1D_attr = partial(attribute, dtype=[str], access=AttrWriteType.READ,
                      max_dim_x=512)

_SpecCmdLineRE = re.compile("\\n*(?P<line>\d+)\.(?P<session>\w+)\>\s*")


#TODO:
# 1 - tests!


class Spec(Device):
    """A TANGO_ device for SPEC_ based on SpecClient."""
    __metaclass__ = DeviceMeta

    Spec = device_property(dtype=str, default_value="localhost:spec",
        doc="SPEC session (examples: localhost:spec, mach101:fourc)")

    AutoDiscovery = device_property(dtype=bool, default_value=False,
        doc="Enable/disable auto discovery")

    OutputBufferMaxLength = device_property(dtype=int,
        default_value=1000, doc="maximum output buffer length")

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

        self.set_change_event("State", True, True)
        self.set_change_event("Status", True, False)
        self.set_change_event("Output", True, False)
        self.set_change_event("MotorList", True, False)
        self.set_change_event("CounterList", True, False)
        self.set_change_event("VariableList", True, False)

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
            self.__spec = get_proxy(_Spec.Spec)
            self.__spec.connectToSpec(spec_name, timeout=1.0)
            dbg("Created SPEC object")
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
            self.__spec_tty = get_proxy(SpecVariable.SpecVariableA,
                                        callbacks=cb)
            self.__spec_tty.connectToSpec("output/tty", spec_name,
                                          dispatchMode=SpecEventsDispatcher.FIREEVENT,
                                          prefix=False)
            dbg("Created SPEC tty channel")
            switch_state(self, DevState.ON, "Connected to spec " + spec_name)
        except SpecClientError as spec_error:
            err("Error creating SPEC tty channel")
            dbg("Details:", exc_info=1)
            status = "Error connecting to Spec {0} output".format(spec_name)
            switch_state(self, DevState.FAULT, status)
            self.__constructing = False
            return

        for variable in self.Variables:
            try:
                self.__addVariable(variable)
            except SpecClientError as spec_error:
                err("Error creating variable %s", variable)
                dbg("Details:", exc_info=1)
                msg = "Error adding variable '%s': %s" % (variable,
                                                          str(spec_error))
                switch_state(self, DevState.FAULT, self.get_status + "\n" + msg)

        if self.AutoDiscovery and not self.__constructing:
            self.Reconstruct()
        self.__constructing = False

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
        execute(self.push_change_event , "Output", text)

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
        value = self.__variables[v_name][0].getValue()
        attr.set_value(json.dumps(value))

    @DebugIt()
    def write_Variable(self, attr):
        v_name, value = attr.get_name(), attr.get_write_value()
        value = json.loads(value)
        self.__log.debug("set %s = %s", v_name, value)
        self.__variables[v_name][0].setValue(value)

    # ----------------------------------------------------------------
    # Tango Commands
    # ----------------------------------------------------------------

    def _execute_cmd(self, cmd, wait=True):
        try:
            spec_cmd = get_proxy(SpecCommand.SpecCommand, None, self.Spec)
        except SpecClientError as error:
            status = "Spec %s error: %s" % (self.Spec, error)
            switch_state(self, DevState.FAULT, status)

        if wait:
            return str(spec_cmd.executeCommand(cmd))
        else:
            task = spec_cmd.executeCommand(cmd, wait=False)
            self.__executing_commands[id(spec_cmd)] = task, cmd, spec_cmd
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
        self.__log.info("Abort command %s", cmd_name)
        spec_cmd.abort()

    @command(dtype_in=str, doc_in="spec variable name")
    def AddVariable(self, variable_name):
        """
        Export a SPEC_ variable to Tango by adding a new attribute
        to this device with the same name as the variable.

        :param variable_name:
            SPEC_ variable name to be exported as a TANGO_ attribute
        :type variable_name: str
        :throws PyTango.DevFailed:
            If the variable is already exposed in this TANGO_ DS.
        """
        self.__log.info("Adding new variable %s", variable_name)
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
        Unexposes the given variable from this device.

        :param variable_name: the name of the SPEC_ variable to be removed
        :type variable_name: str
        :throws PyTango.DevFailed:
            If the variable is not exposed in this TANGO_ DS
        """
        self.__log.info("Removing variable %s", variable_name)
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
        self.__log.info("Adding new motor %s", motor_info)
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
                old_dev_name = db.get_device_alias(motor_alias)
                self.__log.warning(
                    "%s already associated with device %s. Tango "
                    "alias will NOT be created", motor_alias,
                    old_dev_name)
            except DevFailed:
                db.put_device_alias(dev_name, motor_alias)

        util.create_device("SpecMotor", dev_name, cb=cb)

        execute(self.push_change_event, "MotorList",
                self.__get_MotorList())

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
        self.__log.info("Removing motor %s", motor_name)
        util = Util.instance()
        tango_spec_motors = util.get_device_list_by_class("SpecMotor")
        for tango_spec_motor in tango_spec_motors:
            if tango_spec_motor.get_spec_motor_name() == motor_name:
                tango_spec_motor_name = tango_spec_motor.get_name()
                util.delete_device("SpecMotor", tango_spec_motor_name)
                break
        else:
            raise KeyError("No motor with name '%s'" % motor_name)

        execute(self.push_change_event, "MotorList",
                self.__get_MotorList())

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
        self.__log.info("Adding new counter %s", counter_info)
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
            db.put_device_property(dev_name,
                                   dict(SpecCounter=counter_name))
            try:
                old_dev_name = db.get_device_alias(counter_alias)
                self.__log.warning(
                    "%s already associated with device %s. Tango "
                    "alias will NOT be created", counter_alias,
                    old_dev_name)
            except DevFailed:
                db.put_device_alias(dev_name, counter_alias)

        util.create_device("SpecCounter", dev_name, cb=cb)

        execute(self.push_change_event, "CounterList",
                self.__get_CounterList())

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
        self.__log.info("Removing counter %s", counter_name)
        util = Util.instance()
        tango_spec_counters = util.get_device_list_by_class("SpecCounter")
        for tango_spec_counter in tango_spec_counters:
            if tango_spec_counter.get_spec_counter_name() == counter_name:
                tango_spec_counter_name = tango_spec_counter.get_name()
                util.delete_device("SpecCounter", tango_spec_counter_name)
                break
        else:
            raise KeyError("No counter with name '%s'" % counter_name)

        execute(self.push_change_event, "CounterList",
                self.__get_CounterList())

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
        self.__log.debug("Adding variable %s", variable)
        def update(value):
            self.__log.debug("update variable '%s'", variable)
            execute(self.push_change_event, variable, json.dumps(value))

        cb = dict(update=update)
        v = get_proxy(SpecVariable.SpecVariableA, callbacks=cb)
        v.connectToSpec(variable, self.Spec,
                        dispatchMode=SpecEventsDispatcher.FIREEVENT)
        self.__variables[variable] = v, update

        v_attr = Attr(variable, CmdArgType.DevString,
                      AttrWriteType.READ_WRITE)
        v_attr.set_change_event(True, False)
        v_attr.set_disp_level(DispLevel.EXPERT)
        self.add_attribute(v_attr, self.read_Variable,
                           self.write_Variable)

    def __removeVariable(self, variable):
        del self.__variables[variable]
        self.remove_attribute(variable)


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
    logging.info("Reconstructing...")
    spec = spec_dev.get_spec()
    util = Util.instance()
    get_class_devs = util.get_device_list_by_class
    motor_devs = set([m.SpecMotor for m in get_class_devs("SpecMotor")])
    counter_devs = set([m.SpecCounter for m in get_class_devs("SpecCounter")])

    spec_motors = set(spec.getMotorsMne())
    new_motors = spec_motors.difference(motor_devs)
    del_motors = motor_devs.difference(spec_motors)
    if new_motors:
        logging.info("new motors: %s", ", ".join(new_motors))
    else:
        logging.info("no new motors to be added")
    if del_motors:
        logging.info("remove motors: %s", ", ".join(del_motors))
    else:
        logging.info("no motors to be removed")
    for motor in new_motors:
        spec_dev.AddMotor([motor])
    for motor in del_motors:
        spec_dev.RemoveMotor(motor)

    spec_counters = set(spec.getCountersMne())
    new_counters = spec_counters.difference(counter_devs)
    del_counters = counter_devs.difference(spec_counters)
    if new_counters:
        logging.info("new counters: %s", ", ".join(new_counters))
    else:
        logging.info("no new counters to be added")
    if del_counters:
        logging.info("remove counters: %s", ", ".join(del_counters))
    else:
        logging.info("no counters to be removed")
    for counter in new_counters:
        spec_dev.AddCounter([counter])
    for counter in del_counters:
        spec_dev.RemoveCounter(counter)


def reconstruct_init():
    util = Util.instance()
    spec_dev = util.get_device_list_by_class("Spec")[0]
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
    run(classes, **kwargs)


if __name__ == '__main__':
    run()

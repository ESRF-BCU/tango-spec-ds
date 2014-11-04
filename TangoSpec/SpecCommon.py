# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
# This file is part of the Tango SPEC device server
#
# Copyright (c) 2014, European Synchrotron Radiation Facility.
# Distributed under the GNU Lesser General Public License.
# See LICENSE.txt for more info.
#------------------------------------------------------------------------------

"""A TANGO motor device for SPEC based on SpecClient."""

import Queue
import logging
import threading

from PyTango import DevState, Util

from SpecClient_gevent import SpecMotor
from SpecClient_gevent import SpecCounter

SpecMotorState_2_TangoState = {
    SpecMotor.NOTINITIALIZED: DevState.UNKNOWN,
    SpecMotor.UNUSABLE: DevState.UNKNOWN,
    SpecMotor.READY: DevState.ON,
    SpecMotor.MOVESTARTED: DevState.MOVING,
    SpecMotor.MOVING: DevState.MOVING,
    SpecMotor.ONLIMIT: DevState.ALARM,
}

SpecCounterState_2_TangoState = {
    SpecCounter.NOTINITIALIZED: DevState.UNKNOWN,
    SpecCounter.NOTCOUNTING: DevState.ON,
    SpecCounter.COUNTING: DevState.RUNNING,
}

SpecCounterType_2_str = {
    SpecCounter.UNKNOWN: 'Unknown',
    SpecCounter.SCALER: 'Scaler',
    SpecCounter.TIMER: 'Timer',
    SpecCounter.MONITOR: 'Monitor'
}

class _TangoWorker(threading.Thread):

    def __init__(self, **kwargs):
        kwargs['name'] = kwargs.pop('name', 'TangoWorker')
        daemon = kwargs.pop('daemon', True)
        threading.Thread.__init__(self, **kwargs)
        self.stop = False
        self.setDaemon(daemon)
        self.tasks = Queue.Queue()

    def run(self):
        tasks = self.tasks
        while not self.stop:
            try:
                f, args, kwargs = tasks.get(timeout=0.5)
            except Queue.Empty:
                continue
            try:
                f(*args, **kwargs)
            except:
                logging.warning("Failed to execute %s", str(f))
                logging.debug("Details:", exc_info=1)

    def execute(self, f, *args, **kwargs):
        self.tasks.put((f, args, kwargs))


__TANGO_WORKER = None
def TangoWorker():
    global __TANGO_WORKER
    if __TANGO_WORKER is None:
        __TANGO_WORKER = _TangoWorker()
        __TANGO_WORKER.start()
    return __TANGO_WORKER


def execute(f, *args, **kwargs):
    """Helper to execute a task in the tango worker thread"""
    return TangoWorker().execute(f, *args, **kwargs)


def switch_state(device, state=None, status=None):
    """Helper to switch state and/or status and send event"""
    if state is not None:
        device.set_state(state)
        execute(device.push_change_event, "state", state)
        if state in (DevState.ALARM, DevState.UNKNOWN, DevState.FAULT):
            msg = "State changed to " + str(state) 
            if status is not None:
                msg += ": " + status
            device.__log.error(msg)
    if status is not None:
        device.set_status(status)
        execute(device.push_change_event, "status", status)


def get_spec_names():
    util = Util.instance()
    tango_specs = util.get_device_list_by_class("Spec")
    if not tango_specs:
        return []
    return [ts.Spec for ts in tango_specs]


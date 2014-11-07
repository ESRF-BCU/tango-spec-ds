
Welcome to TangoSpec
====================

TangoSpec consists of a TANGO device server called *TangoSpec*. The device
server should contain at least one device of TANGO class *TangoSpec*.

All other devices (*SpecMotor*, *TangoSpecCounter*) can be created
dynamically on demand by executing commands on the *TangoSpec* device.

Start a server with::

    $ TangoSpec fourc

Run a python client::

    >>> import PyTango
    >>> fourc = PyTango.DeviceProxy("ID00/SPEC/fourc")
    
    >>> fourc.addMotor(["energy"])

    >>> energy = PyTango.DeviceProxy("energy")

    >>> energy.position
    0.123

    >>> print(energy.state())
    ON

    >>> fourc.AddVariable("FF_DIR")
    >>> import json
    >>> FF_DIR = json.loads(fourc.FF_DIR)
    >>> FF_DIR
    {u'config': u'/users/homer/Fourc/config',
     u'data': u'/users/homer/Fourc/data',
     u'sample': u'niquel'}

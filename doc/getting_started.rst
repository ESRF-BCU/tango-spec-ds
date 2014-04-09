
.. _tangospec_getting_started:

================
Getting started
================

TangoSpec consists of a TANGO_ device server called *TangoSpec*. The device
server should contain at least one device of TANGO_ class *TangoSpec*.

All other devices (*TangoSpecMotor*, *TangoSpecCounter*) can be created
dynamically on demand by executing commands on the *TangoSpec* device.

This chapter describes how to install, setup, run and customize a new *TangoSpec*
server.

.. _tangospec_download_install:

Download & install
------------------

ESRF Production environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For production environment, use the code from the bliss installer package
called *TangoSpec*.

Development environment
~~~~~~~~~~~~~~~~~~~~~~~

For development, you can get get the code from ESRF gitlab::

    $ git clone git@gitlab.esrf.fr:andy.gotz/tango-spec.git

.. _tangospec_setup: 

Setup a new TangoSpec server
----------------------------

Go to jive and select :menuselection:`Edit --> Create server`. You will
get a dialog like the one below:

.. image:: _static/images/jive_create_server.png
    :alt: Create TangoSpec server Jive dialog
    :align: center

The *Server* field should be ``TangoSpec/<instance>`` where instance is a name at
your choice (usually the name of the spec session).

The *Class* field should be ``TangoSpec``.

The *Devices* field should be the TANGO_ device name according to the convention
in place at the institute.

Press *Register server*.

Now go to the command line and type::

    $ TangoSpec fourc

(replace *fourc* with your server instance)

.. _tangospec_expose_motor:

Expose a motor
--------------

Each motor in SPEC_ can be represented as a TANGO_ device of TANGO_ class
*TangoSpecMotor*. 

When you setup a new *TangoSpec* device server it will not export any of the
SPEC_ motors. 

You have to specify which SPEC_ motors you want to be exported to SPEC.
To export a SPEC_ motor to spec just execute the TANGO_ command
:meth:`~TangoSpec.TangoSpec.AddMotor` on the *TangoSpec* device. 
This can be done in Jive or from a python shell::

    >>> import PyTango
    >>> fourc = PyTango.DeviceProxy("ID00/SPEC/fourc")
    >>> fourc.SpecMotorList
    energy
    ffsamy
    ffsamz
    istopy
    istopz

    >>> # creates a TangoSpecMotor called 'ID00/SPEC/energy' and with alias 'energy'
    >>>
    >>> fourc.addMotor(["energy"])
    >>> energy = PyTango.DeviceProxy("energy") # or  PyTango.DeviceProxy("ID00/SPEC/energy")

    >>> # creates a TangoSpecMotor called 'a/b/theta' and with alias 'theta'
    >>>
    >>> fourc.addMotor(["theta", "a/b/theta"])
    >>> theta = PyTango.DeviceProxy("theta") # or  PyTango.DeviceProxy("a/b/theta")

    >>> # creates a TangoSpecMotor called 'a/b/phi' and with alias 'spec_phi'
    >>> 
    >>> fourc.addMotor(["phi", "a/b/phi", "spec_phi"])
    >>> phi = PyTango.DeviceProxy("spec_phi") # or  PyTango.DeviceProxy("a/b/phi")

.. _tangospec_expose_variable:

Expose a variable
-----------------

SPEC_ variables can be exported to TANGO_ as dynamic attributes in the *TangoSpec*
device.

To expose an existing SPEC_ variable to TANGO_ just execute the TANGO_ command
 :meth:`~TangoSpec.TangoSpec.AddVariable` on the *TangoSpec* device.

As a result, a new attribute with the same name as the SPEC_ variable name will
be created in the *TangoSpec* device.

Example how to expose a SPEC_ variable called *FF_DIR*::

    >>> import PyTango
    >>> fourc = PyTango.DeviceProxy("ID00/SPEC/Fourc")

    >>> # expose a variable called 'FF_DIR'
    >>> fourc.AddVariable("FF_DIR")

.. _tangospec_readwrite_variable:

Read/Write variables
--------------------

The new TANGO_ attribute will a read-write scalar string.
In order to be able to represent proper data types the string is encoded in
:mod:`json` format. In order to read the value of a SPEC_ variable you must
first decode it from :mod:`json`. Fortunately, :mod:`json` is a well known
format. Example how to read the value of a previously exposed (see chapter above)
SPEC_ variable called *FF_DIR* (the variable is an associative array)::

    >>> import json
    >>> FF_DIR = json.loads(fourc.FF_DIR)
    >>> FF_DIR
    {u'config': u'/users/homer/Fourc/config',
     u'data': u'/users/homer/Fourc/data',
     u'sample': u'niquel'}
 
    >>> type(FF_DIR)
    dict

Notice that the value of FF_DIR is **not** a string but an actual dictionary.

To write a new value into a SPEC_ variable the opposite operation needs to be
performed. Example::

    >>> FF_DIR = dict(config="/tmp/config", data="/tmp/data", sample="copper")
    >>> fourc.FF_DIR = json.dumps(FF_DIR)

.. _tangospec_run_macro:

Run a macro
-----------

To run a macro use the :meth:`~TangoSpec.TangoSpec.ExecuteCmd` command. Example::

   >>> fourc.ExecuteCmd("wa")

(nothing will be shown because you are not listening to SPEC_ output. See
:ref:`tangospec_output`)

*Quick* macros can be ran using this synchronous method. Macros that take a
long time (ex: ascan) will block the client and eventually a timeout exception
will be raised (default timeout is 3s).

To run long macros there are two options:

Run macro asynchronously
~~~~~~~~~~~~~~~~~~~~~~~~

Tell the TANGO_ server to start executing the macro asynchronously allowing
you to do other stuff while the macro is running. For this use the command
:meth:`~TangoSpec.TangoSpec.ExecuteCmdA`.

If you are interested you can monitor if the macro as finished 
(:meth:`~TangoSpec.TangoSpec.IsReplyArrived` command) and optionaly
get the result of it's execution (:meth:`~TangoSpec.TangoSpec.GetReply`).
Example ::

   >>> ascan_id = fourc.ExecuteCmd("ascan phi 0 90 100 1.0")
   >>> # do my stuff while the ascan is running...
   
   >>> while not fourc.IsReplyArrived(ascan_id):
   ...     # do more stuff

   >>> ascan_result = fourc.GetReply(ascan_id)

.. note::
     :meth:`~TangoSpec.TangoSpec.GetReply` will block until the command 
     finishes.

Run macro synchronously
~~~~~~~~~~~~~~~~~~~~~~~~

If you want to be blocked until the macro finishes:
First, configure the DeviceProxy timeout to a long time and then execute
the macro using the :meth:`~TangoSpec.TangoSpec.ExecuteCmd` command::

    >>> fourc.set_timeout_millis(1000*60*60*24*7) # a week
    >>> ascan_result = fourc.ExecuteCmd("ascan phi 0 90 100 1.0")

Just make sure the ascan takes less than a week ;-)

.. _tangospec_move_motor:

Move a motor
------------

.. todo:: write Move a motor chapter

.. _tangospec_output:

Listen to output
----------------

.. todo:: write list to output chapter

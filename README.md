% TangoSpec Documentation
% TangoSpec development team
% November 07, 2014

[index::doc]

TangoSpec is a [TANGO](http://www.tango-controls.org/) device server
which provides a [TANGO](http://www.tango-controls.org/) interface to
[SPEC](http://www.certif.com/).

Contents:

Getting started
===============

[getting~s~tarted:tangospec-getting-started][getting~s~tarted:getting-started][getting~s~tarted::doc][getting~s~tarted:welcome-to-tangospec-s-documentation]
TangoSpec consists of a [TANGO](http://www.tango-controls.org/) device
server called *TangoSpec*. The device server should contain at least one
device of [TANGO](http://www.tango-controls.org/) class *TangoSpec*.

All other devices (*SpecMotor*, *SpecCounter*) can be created
dynamically on demand by executing commands on the *TangoSpec* device.

This chapter describes how to install, setup, run and customize a new
*TangoSpec* server.

Download & install
------------------

[getting~s~tarted:download-install][getting~s~tarted:tangospec-download-install]

### ESRF Production environment

[getting~s~tarted:esrf-production-environment] For production
environment, use the code from the bliss installer package called
*TangoSpec*.

### Development environment

[getting~s~tarted:development-environment] For development, you can get
get the code from ESRF gitlab:

    \$ git clone git@gitlab.esrf.fr:andy.gotz/tango-spec.git

Setup a new TangoSpec server
----------------------------

[getting~s~tarted:tangospec-setup][getting~s~tarted:setup-a-new-tangospec-server]
Go to jive and select *Edit $\rightarrow$ Create server*. You will get a
dialog like the one below:

![image](jive_create_server.png)

The *Server* field should be where instance is a name at your choice
(usually the name of the spec session, ex: TangoSpec/fourc).

The *Class* field should be .

The *Devices* field should be the
[TANGO](http://www.tango-controls.org/) device name according to the
convention in place at the institute (ex: ID00/spec/fourc).

Press *Register server*.

Select the Server tab, go to node TangoSpec/\<instance\>/Spec/\<device
name\>/properties. Add a new property called *Spec* by clicking the *New
property* button. Set the *Spec* property value to the spec session name
(example: machine01:fourc).

Optional:
:   By default, Spec server will start with auto discovery deactivated.
    This means that motors and counters will **not** be automatically
    added. You can changed this behavior by setting a new property
    called *AutoDiscovery* and setting it to (See )

Now go to the command line and type (replace *fourc* with your server
instance):

    \$ TangoSpec fourc

Auto discovery
--------------

[getting~s~tarted:tangospec-auto-discovery][getting~s~tarted:auto-discovery]
TangoSpec server can run with auto discovery enabled or disabled.

When auto discovery is enabled, every time the TangoSpec server starts
it will synchronize the list of motors and counters with the list
provided by spec. All motors and counters from spec will be
automatically exposed as TANGO devices.

When auto discovery is disabled, tango motors and counters must be
created manually (see and ).

Auto discovery is disabled by default unless you set the property of the
Spec device has been set to .

note

Note:

When a Spec TANGO server is running, to switch auto discovery mode, you
need to change the value of the **and** execute the command on the Spec
TANGO device to allow changes to take place.

Spec session reconstruction
---------------------------

[getting~s~tarted:spec-session-reconstruction] It is possible to
synchronize the list of TANGO spec motors and counters with the list of
motors and counters provided by Spec. To do this, simply execute the
command provided by the Spec TANGO device server. After executing this
command all motors and counters exported by Spec will be present as
TANGO devices. Example:

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{k+kn}{import} \PYG{n+nn}{PyTango}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ID00/SPEC/fourc}\PYG{l+s}{"}\PYG{p}{)}

    \PYG{g+go}{\PYGZsh{} tells you the list of existing spec motors}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{SpecMotorList}
    \PYG{g+go}{['energy', 'ffsamy', 'ffsamz', 'istopy', 'istopz']}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{c}{\PYGZsh{} tells you which spec motors are exposed as tango motors}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{MotorList}
    \PYG{g+go}{[]}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{Reconstruct}\PYG{p}{(}\PYG{p}{)}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{MotorList}
    \PYG{g+go}{['energy (ID00/Spec/energy)',}
    \PYG{g+go}{ 'ffsamy (ID00/Spec/ffsamy)',}
    \PYG{g+go}{ 'ffsamz (ID00/Spec/ffsamz)',}
    \PYG{g+go}{ 'istopy (ID00/Spec/istopy)',}
    \PYG{g+go}{ 'istopz (ID00/Spec/istopz)']}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{c}{\PYGZsh{} now there is a Tango device of class SpecMotor for each motor in the spec session:}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{energy} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ID00/SPEC/enery}\PYG{l+s}{"}\PYG{p}{)}

Expose a motor
--------------

[getting~s~tarted:expose-a-motor][getting~s~tarted:tangospec-expose-motor]
Each motor in [SPEC](http://www.certif.com/) can be represented as a
[TANGO](http://www.tango-controls.org/) device of
[TANGO](http://www.tango-controls.org/) class *SpecMotor*.

When you setup a new *TangoSpec* device server it will not export any of
the [SPEC](http://www.certif.com/) motors (unless : ref:*auto discovery
\<tangospec\_auto\_discovery\>*.

You have to specify which [SPEC](http://www.certif.com/) motors you want
to be exported to SPEC. To export a [SPEC](http://www.certif.com/) motor
to spec just execute the [TANGO](http://www.tango-controls.org/) command
on the *TangoSpec* device. This can be done in Jive or from a python
shell:

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{k+kn}{import} \PYG{n+nn}{PyTango}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ID00/SPEC/fourc}\PYG{l+s}{"}\PYG{p}{)}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{SpecMotorList}
    \PYG{g+go}{energy}
    \PYG{g+go}{ffsamy}
    \PYG{g+go}{ffsamz}
    \PYG{g+go}{istopy}
    \PYG{g+go}{istopz}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{c}{\PYGZsh{} creates a SpecMotor called 'ID00/SPEC/energy' and with alias 'energy'}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{addMotor}\PYG{p}{(}\PYG{p}{[}\PYG{l+s}{"}\PYG{l+s}{energy}\PYG{l+s}{"}\PYG{p}{]}\PYG{p}{)}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{energy} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{energy}\PYG{l+s}{"}\PYG{p}{)} \PYG{c}{\PYGZsh{} or  PyTango.DeviceProxy("ID00/SPEC/energy")}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{c}{\PYGZsh{} creates a SpecMotor called 'a/b/ffsamy' and with alias 'ffsamy'}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{addMotor}\PYG{p}{(}\PYG{p}{[}\PYG{l+s}{"}\PYG{l+s}{theta}\PYG{l+s}{"}\PYG{p}{,} \PYG{l+s}{"}\PYG{l+s}{a/b/ffsamy}\PYG{l+s}{"}\PYG{p}{]}\PYG{p}{)}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{theta} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ffsamy}\PYG{l+s}{"}\PYG{p}{)} \PYG{c}{\PYGZsh{} or  PyTango.DeviceProxy("a/b/ffsamy")}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{c}{\PYGZsh{} creates a SpecMotor called 'a/b/istopy' and with alias 'spec\PYGZus{}istopy'}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{addMotor}\PYG{p}{(}\PYG{p}{[}\PYG{l+s}{"}\PYG{l+s}{istopy}\PYG{l+s}{"}\PYG{p}{,} \PYG{l+s}{"}\PYG{l+s}{a/b/istopy}\PYG{l+s}{"}\PYG{p}{,} \PYG{l+s}{"}\PYG{l+s}{spec\PYGZus{}istopy}\PYG{l+s}{"}\PYG{p}{]}\PYG{p}{)}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{phi} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{spec\PYGZus{}istopy}\PYG{l+s}{"}\PYG{p}{)} \PYG{c}{\PYGZsh{} or  PyTango.DeviceProxy("a/b/istopy")}

Expose a counter
----------------

[getting~s~tarted:tangospec-expose-counter][getting~s~tarted:expose-a-counter]
Each counter in [SPEC](http://www.certif.com/) can be represented as a
[TANGO](http://www.tango-controls.org/) device of
[TANGO](http://www.tango-controls.org/) class *SpecCounter*.

When you setup a new *TangoSpec* device server it will not export any of
the [SPEC](http://www.certif.com/) counters.

You have to specify which [SPEC](http://www.certif.com/) counters you
want to be exported to SPEC. To export a [SPEC](http://www.certif.com/)
counter to spec just execute the [TANGO](http://www.tango-controls.org/)
command on the *TangoSpec* device. This can be done in Jive or from a
python shell:

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{k+kn}{import} \PYG{n+nn}{PyTango}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ID00/SPEC/fourc}\PYG{l+s}{"}\PYG{p}{)}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{SpecCounterList}
    \PYG{g+go}{sec}
    \PYG{g+go}{mon}
    \PYG{g+go}{det}
    \PYG{g+go}{c1}
    \PYG{g+go}{c2}
    \PYG{g+go}{c3}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{c}{\PYGZsh{} creates a SpecCounter called 'ID00/SPEC/sec' and with alias 'sec'}
    \PYG{g+go}{\PYGZgt{}\PYGZgt{}\PYGZgt{}}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{addCounter}\PYG{p}{(}\PYG{p}{[}\PYG{l+s}{"}\PYG{l+s}{sec}\PYG{l+s}{"}\PYG{p}{]}\PYG{p}{)}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{sec} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{sec}\PYG{l+s}{"}\PYG{p}{)} \PYG{c}{\PYGZsh{} or  PyTango.DeviceProxy("ID00/SPEC/sec")}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{c}{\PYGZsh{} creates a SpecCounter called 'a/b/sec' and with alias 'sec'}
    \PYG{g+go}{\PYGZgt{}\PYGZgt{}\PYGZgt{}}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{addCounter}\PYG{p}{(}\PYG{p}{[}\PYG{l+s}{"}\PYG{l+s}{sec}\PYG{l+s}{"}\PYG{p}{,} \PYG{l+s}{"}\PYG{l+s}{a/b/sec}\PYG{l+s}{"}\PYG{p}{]}\PYG{p}{)}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{theta} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{sec}\PYG{l+s}{"}\PYG{p}{)} \PYG{c}{\PYGZsh{} or  PyTango.DeviceProxy("a/b/sec")}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{c}{\PYGZsh{} creates a SpecCounter called 'a/b/det' and with alias 'spec\PYGZus{}det'}
    \PYG{g+go}{\PYGZgt{}\PYGZgt{}\PYGZgt{}}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{addCounter}\PYG{p}{(}\PYG{p}{[}\PYG{l+s}{"}\PYG{l+s}{det}\PYG{l+s}{"}\PYG{p}{,} \PYG{l+s}{"}\PYG{l+s}{a/b/det}\PYG{l+s}{"}\PYG{p}{,} \PYG{l+s}{"}\PYG{l+s}{spec\PYGZus{}det}\PYG{l+s}{"}\PYG{p}{]}\PYG{p}{)}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{phi} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{specdet}\PYG{l+s}{"}\PYG{p}{)} \PYG{c}{\PYGZsh{} or  PyTango.DeviceProxy("a/b/det")}

Expose a variable
-----------------

[getting~s~tarted:tangospec-expose-variable][getting~s~tarted:expose-a-variable]
[SPEC](http://www.certif.com/) variables can be exported to
[TANGO](http://www.tango-controls.org/) as dynamic attributes in the
*TangoSpec* device.

To expose an existing [SPEC](http://www.certif.com/) variable to [TANGO](http://www.tango-controls.org/) just execute the [TANGO](http://www.tango-controls.org/) command
:   on the *TangoSpec* device.

As a result, a new attribute with the same name as the
[SPEC](http://www.certif.com/) variable name will be created in the
*TangoSpec* device.

Example how to expose a [SPEC](http://www.certif.com/) variable called
*FF\_DIR*:

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{k+kn}{import} \PYG{n+nn}{PyTango}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ID00/SPEC/Fourc}\PYG{l+s}{"}\PYG{p}{)}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{c}{\PYGZsh{} expose a variable called 'FF\PYGZus{}DIR'}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{AddVariable}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{FF\PYGZus{}DIR}\PYG{l+s}{"}\PYG{p}{)}

Read/Write variables
--------------------

[getting~s~tarted:tangospec-readwrite-variable][getting~s~tarted:read-write-variables]
The new [TANGO](http://www.tango-controls.org/) attribute will a
read-write scalar string. In order to be able to represent proper data
types the string is encoded in
[](http://docs.python.org/library/json.html#module-json) format. In
order to read the value of a [SPEC](http://www.certif.com/) variable you
must first decode it from
[](http://docs.python.org/library/json.html#module-json). Fortunately,
[](http://docs.python.org/library/json.html#module-json) is a well known
format. Example how to read the value of a previously exposed (see
chapter above) [SPEC](http://www.certif.com/) variable called *FF\_DIR*
(the variable is an associative array):

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{k+kn}{import} \PYG{n+nn}{json}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{FF\PYGZus{}DIR} \PYG{o}{=} \PYG{n}{json}\PYG{o}{.}\PYG{n}{loads}\PYG{p}{(}\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{FF\PYGZus{}DIR}\PYG{p}{)}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{FF\PYGZus{}DIR}
    \PYG{g+go}{\PYGZob{}u'config': u'/users/homer/Fourc/config',}
    \PYG{g+go}{ u'data': u'/users/homer/Fourc/data',}
    \PYG{g+go}{ u'sample': u'niquel'\PYGZcb{}}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n+nb}{type}\PYG{p}{(}\PYG{n}{FF\PYGZus{}DIR}\PYG{p}{)}
    \PYG{g+go}{dict}

Notice that the value of FF\_DIR is **not** a string but an actual
dictionary.

To write a new value into a [SPEC](http://www.certif.com/) variable the
opposite operation needs to be performed. Example:

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{FF\PYGZus{}DIR} \PYG{o}{=} \PYG{n+nb}{dict}\PYG{p}{(}\PYG{n}{config}\PYG{o}{=}\PYG{l+s}{"}\PYG{l+s}{/tmp/config}\PYG{l+s}{"}\PYG{p}{,} \PYG{n}{data}\PYG{o}{=}\PYG{l+s}{"}\PYG{l+s}{/tmp/data}\PYG{l+s}{"}\PYG{p}{,} \PYG{n}{sample}\PYG{o}{=}\PYG{l+s}{"}\PYG{l+s}{copper}\PYG{l+s}{"}\PYG{p}{)}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{FF\PYGZus{}DIR} \PYG{o}{=} \PYG{n}{json}\PYG{o}{.}\PYG{n}{dumps}\PYG{p}{(}\PYG{n}{FF\PYGZus{}DIR}\PYG{p}{)}

Run a macro
-----------

[getting~s~tarted:run-a-macro][getting~s~tarted:tangospec-run-macro] To
run a macro use the command. Example:

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{ExecuteCmd}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{wa}\PYG{l+s}{"}\PYG{p}{)}

(nothing will be shown because you are not listening to
[SPEC](http://www.certif.com/) output. See )

*Quick* macros can be ran using this synchronous method. Macros that
take a long time (ex: ascan) will block the client and eventually a
timeout exception will be raised (default timeout is 3s).

To run long macros there are two options:

### Run macro asynchronously

[getting~s~tarted:run-macro-asynchronously] Tell the
[TANGO](http://www.tango-controls.org/) server to start executing the
macro asynchronously allowing you to do other stuff while the macro is
running. For this use the command .

If you are interested you can monitor if the macro as finished (
command) and optionaly get the result of it’s execution (). Example

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{ascan\PYGZus{}id} \PYG{o}{=} \PYG{n}{fourc}\PYG{o}{.}\PYG{n}{ExecuteCmd}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ascan phi 0 90 100 1.0}\PYG{l+s}{"}\PYG{p}{)}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{c}{\PYGZsh{} do my stuff while the ascan is running...}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{k}{while} \PYG{o+ow}{not} \PYG{n}{fourc}\PYG{o}{.}\PYG{n}{IsReplyArrived}\PYG{p}{(}\PYG{n}{ascan\PYGZus{}id}\PYG{p}{)}\PYG{p}{:}
    \PYG{g+gp}{... }    \PYG{c}{\PYGZsh{} do more stuff}

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{ascan\PYGZus{}result} \PYG{o}{=} \PYG{n}{fourc}\PYG{o}{.}\PYG{n}{GetReply}\PYG{p}{(}\PYG{n}{ascan\PYGZus{}id}\PYG{p}{)}

note

Note:

will block until the command finishes.

### Run macro synchronously

[getting~s~tarted:run-macro-synchronously] If you want to be blocked
until the macro finishes: First, configure the DeviceProxy timeout to a
long time and then execute the macro using the command:

    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{fourc}\PYG{o}{.}\PYG{n}{set\PYGZus{}timeout\PYGZus{}millis}\PYG{p}{(}\PYG{l+m+mi}{1000}\PYG{o}{*}\PYG{l+m+mi}{60}\PYG{o}{*}\PYG{l+m+mi}{60}\PYG{o}{*}\PYG{l+m+mi}{24}\PYG{o}{*}\PYG{l+m+mi}{7}\PYG{p}{)} \PYG{c}{\PYGZsh{} a week}
    \PYG{g+gp}{\PYGZgt{}\PYGZgt{}\PYGZgt{} }\PYG{n}{ascan\PYGZus{}result} \PYG{o}{=} \PYG{n}{fourc}\PYG{o}{.}\PYG{n}{ExecuteCmd}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ascan phi 0 90 100 1.0}\PYG{l+s}{"}\PYG{p}{)}

Just make sure the ascan takes less than a week ;-)

Move a motor
------------

[getting~s~tarted:tangospec-move-motor][getting~s~tarted:move-a-motor]

note

Todo

write Move a motor chapter

Listen to output
----------------

[getting~s~tarted:tangospec-output][getting~s~tarted:listen-to-output]

note

Todo

write list to output chapter

TangoSpec API
=============

[api:tangospec-api][api::doc][api:pypi][api:module-TangoSpec] A
[TANGO](http://www.tango-controls.org/) device server which provides a
[TANGO](http://www.tango-controls.org/) interface to
[SPEC](http://www.certif.com/).

[api:TangoSpec.run] Runs the Spec device server

[api:TangoSpec.Spec] Bases:

A [TANGO](http://www.tango-controls.org/) device server for
[SPEC](http://www.certif.com/) based on SpecClient.

[api:TangoSpec.Spec.SpecMotorList] Attribute containning the list of all
[SPEC](http://www.certif.com/) motors

[api:TangoSpec.Spec.SpecCounterList] Attribute containning the list of
all [SPEC](http://www.certif.com/) counters

[api:TangoSpec.Spec.MotorList] Attribute containning the list of
[SPEC](http://www.certif.com/) motors exported to
[TANGO](http://www.tango-controls.org/)

[api:TangoSpec.Spec.CounterList] Attribute containning the list of
[SPEC](http://www.certif.com/) counters exported to
[TANGO](http://www.tango-controls.org/)

[api:TangoSpec.Spec.VariableList] Attribute containning the list of
[SPEC](http://www.certif.com/) variables exported to
[TANGO](http://www.tango-controls.org/)

[api:TangoSpec.Spec.Output] Attribute which reports
[SPEC](http://www.certif.com/) console output (output/tty variable)

[api:TangoSpec.Spec.ExecuteCmd] Execute a [SPEC](http://www.certif.com/)
command synchronously. Use instead if you intend to run commands that
take some time.

> Parameters
> :   **command**
>     ([*str*](http://docs.python.org/library/functions.html#str)) – the
>     command to be executed (ex: )
>
[api:TangoSpec.Spec.ExecuteCmdA] Execute a
[SPEC](http://www.certif.com/) command asynchronously.

> Parameters
> :   **command**
>     ([*str*](http://docs.python.org/library/functions.html#str)) – the
>     command to be executed (ex: )
>
> Returns
> :   an identifier for the command.
>
> Return type
> :   int
>
[api:TangoSpec.Spec.GetReply] Returns the reply of the
[SPEC](http://www.certif.com/) command given by the cmd\_id, previously
requested through . It waits if the command is not finished

> Parameters
> :   **cmd\_id**
>     ([*int*](http://docs.python.org/library/functions.html#int)) –
>     command identifier
>
> Returns
> :   the reply for the requested command
>
> Return type
> :   str
>
[api:TangoSpec.Spec.IsReplyArrived] Determines if a command executed
previously with the given cmd\_id is finished.

> Parameters
> :   **cmd\_id**
>     ([*int*](http://docs.python.org/library/functions.html#int)) –
>     command identifier
>
> Returns
> :   True if the command response as arrived or False otherwise
>
> Return type
> :   bool
>
[api:TangoSpec.Spec.AddVariable] Export a [SPEC](http://www.certif.com/)
variable to Tango by adding a new attribute to this device with the same
name as the variable.

> Parameters
> :   **variable\_name**
>     ([*str*](http://docs.python.org/library/functions.html#str)) –
>     [SPEC](http://www.certif.com/) variable name to be exported as a
>     [TANGO](http://www.tango-controls.org/) attribute
>
> Throws PyTango.DevFailed
> :   If the variable is already exposed in this
>     [TANGO](http://www.tango-controls.org/) DS.
>
[api:TangoSpec.Spec.RemoveVariable] Unexposes the given variable from
this [TANGO](http://www.tango-controls.org/) DS.

> Parameters
> :   **variable\_name**
>     ([*str*](http://docs.python.org/library/functions.html#str)) – the
>     name of the [SPEC](http://www.certif.com/) variable to be removed
>
> Throws PyTango.DevFailed
> :   If the variable is not exposed in this
>     [TANGO](http://www.tango-controls.org/) DS
>
[api:TangoSpec.Spec.AddMotor] Adds a new SpecMotor to this DS.

*motor\_info* must be a sequence of strings with the following options:

    spec\_motor\_name [, tango\_device\_name [, tango\_alias\_name]]

Examples:

    \PYG{n}{spec} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ID00/spec/fourc}\PYG{l+s}{"}\PYG{p}{)}
    \PYG{n}{spec}\PYG{o}{.}\PYG{n}{AddMotor}\PYG{p}{(}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{th}\PYG{l+s}{"}\PYG{p}{,}\PYG{p}{)}\PYG{p}{)}
    \PYG{n}{spec}\PYG{o}{.}\PYG{n}{AddMotor}\PYG{p}{(}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{tth}\PYG{l+s}{"}\PYG{p}{,} \PYG{l+s}{"}\PYG{l+s}{ID00/fourc/tth}\PYG{l+s}{"}\PYG{p}{,} \PYG{l+s}{"}\PYG{l+s}{theta2}\PYG{l+s}{"}\PYG{p}{)}\PYG{p}{)}

> Parameters
> :   -   **spec\_motor\_name** – name of the spec motor to export to
>         [TANGO](http://www.tango-controls.org/)
>
>     -   **tango\_device\_name** – optional tango name to give to the
>         new [TANGO](http://www.tango-controls.org/) motor device
>         [default:
>         \<tangospec\_domain\>/\<tangospec\_family\>/\<spec\_motor\_name\>]
>
>     -   **tango\_alias\_name** – optional alias to give to the new
>         tango motor device [default: \<spec\_motor\_name\>]. Note: if
>         the alias exists it will **not** be overwritten.
>
> Throws PyTango.DevFailed
> :   If [SPEC](http://www.certif.com/) motor does not exist or if motor
>     is already exported
>
[api:TangoSpec.Spec.RemoveMotor] Removes the given SpecMotor from this
DS.

> Parameters
> :   **motor\_name**
>     ([*str*](http://docs.python.org/library/functions.html#str)) –
>     [SPEC](http://www.certif.com/) motor name to be removed
>
Examples:

    \PYG{n}{spec} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ID00/spec/fourc}\PYG{l+s}{"}\PYG{p}{)}
    \PYG{n}{spec}\PYG{o}{.}\PYG{n}{RemoveMotor}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{th}\PYG{l+s}{"}\PYG{p}{)}

[api:TangoSpec.Spec.AddCounter] Adds a new SpecCounter to this DS.

*counter\_info* must be a sequence of strings with the following
options:

    spec\_counter\_name [, tango\_device\_name [, tango\_alias\_name]]

Examples:

    \PYG{n}{spec} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ID00/spec/fourc}\PYG{l+s}{"}\PYG{p}{)}
    \PYG{n}{spec}\PYG{o}{.}\PYG{n}{AddCounter}\PYG{p}{(}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{sec}\PYG{l+s}{"}\PYG{p}{,}\PYG{p}{)}\PYG{p}{)}
    \PYG{n}{spec}\PYG{o}{.}\PYG{n}{AddCounter}\PYG{p}{(}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{det}\PYG{l+s}{"}\PYG{p}{,} \PYG{l+s}{"}\PYG{l+s}{ID00/fourc/detector}\PYG{l+s}{"}\PYG{p}{,} \PYG{l+s}{"}\PYG{l+s}{detector}\PYG{l+s}{"}\PYG{p}{)}\PYG{p}{)}

> Parameters
> :   -   **spec\_counter\_name** – name of the spec counter to export
>         to [TANGO](http://www.tango-controls.org/)
>
>     -   **tango\_device\_name** – optional tango name to give to the
>         new [TANGO](http://www.tango-controls.org/) counter device
>         [default:
>         \<tangospec\_domain\>/\<tangospec\_family\>/\<spec\_counter\_name\>]
>
>     -   **tango\_alias\_name** – optional alias to give to the new
>         tango counter device [default: \<spec\_counter\_name\>]. Note:
>         if the alias exists it will **not** be overwritten.
>
> Throws PyTango.DevFailed
> :   If [SPEC](http://www.certif.com/) counter does not exist or if
>     counter is already exported
>
[api:TangoSpec.Spec.RemoveCounter] Removes the given SpecCounter from
this DS.

> Parameters
> :   **counter\_name**
>     ([*str*](http://docs.python.org/library/functions.html#str)) –
>     [SPEC](http://www.certif.com/) counter name to be removed
>
Examples:

    \PYG{n}{spec} \PYG{o}{=} \PYG{n}{PyTango}\PYG{o}{.}\PYG{n}{DeviceProxy}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{ID00/spec/fourc}\PYG{l+s}{"}\PYG{p}{)}
    \PYG{n}{spec}\PYG{o}{.}\PYG{n}{RemoveCounter}\PYG{p}{(}\PYG{l+s}{"}\PYG{l+s}{th}\PYG{l+s}{"}\PYG{p}{)}

[api:TangoSpec.Spec.Reconstruct] Exposes to Tango all counters and
motors that where found in SPEC.

[api:TangoSpec.SpecMotor] Bases:

A TANGO SPEC motor device based on SpecClient.

[api:TangoSpec.SpecCounter] Bases:

A TANGO SPEC counter device based on SpecClient.

Indices and tables
==================

[index:indices-and-tables][index:pypi]

-   *genindex*

-   *modindex*

-   *search*

\#1

\#1

`TangoSpec`

,

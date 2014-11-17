
.. _tangospec_api:

=============
TangoSpec API
=============

.. automodule:: TangoSpec

.. autofunction:: TangoSpec.run

.. autoclass:: TangoSpec.Spec
 
   .. attribute:: Spec

      TANGO_ device property containing spec session name
      (examples: ``localhost:spec``, ``mach101:fourc``)

   .. attribute:: AutoDiscovery

      TANGO_ device property (bool) describing if auto discovery is
      enabled or disabled (see: :ref:`tangospec_auto_discovery`). Default
      value is ``False``.
      
   .. attribute:: OutputBufferMaxLength

      TANGO_ device property (int) describing the output history buffer
      maximum length (in number of output lines). Default is 1000 lines.

   .. attribute:: SpecMotorList

      TANGO_ attribute containning the list of all SPEC_ motors

   .. attribute:: SpecCounterList

      TANGO_ attribute containning the list of all SPEC_ counters

   .. attribute:: MotorList

      TANGO_ attribute containning the list of SPEC_ motors exported to TANGO_
   
   .. attribute:: CounterList

      TANGO_ attribute containning the list of SPEC_ counters exported to TANGO_

   .. attribute:: VariableList

      TANGO_ attribute containning the list of SPEC_ variables exported to TANGO_

   .. attribute:: Output

      TANGO_ attribute which reports SPEC_ console output (output/tty variable)


.. autoclass:: TangoSpec.SpecMotor

   .. attribute:: SpecMotor

      TANGO_ device property containing the spec motor mnemonic
      (examples: ``th``, ``localhost:spec::chi``, ``mach101:fourc::phi``).
      The full name is only required if running the TangoSpec DS without a Spec
      manager device.

   .. attribute:: Position

   TANGO_ attribute for the motor user position. Setting a value on this
   attribute will move the motor to the specified value.

   .. attribute:: State

   TANGO_ attribute for the motor state.

   * INIT - motor initialization phase (startup or through Init command)
   * ON - motor is enabled and stopped.
   * MOVING - motor is moving 
   * ALARM - motor limit switch is active or position in the alarm range
   * FAULT - connection to SPEC_ motor lost

   .. attribute:: Status

   TANGO_ attribute for the motor status.

   .. attribute:: DialPosition

   TANGO_ attribute for the motor dial position.

   .. attribute:: Sign

   TANGO_ attribute for the motor sign.

   .. attribute:: Offset

   TANGO_ attribute for the motor offset.

   .. attribute:: AcceletationTime

   TANGO_ attribute for the motor acceleration time (s).

   .. attribute:: Backlash

   TANGO_ attribute for the motor backlash.

   .. attribute:: StepSize

   TANGO_ attribute for the current step size
   (used by the StepDown and StepUp commands).

   .. attribute:: Limit_Switches

   TANGO_ attribute for the motor limit switches (home, upper, lower).

   .. method:: Init

   Initializes the TANGO_ motor


.. autoclass:: TangoSpec.SpecCounter

   .. attribute:: SpecCounter

      TANGO_ device property containing the spec counter mnemonic
      (examples: ``sec``, ``localhost:spec::det``, ``mach101:fourc::mon``).
      The full name is only required if running the TangoSpec DS without a Spec
      manager device.

   .. attribute:: State

   TANGO_ attribute for the counter state.

   * INIT - counter initialization phase (startup or through Init command)
   * ON - counter is enabled and stopped.
   * RUNNIG - counter is counting 
   * ALARM - counter value in the alarm range
   * FAULT - connection to SPEC_ counter lost

   .. attribute:: Status

   TANGO_ attribute for the counter status.

   .. attribute:: Value

   TANGO_ attribute for the counter value.

   .. method:: Init

   Initializes the TANGO_ counter


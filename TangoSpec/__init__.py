# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
# This file is part of the Tango SPEC device server
#
# Copyright (c) 2014, European Synchrotron Radiation Facility.
# Distributed under the GNU Lesser General Public License.
# See LICENSE.txt for more info.
#------------------------------------------------------------------------------

"""A TANGO_ device server which provides a TANGO interface to SPEC."""

import datetime
__this_year = datetime.date.today().year
del datetime

__project__ = 'TangoSpec'
__version_info__ = (1, 0, 0, 'final', 0)
__version__ = "{0[0]}.{0[1]}.{0[2]}".format(__version_info__)
__authors__ = ['Andy Gotz', 'Tiago Coutinho', 'Matias Guijarro']
__author__ = __authors__[0]
__copyright__ = '{0}, European Synchrotron Radiation Facility'.format(__this_year)
__description__ = __doc__



from .TangoSpec import TangoSpec, run
from .TangoSpecMotor import TangoSpecMotor
from .TangoSpecCounter import TangoSpecCounter

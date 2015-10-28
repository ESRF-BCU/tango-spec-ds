# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
# This file is part of the Tango SPEC device server
#
# Copyright (c) 2014, European Synchrotron Radiation Facility.
# Distributed under the GNU Lesser General Public License.
# See LICENSE.txt for more info.
#------------------------------------------------------------------------------

"""A TANGO_ device server which provides a TANGO_ interface to SPEC_."""

import datetime
__this_year = datetime.date.today().year
del datetime

__project__ = 'TangoSpec'
__version_info__ = (2, 2, 0, 'final', 0)
__version__ = "{0[0]}.{0[1]}.{0[2]}".format(__version_info__)
__authors__ = ['Tiago Coutinho', 'Matias Guijarro', 'Andy Gotz']
__author__ = __authors__[0]
__copyright__ = '{0}, European Synchrotron Radiation Facility'.format(__this_year)
__description__ = __doc__

from .Spec import Spec, run
from .SpecMotor import SpecMotor
from .SpecCounter import SpecCounter

# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
# This file is part of the Tango SPEC device server
#
# Copyright (c) 2014, European Synchrotron Radiation Facility.
# Distributed under the GNU Lesser General Public License.
# See LICENSE.txt for more info.
#------------------------------------------------------------------------------

import os
import sys
from distutils.core import setup


def main():
    cmdclass = {}
    try:
        from sphinx.setup_command import BuildDoc
        cmdclass['build_doc'] = BuildDoc
    except ImportError:
        pass
    
    sys.path.insert(0, os.path.dirname(__file__))

    import TangoSpec

    setup(name=TangoSpec.__project__,
          version=TangoSpec.__version__,
          description=TangoSpec.__description__,
          author=TangoSpec.__author__,
          packages=['TangoSpec'],
          url="http://www.tango-controls.org",
          cmdclass=cmdclass,
        )


if __name__ == "__main__":
    main()

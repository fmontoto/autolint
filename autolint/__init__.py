#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .autolint import __conf_file__

__author__ = "Francisco Montoto"
__copyright__ = "Copyright © 2016 Francisco Montoto"
__created__ = "2016-07-13"
__email__ = "fmontotomonroy@gmail.com"

__license__ = "MIT"
__project__ = "autolint"
__description__ = "Automated run of linter at your repository."
__url__ = "https://www.github.com/fmontoto/autolint"
__status__ = "Development"
__updated__ = "2016-07-13"
__version__ = "0.0.1"

__conf_file__ = __conf_file__
__entry_points__ = {'console_scripts': [
                        'autolint = autolint.autolint:main'
                    ]}

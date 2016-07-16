#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools
import autolint

with open('requirements.txt', 'r') as f:
    __dependencies__ = f.read().strip().split()

__extra_data__ = {'autolint': [autolint.__conf_file__]}
__long_description__ = "TODO"

__setup__ = {"name": autolint.__project__,
             "version": autolint.__version__,
             "author": autolint.__author__,
             "author_email": autolint.__email__,
             "url": autolint.__url__,
             "description": autolint.__description__,
             "long_description": __long_description__,
             "install_requires": __dependencies__,
             "packages": ['autolint'],
             "package_data": __extra_data__,
             "entry_points": autolint.__entry_points__
             }
setuptools.setup(**__setup__)

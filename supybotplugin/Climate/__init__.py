#!/usr/bin/env python
# coding=utf-8

"""
Get climate data from Wikipedia and formats it in a possibly IRC-friendly way.
"""

import supybot
import supybot.world as world

__version__ = "0.1"

__author__ = "jarek piórkowski"

__contributors__ = {}

__url__ = 'https://github.com/qviri/climate-graph'

import config
import plugin
reload(plugin) # In case we're being reloaded.
# Add more reloads here if you add third-party modules and want them to be
# reloaded when this plugin is reloaded.  Don't forget to import them as well!

if world.testing:
    import test

Class = plugin.Class
configure = config.configure


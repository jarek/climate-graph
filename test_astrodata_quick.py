#!/usr/bin/env python
# coding=utf-8

from __future__ import unicode_literals
import calendar
import time
import datetime
import ephem

import astrodata
import climate

if __name__ == '__main__':
    cities = climate.get_cities()
    
    data = {'r': [], 'e': []}
    for city in cities:
        time1 = time.time()
        for i in range(12):
            data['e'].append(astrodata.month_daylight(city, i+1, True).total_seconds() / 3600)
        print "exact: " + str(time.time() - time1)

        time2 = time.time()
        for i in range(12):
            data['r'].append(astrodata.month_daylight(city, i+1, False).total_seconds() / 3600)
        print "rough: " + str(time.time() - time2)

    for i in range(12):
        print str(i+1) + ' ',
        print str(round(data['e'][i], 2)) + '-' + str(round(data['r'][i], 2)),
        print ' = ' + str(round(data['e'][i] - data['r'][i], 3)),
        print '\t: ' + str(round(100 * (data['r'][i] - data['e'][i]) / data['e'][i], 2)) + '%'
        # TODO: graph the differences vs actual day lengths to see where 
        # i'm undershooting and try to understand why?
    

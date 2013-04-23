#!/usr/bin/env python
# coding=utf-8

from __future__ import unicode_literals
import calendar
import datetime
import ephem

import climate

# compute sun data once when file is loaded/imported
s = ephem.Sun()
s.compute()

def process_location(location):
    if not isinstance(location, ephem.Observer):
        if isinstance(location, list) and len(location) == 2:
            # interpret as a latlong pair passed in
            ll = location
            location = ephem.Observer()
            location.lat = str(ll[0])
            location.lon = str(ll[1])
        else:
            location = ephem.city(str(location))
            
    return location

def day_duration(location, date = False):
    # GLOBAL USED: s
    
    location = process_location(location)

    if date == False:
        location.date = datetime.datetime.today()
    else:
        location.date = date

    daylight = abs(location.next_setting(s, date) - 
        location.previous_rising(s, date))

    if daylight > 1:
        daylight -= 1

    return datetime.timedelta(daylight)
    
def month_daylight(location, month):
    # use a constant non-leap year. constant because it doesn't matter outside
    # of leap or non-leap, non-leap since I suspect any monthly numbers 
    # are given for non-leap Februarys
    year = 2013
    
    location = process_location(location)
    
    month_days = calendar.monthrange(year, month)[1]
    total_duration = datetime.timedelta(0)
    for i in range(month_days):
        day = datetime.date(year, month, i + 1)
        total_duration += day_duration(location, day)
        
    return total_duration

if __name__ == '__main__':
    cities = climate.get_cities()
    
    for city in cities:
        v = ephem.city(str(city))
        print 'day lengths in %s on first day of month, in hours:' % city
        
        for i in range(12):
            daylight = day_duration(v, datetime.date(2013, i+1, 1))
            daylight = daylight.total_seconds() / 3600
            print '%s %0.1f' % (climate.MONTHS[i], daylight)

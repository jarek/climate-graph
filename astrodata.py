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
            try:
                location = ephem.city(unicode(location))
            except:
                try:
                    location = get_location_from_wikipedia(unicode(location))
                except:
                    location = False

    return location

def get_location_from_wikipedia(name):
    data = climate.get_coordinates(name)

    location = ephem.Observer()
    # pyephem is a little weird, only works right when these are strings
    location.lat = str(data['lat'])
    location.lon = str(data['lng'])

    try:
        # on the other hand, elevation must be specified as a float
        location.elevation = float(data['elevation'])
    except:
        # ignore, might not have been specified, 
        # or might be in a format float or pyephem can't handle
        # e.g. Whitehorse uses "670&ndash;1702"
        pass

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
    
def month_daylight(location, month, exact = False):
    # Specify exact = True to request an exact measurement, that is,
    # duration of each day calculated individually then summed.
    # As calculating a day's data takes ephem a considerable amount of time, 
    # doing something like calculating exact daylight over the entire year
    # can take 1 or 2 seconds.
    # exact = False speeds this up by only checking between 3 and 8 days
    # during the month (depending on location's latitude - at locations closer
    # to equator, day lengths change less dramatically) and taking a mean of 
    # these. This is generally quite accurate, e.g., Helsinki monthly numbers 
    # are within 66 minutes / 0.6% throughout the year, and right at equator 
    # Singapore monthly numbers are always within 2 minutes / 0.0061%.
    # However, specify exact = True if you want to be sure.

    # TODO: this function currently fails for locations where there is at least
    # one day when the sun doesn't set at all. This is roughly 66° latitude
    # and up. Need to handle this somehow - perhaps catch the exception 
    # and return 24 hours?

    # use a constant non-leap year. constant because it doesn't matter outside
    # of leap or non-leap, non-leap since I suspect any monthly numbers 
    # are given for non-leap Februarys
    year = 2013
    
    location = process_location(location)
    
    month_days = calendar.monthrange(year, month)[1]

    total_duration = datetime.timedelta(0)

    if not exact:
        # TODO: maybe also use different day number multiplier 
        # for different months if I can find a consistent pattern
        # of which months are most frequently off
        
        skip_days = int(round(month_days / (5 * location.lat)))
        if skip_days > 13:
            skip_days = 13 # cap at 13 so that we always get at least 3 days

        days = range(1, month_days + 1, skip_days)

        # if the days list doesn't end on last day of month, shift all days
        # so that they're centred within the month
        adj = (month_days - days[-1])/2 
        if adj > 0:
            days[:] = [day + adj for day in days] 

        for day_of_month in days:
            day = datetime.date(year, month, day_of_month)
            total_duration += day_duration(location, day)

        total_duration = (total_duration / len(days)) * month_days
    else:
        for i in range(month_days):
            day = datetime.date(year, month, i+1)
            total_duration += day_duration(location, day)
        
    return total_duration

if __name__ == '__main__':
    cities = climate.get_cities()
    
    for city in cities:
        v = process_location(unicode(city))
        print 'day lengths in %s on first day of month, in hours:' % city
        
        for i in range(12):
            daylight = day_duration(v, datetime.date(2013, i+1, 1))
            daylight = daylight.total_seconds() / 3600
            print '%s %0.1f' % (climate.MONTHS[i], daylight)

        print
        print 'total day lengths in %s per month, in hours,' % city
        print 'calculated exactly and inexactly, and the error'

        for i in range(12):
            exact = month_daylight(v, i+1, exact = True).total_seconds() / 3600
            inexact = month_daylight(v, i+1, exact = False).total_seconds() / 3600

            print '%s %0.2f %0.2f %0.2f %f%%' % (climate.MONTHS[i], \
                exact, inexact, abs(exact-inexact),\
                100*abs(exact-inexact)/inexact)


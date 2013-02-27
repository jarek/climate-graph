#!/usr/bin/env python
# coding=utf-8

from __future__ import unicode_literals
import unittest
import os
import time
from datetime import datetime
from datetime import timedelta

import climate
import cache

class known_values(unittest.TestCase):
    def test_nonexistent_page(self):
        """nonexisting page should give corresponding error message"""

        data = climate.get_climate_data('Fakey Place, gdsngkjdsnk')

        self.assertEqual(data['page_error'], True)
        self.assertEqual(data['title'].endswith('location not found'), True)

    def test_redirect(self):
        """wikipedia redirects should be followed"""

        data = climate.get_climate_data('nyc')

        self.assertEqual(data['title'], 'New York City')

    def test_no_climate_data(self):
        """page with no climate data should return a default
        initialized-but-empty result set"""

        pagename = 'Elmira, Ontario'
        data = climate.get_climate_data(pagename)

        self.assertEqual(data['page_error'], False)
        self.assertEqual(data['title'], pagename)

        for row_name in climate.ROWS:
            self.assertEqual(len(data[row_name]), 0)

    def test_any_unicode(self):
        """arbitrary unicode should work in query"""

        pagenames = ['Reykjavík', 'Gdańsk', '香港', 'ᐃᓄᒃᑕᐅᑦ']

        for pagename in pagenames:
            data = climate.get_climate_data(pagename)

    def test_unicode_page_name(self):
        """Page that is accessible on Wikipedia via a Unicode name 
        should return correct climate info.
        Test with Jan high and Dec record low for Hong Kong (香港)"""

        data = climate.get_climate_data('香港')

        self.assertEqual(data['title'], 'Hong Kong')
        self.assertEqual(data['high C'][0], 18.6)
        self.assertEqual(data['record low C'][11], 4.3)

    def test_weatherbox_cached_template(self):
        """ Test a New York City-specific weatherbox use that invokes
        a pre-rendered {{New York City weatherbox/cached}} template.
        More information in a comment in 
        climate.get_climate_data.find_separate_weatherbox_template """
        
        data = climate.get_climate_data('New York City')

        self.assertEqual(data['record high C'][2], 30.0) # March
        self.assertEqual(data['low C'][10], 5.3) # November

    def test_unit_conversion(self):
        """ Test for correct conversion of units. Includes F->C and 
        inches to mm and cm. Based on data for Seattle and NYC. """

        known_data = {
            'New York City': {
                'precipitation mm': {5: 112, 10: 102.1}, # jun, nov
                'snow cm': {0: 20.3, 5: 0, 11: 12.2} #jan, jun, dec
            },
            'Seattle': {
                'high C': {3: 14.5}, #april
                'record low C': {1: -17.2, 7: 6.7}, #feb, aug
                'precipitation mm': {0: 141.2, 6: 17.8}, #jan, jul
                'snow cm': {1: 3.6, 11: 3.8, 5: 0} # feb, dec, jun
            }
        }

        for city,data in known_data.items():
            actual_data = climate.get_climate_data(city)

            for key,key_data in data.items():
                for month,expected_value in key_data.items():
                    self.assertEqual(actual_data[key][month], expected_value)

    def test_known_data(self):
        """Test for correct retrieval of some data for some cities.
        Test against known-correct values retrieved via browser at time
        of test authoring.
        Basically make sure future changes don't mess up known-working
        queries."""

        known_data = {
            'Vancouver': {
                'record high C': {6: 31.7}, #july
                'mean C': {9: 11.1}, #october
                'precipitation mm': {7: 50.8} #august
            },
            'Seattle': {
                # temperatures here also test conversion into C
                'high C': {3: 14.5}, #april
                'record low C': {1: -17.2, 7: 6.7}, #feb, aug
                'precipitation days': {10: 18.4}, #november
                'sun': {7: 248} #august
            },
            'Calgary': {
                'snow cm': {2: 21.9}, #march
                'sun': {6: 314.9}, #july
                'mean C': {4: 9.8}, #may
                'low C': {10: -8.9}, #november
                'record low C': {1: -45} #february
            },
            'Melbourne': {
                'record high C': {1: 46.4}, #february
                'record low C': {6: -2.8}, #july
                'sun': {5: 108}, #june
            },
            'Toronto': {
                'mean C': {6: 22.2}, #july
                'snow days': {0: 12.0, 4: 0}, #january, may
                'record low C': {11: -30}, #december
                'rain mm': {7: 79.6}, #august
                'sun': {4: 229.1} #may
            },
            # for Sydney, test conversion from daily sun hours, as
            # specified on wiki page, into monthly hours, as used
            # elsewhere in the script
            'Sydney': {
                'sun': {11: 235.6, 5: 165}, #december, june
                'record high C': {0: 45.8}, #january
                'record low C': {3: 7}, #april
                'rain days': {5: 12.5},
                'rain mm': {8: 68.9}
            }
        }

        for city,data in known_data.items():
            actual_data = climate.get_climate_data(city)

            for key,key_data in data.items():
                for month,expected_value in key_data.items():
                    self.assertEqual(actual_data[key][month], expected_value)

class climate_cache_test(unittest.TestCase):
    def test_cache_create(self):
        """ Really basic test: get a page, then check if it is 
        reported as having cache available. """

        climate.get_climate_data('Melbourne')
        self.assertEqual(cache.exists('Melbourne'), True)

    def test_cache_timing(self):
        """ Bit of a wonky test: test actual caching by comparing time
        to load a page uncached and time to load it cached. The latter
        should be shorter.
        Might fail with a false negative if filesystem is being slow 
        at the moment, but in general it should work pretty well. """

        page = 'Melbourne'
        cache.clear(page)

        time1 = time.time()
        climate.get_climate_data(page)
        time_with_no_cache = time.time() - time1

        time2 = time.time()
        climate.get_climate_data(page)
        time_with_cache = time.time() - time2

        self.assertTrue(time_with_cache < time_with_no_cache)

    def test_cache_timeout(self):
        """ Make sure files older than 7 days are treated as not valid
        for cache purposes. Fake this with changing a file's 
        modified time with os.utime() """

        page = 'Melbourne'

        climate.get_climate_data(page)
        self.assertEqual(cache.exists(page), True)

        # cache.get_file_name should really be treated as private
        # most of the time, but for the purposes of the test 
        # it's OK to use it I guess
        file_name = cache.get_file_name(page)

        # set new filetime to (max cache age + 1 day) ago
        new_file_datetime = datetime.now() - \
            timedelta(cache.CACHE_PERIOD_DAYS + 1, 0)
        new_file_timestamp = time.mktime(new_file_datetime.timetuple())

        # use the new timestamp as both access time and modify time
        os.utime(file_name, (new_file_timestamp, new_file_timestamp))

        # assert it's now reported as not cacheable
        self.assertEqual(cache.exists(page), False)

    def test_cache_clear(self):
        """ Test cache clearing by downloading a page (and thus 
        creating the cached version), then asking for it to be cleared,
        and checking if the file still exists """

        # download a test page first - make sure it is cached
        climate.get_climate_data('Melbourne')

        # clear, and see if it reports successful
        paths = cache.clear('Melbourne')
        self.assertEqual(cache.exists('Melbourne'), False)

        # check if file physically exists
        for path in paths:
            self.assertFalse(os.path.exists(path))

    def test_cache_clear_all(self):
        """ Test cache clearing by downloading a page (and thus 
        creating the cached version), then asking for everything 
        to be cleared, and checking if files reported exist """
        # download a test page first - make sure it is cached
        climate.get_climate_data('Melbourne')

        paths = cache.clear_all()

        # see if it self-reports successful for the test page
        self.assertEquals(cache.exists('Melbourne'), False)

        # check if files physically exists
        for path in paths:
            self.assertFalse(os.path.exists(path))


if __name__ == '__main__':
    unittest.main()


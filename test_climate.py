#!/usr/bin/env python
# coding=utf-8

from __future__ import unicode_literals
import unittest
import climate

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
		self.assertEqual(data['high'][0], 18.6)
		self.assertEqual(data['record low'][11], 4.3)

	def test_known_data(self):
		"""Test for correct retrieval of some data for some cities.
		Test against known-correct values retrieved via browser at time
		of test authoring.
		Basically make sure future changes don't mess up known-working
		queries."""

		known_data = {
			'Vancouver': {
				'record high': {6: 31.7}, #july
				'mean': {9: 11.1}, #october
				'precipitation mm': {7: 50.8} #august
			},
			'Seattle': {
				# temperatures here also test conversion into C
				'high': {3: 14.5}, #april
				'record low': {1: -17.2, 7: 6.7}, #feb, aug
				'precipitation days': {10: 18.4}, #november
				'sun': {7: 248} #august
				# TODO: test for conversion in -> cm/mm
			},
			'Calgary': {
				'snow cm': {2: 21.9}, #march
				'sun': {6: 314.9}, #july
				'mean': {4: 9.8}, #may
				'low': {10: -8.9}, #november
				'record low': {1: -45} #february
			},
			'Melbourne': {
				'record high': {1: 46.4}, #february
				'record low': {6: -2.8}, #july
				'sun': {5: 108}, #june
			},
			'Toronto': {
				'mean': {6: 22.2}, #july
				'snow days': {0: 12.0, 4: 0}, #january, may
				'record low': {11: -30}, #december
				'rain mm': {7: 79.6}, #august
				'sun': {4: 229.1} #may
			},
			# for Sydney, test conversion from daily sun hours, as
			# specified on wiki page, into monthly hours, as used
			# elsewhere in the script
			'Sydney': {
				'sun': {11: 235.6, 5: 165}, #december, june
				'record high': {0: 45.8}, #january
				'record low': {3: 7}, #april
				'rain days': {5: 12.5},
				'rain mm': {8: 68.9}
			}
		}

		for city,data in known_data.items():
			actual_data = climate.get_climate_data(city)

			for key,key_data in data.items():
				for month,expected_value in key_data.items():
					self.assertEqual(
						actual_data[key][month],
						expected_value)


if __name__ == '__main__':
	unittest.main()

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

	# TODO: test with some known data
	# (Vancouver, Toronto, Calgary, Melbourne, etc)
	# to make sure future changes don't mess up known-working 
	# queries
	
if __name__ == '__main__':
	unittest.main()

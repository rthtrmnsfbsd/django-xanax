# -*- coding: utf-8 -*-
from django.test import TestCase

from xanax.templatetags.xanax_tags import preview_token

class SimpleTest(TestCase):

    def setUp(self):
        pass

    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

    def test_xanax_tags_preview_token_empty(self):
        """
        Tests that if in template context doe's not exist preview_token
        variable template tag preview_token render empty string
        """
        context = {}

        self.assertEqual(preview_token(context), '')


    def test_xanax_tags_preview_token_data(self):
        """
        Tests that if in template context has preview_token
        variable template tag preview_token render hidden form field
        """
        context = {'preview_token':'heipghoiesruhgoaeiblig'
                                    +'feitfgqweroifgqeruofgqweofg'}
        result = u"<div style='display:none'>" \
                 + u"<input type='hidden' name='preview_token' " \
                 + u"value='heipghoiesruhgoaeibligfeit" \
                 + u"fgqweroifgqeruofgqweofg' /></div>"

        self.assertEqual(preview_token(context), result)

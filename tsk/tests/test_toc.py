# coding=utf8
import unittest 
import mock
import StringIO

from tsk.toc import TOC

# TODO change tests to match the new logic
@mock.patch('__builtin__.open')
class Skip_TOC(unittest.TestCase):
    @property
    def _toc_contents(self):
        return """
---
indent_spacing: 4
bullet_characters: -*+
page_level: 1
---

Chapter 1
    sublevel 1.1
    sublevel 1.2
        sub-sublevel 1.2.1
    sublevel 1.3

Chapter 2
    sublevel 2.1
        sub-sublevel 2.1.1
            sub-sub-sublevel 2.1.1.1
    sublevel 2.2"""

    def test_toc_mapper_understands_toc_hierarchy(self, mk_open):
        mk_open.return_value.__enter__.return_value = StringIO.StringIO(
            self._toc_contents)
        toc = TOC(None, '')
        #with mock.patch.object(toc, 'page_exists', lambda self: True):
        toc.generate()
        root = toc.toc
        chapter_1 = toc(0)
        self.assertEqual(root['level'], -1)
        self.assertEqual(chapter_1['hierarchy'], [1,0,0,0,0])
        self.assertEqual(toc(0,0)['hierarchy'], [1,1,0,0,0])
        self.assertEqual(toc(0,1)['hierarchy'], [1,2,0,0,0])
        self.assertEqual(toc(0,1,0)['hierarchy'], [1,2,1,0,0])
        self.assertEqual(toc(1)['hierarchy'], [2,0,0,0,0])
        self.assertEqual(toc(1,0)['hierarchy'], [2,1,0,0,0])

    #TODO: test_toc_mapper_raises_error_when_hierarchy_is_missing_a_level()

    def test_toc_url_present_if_page_exists(self, mk_open):
        mk_open.return_value.__enter__.return_value = StringIO.StringIO(
            self._toc_contents)
        toc = TOC(None, '')
        with mock.patch.object(toc, 'page_exists', lambda self: True):
            toc.generate()
            self.assertEqual(toc(0)['url'], 'chapter-1.html')

    def test_toc_url_missing_if_page_missing(self, mk_open):
        mk_open.return_value.__enter__.return_value = StringIO.StringIO(
            self._toc_contents)
        toc = TOC(None, '')
        with mock.patch.object(toc, 'page_exists', lambda self: False):
            toc.generate()
            self.assertTrue(toc(0)['url'] is None)
            self.assertTrue(toc(1)['url'] is None) 

    def test_toc_url_points_to_page_for_levels_below_bookmark(self, mk_open):
        mk_open.return_value.__enter__.return_value = StringIO.StringIO(
            self._toc_contents)
        toc = TOC(None, '')
        with mock.patch.object(toc, 'page_exists', lambda self: True):
            toc.generate()
            self.assertEqual(toc(0)['url'], 'chapter-1.html')
            self.assertEqual(toc(0,0)['url'], 'sublevel-1-1.html')
            self.assertEqual(toc(1,1)['url'], 'sublevel-2-2.html')

    def test_toc_url_points_to_upper_level_page_url_for_levels_at_or_above_bookmark(
            self, mk_open):
        mk_open.return_value.__enter__.return_value = StringIO.StringIO(
            self._toc_contents)
        toc = TOC(None, '')
        with mock.patch.object(toc, 'page_exists', lambda self: True):
            toc.generate()
            self.assertEqual(toc(0,1,0)['url'], 'sublevel-1-2.html')
            self.assertEqual(toc(1,0,0,0)['url'], 'sublevel-2-1.html')
    ##TODO: 
    # test for toc unicode support
    # test for toc level_type
    # test for toc comments
    # test slugify replaces ampersand with `and`
    # test children

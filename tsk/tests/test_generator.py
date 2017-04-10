# coding=utf8
import unittest 
import mock
import StringIO

import jinja2

from tsk.generator import slugify, Generator, TskError, TOC, markdown

class GeneratorTest(unittest.TestCase):

    def setUp(self):
        super(GeneratorTest, self).setUp()
        self.config = dict(
            MARKDOWN_PATH='./markdown',
            TEMPLATE_PATH='./templates',
            DEFAULT_TEMPLATE='main.html',
            MARKDOWN_OUTPUT_DIR='./templates/pages',
            WEB_PAGES_PATH='./website',
        )

    def test_required_configs_must_be_set(self): 
        # TEMPLATE_PATH should be set
        config = self.config.copy()
        config.pop('TEMPLATE_PATH')
        with self.assertRaises(TskError) as a:
            Generator(config)
            self.assertTrue(str(a.exception).startswith('TEMPLATE_PATH must'))

        # MARKDOWN_PATH should be set
        config = self.config.copy()
        config.pop('MARKDOWN_PATH')
        with self.assertRaises(TskError) as a:
            Generator(config)
            self.assertTrue(str(a.exception).startswith('MARKDOWN_PATH must'))

        # DEFAULT_TEMPLATE should be set
        config = self.config.copy()
        config.pop('DEFAULT_TEMPLATE')
        with self.assertRaises(TskError) as a:
            Generator(config)
            self.assertTrue(str(a.exception).startswith(
                'DEFAULT_TEMPLATE must'))

        # WEB_PAGES_PATH should be set
        config = self.config.copy()
        config.pop('WEB_PAGES_PATH')
        with self.assertRaises(TskError) as a:
            Generator(config)
            self.assertTrue(str(a.exception).startswith('WEB_PAGES_PATH must'))

        # MARKDOWN_OUTPUT_DIR should be set
        config = self.config.copy()
        config.pop('MARKDOWN_OUTPUT_DIR')
        with self.assertRaises(TskError) as a:
            Generator(config)
            self.assertTrue(str(a.exception).startswith('MARKDOWN_OUTPUT_DIR must'))

        # all required configs set
        Generator(self.config)

    @mock.patch('tsk.generator.Environment')
    def test_jinja_environment_instance_created(self, Environ):
        g = Generator(self.config)
        Environ.assert_called_once()
        # assert instance of jinja2.FileSystemLoader
        self.assertTrue(isinstance(Environ.call_args[1]['loader'], 
                                   jinja2.FileSystemLoader))

    def test_markdown_rendering_invokes_convert_method_of_Markdown(self):
        markdown_text = 'some markdown text'
        original_convert = markdown.Markdown.convert
        # purpose of this wrapper is to grab a reference to `self` to use later
        # in assert
        def side_effect(self, *args, **kwargs):
            side_effect.self = self
            return original_convert(self, *args, **kwargs)
        with mock.patch.object(
                # we need `autospec=True` to ensure that mock `convert`
                # passes `self` to underlying side_effect
                markdown.Markdown, 'convert', autospec=True,
                side_effect=side_effect) as mkconvert:
            g = Generator(self.config)
            g.render_markdown(markdown_text)
            mkconvert.assert_called_once_with(side_effect.self, markdown_text)

    @mock.patch('__builtin__.open')
    def test_processing_markdown_should_write_contents_output(self, mock_open):
        data = 'some data'
        mock_file = mock_open.return_value
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = data
        g = Generator(self.config)
        file = 'some.md'
        with mock.patch.object(g, 'write_output') as mock_write:
            g.process_markdown_file(file)

    def test_markdown_rendering_should_return_a_meta_dict(self):
        markdown_text = '---\nvar1: abc\nvar2: xyz\n---\n\nsome markdown text'
        g = Generator(self.config)
        contents, meta = g.render_markdown(markdown_text)
        self.assertTrue(isinstance(meta,dict))

    def test_markdown_rendering_populates_instance_with_meta_data(self):
        markdown_text = '---\nvar1: abc\nvar2: xyz\n---\n\nsome markdown text'
        g = Generator(self.config)
        contents, meta = g.render_markdown(markdown_text)
        self.assertEqual(meta['var1'], 'abc')
        self.assertEqual(meta['var2'], 'xyz')

    @mock.patch('tsk.generator.Generator.exec_command')
    def test_dollar_signed_commands_extracted_from_markdown(
            self, mock_exec_command):
        command = 'some_random_cmd'
        text = 'Lorem blabla \n$${}\nIpsum etc'.format(command)
        g = Generator(self.config)
        g.process_foreign_commands(text)
        mock_exec_command.assert_called_once_with(command, [])

    def test_rendering_jinja_template_calls_get_template_method(self):
        g = Generator(self.config)
        with mock.patch.object(g.jinja_environ, 'get_template') as mk_gtmp:
            g.render_jinja_template(None, template='abc')
            mk_gtmp.assert_called_once_with('abc')

    def test_rendering_jinja_template_calls_template_render_method(self):
        g = Generator(self.config)
        with mock.patch.object(g.jinja_environ, 'get_template') as mk_gtmp:
            g.render_jinja_template('xyz', template='abc', data='data')
            template = mk_gtmp.return_value
            template.render.assert_called_once_with(
                contents='xyz', data='data', toc=None)

    @mock.patch('tsk.generator.os.listdir')
    @mock.patch('tsk.generator.os.path.isfile')
    def test_when_traversing_dir_works_with_file_with_dir_prefix(
            self, mk_isfile, mk_listdir):
        mk_listdir.return_value = ['a.md', 'b.md']
        mk_isfile.return_value = True
        g = Generator(self.config)
        [yv for yv in g.traverse_markdown_dir()]
        mk_isfile.assert_any_call(g.MARKDOWN_PATH+'/'+'a.md') 
        mk_isfile.assert_any_call(g.MARKDOWN_PATH+'/'+'b.md')

    @mock.patch('tsk.generator.os.listdir')
    @mock.patch('tsk.generator.os.path.isfile')
    def test_file_checked_for_md_extension(self, mk_isfile, mk_listdir):
        mk_listdir.return_value = ['a.md', 'b.ist', 'c.md', 'd.txt']
        mk_isfile.return_value = True
        g = Generator(self.config)
        yield_values = [yv[-4:] for yv in g.traverse_markdown_dir()]
        self.assertEqual(yield_values, ['a.md', 'c.md'])

        mk_listdir.return_value = ['somefile.htm', 'etc.txt']
        yield_values = [yv for yv in g.traverse_markdown_dir()]
        self.assertEqual(yield_values, [])

    @mock.patch('__builtin__.open')
    def test_markdown_output_filename_prepended_with_path(self, mk_open):
        mk_open.return_value.__enter__.return_value = mk_open.return_value
        mk_open.return_value.read.return_value = """
        output_file: somefile.html
        """
        g = Generator(self.config)
        with mock.patch.object(g, 'write_output'):
            g.process_markdown_file('somefile.md')
        meta = g.book.pop()
        self.assertTrue(meta['output_path'].startswith(
            self.config['MARKDOWN_OUTPUT_DIR']+'/'))

    def test_markdown_output_filename_1st_fallback_should_be_doc_title(self):
        g = Generator(self.config)
        meta = dict(title='Éléphants sur une Île!',
                    input_file='elephants-sur-deux-iles.md')
        filename = g._markdown_output_filename(meta)
        self.assertTrue(
            filename.endswith('elephants-sur-une-ile.html'))

    def test_markdown_output_filename_2nd_fallback_should_be_md_filename(self):
        g = Generator(self.config)
        meta = dict(input_file='elephants-sur-deux-iles.md')
        filename = g._markdown_output_filename(meta)
        self.assertTrue(
            filename.endswith('elephants-sur-deux-iles.html'))

    def test_slugify_function_translits_title(self):
        g = Generator(self.config)
        text = u'Sömétîmès thȩ wôrld wêéps fÔr thÈß'
        slug = u'sometimes-the-world-weeps-for-thess'
        self.assertEqual(slugify(text), slug)

    def test_slugify_function_replaces_ampersand_with_and(self):
        text = u'Agnes & Tovi'
        slug = u'agnes-and-tovi'
        self.assertEqual(slugify(text), slug)

    @mock.patch('__builtin__.open')
    def test_write_output_should_work_with_binary_strings(self, mk_open):
        mk_open.return_value.__enter__.return_value = mk_open.return_value
        g = Generator(self.config)
        bin_str = u'some unicode string éà'.encode('utf8')
        g.write_output(None, bin_str)
        mk_open.return_value.write.assert_called_with(bin_str)
        bin_str = u'some unicode string éà'.encode('latin1')
        g.write_output(None, bin_str)
        mk_open.return_value.write.assert_called_with(bin_str)

    @mock.patch('__builtin__.open')
    def test_write_output_should_work_with_unicode_strings(self, mk_open):
        mk_open.return_value.__enter__.return_value = mk_open.return_value
        g = Generator(self.config)
        uc_str = u'some unicode string éà'
        g.write_output(None, uc_str)

    def test_markdown_render_should_work_with_unicode_strings(self):
        uc_str = u'some unicode string éà'
        g = Generator(self.config)
        html, meta = g.render_markdown(uc_str)
        self.assertTrue('some unicode' in html)

    def test_markdown_render_should_work_with_utf8_strings(self):
        bin_str = u'some unicode string éà'.encode('utf8')
        g = Generator(self.config)
        html, meta = g.render_markdown(bin_str)
        self.assertTrue('some unicode' in html)

    def test_markdown_render_should_raise_err_with_non_utf8_bin_strings(self):
        bin_str = u'some unicode string éà'.encode('latin1')
        g = Generator(self.config)
        with self.assertRaises(UnicodeDecodeError) as a:
            g.render_markdown(bin_str)
        err_msg = '{!r} codec can\'t'.format('utf8')
        self.assertTrue(str(a.exception).startswith(err_msg))

    @property
    def _toc_content(self):
        return """
        # Chapter 1
        ## sublevel 1.1
        ## sublevel 1.2
        ### sub-sublevel 1.2.1
        ## sublevel 1.3

        # Chapter 2
        ### sub-sublevel 2.0.1
        ## sublevel 2.1
        ### sub-sublevel 2.1.1
        #### sub-sub-sublevel 2.1.1.1
        ## sublevel 2.2
        """

    #def test_toc_mapper_understands_toc_hierarchy(self):
    #    g = Generator(self.config)
    #    toc = g.toc_map(self._toc_content)
    #    self.assertEqual(toc[0]['level'], [1,0,0,0,0])
    #    self.assertEqual(toc[1]['level'], [1,1,0,0,0])
    #    self.assertEqual(toc[5]['level'], [2,0,0,0,0])
    #    self.assertEqual(toc[6]['level'], [2,0,1,0,0])
    #    self.assertEqual(toc[7]['level'], [2,1,0,0,0])

    #def test_toc_url_present_if_page_exists(self):
    #    g = Generator(self.config)
    #    with mock.patch.object(g, '_page_exists', lambda self: True):
    #        toc = g.toc_map(self._toc_content)
    #        self.assertEqual(toc[0]['url'], 'chapter-1.html')

    #def test_toc_url_missing_if_page_missing(self):
    #    g = Generator(self.config)
    #    toc = g.toc_map(self._toc_content)
    #    self.assertTrue(toc[0]['url'] is None)
    #    self.assertTrue(toc[6]['url'] is None) 
    #    self.assertTrue(toc[7]['url'] is None)

    #def test_toc_url_points_to_page_for_levels_below_bookmark(self):
    #    g = Generator(self.config)
    #    with mock.patch.object(g, '_page_exists', lambda self: True):
    #        toc = g.toc_map(self._toc_content)
    #        self.assertEqual(toc[0]['url'], 'chapter-1.html')
    #        self.assertEqual(toc[1]['url'], 'sublevel-1-1.html')
    #        self.assertEqual(toc[10]['url'], 'sublevel-2-2.html')

    #def test_toc_url_points_to_anchor_for_levels_at_or_above_bookmark(self):
    #    g = Generator(self.config)
    #    with mock.patch.object(g, '_page_exists', lambda self: True):
    #        toc = g.toc_map(self._toc_content)
    #        self.assertEqual(toc[3]['url'], 
    #                         'sublevel-1-2.html#sub-sublevel-1-2-1')
    #        self.assertEqual(toc[6]['url'], 
    #                        'chapter-2.html#sub-sublevel-2-0-1')
    #        self.assertEqual(toc[9]['url'], 
    #                        'sublevel-2-1.html#sub-sub-sublevel-2-1-1-1')

    #TODO:
    # test_command_registered_with_provided_name()
    # test_command_registered_with_name_of_function_when_no_name_provided()
    # test_command_registration_checks_for_name_collision()
    # test_registered_command_is_bound_when_flag_active()
    # test_registered_command_is_force_bound_when_instructed()
    # test_command_registered_with_prefix
    # test_partial_input_directory_created_under_markdown_if_non_existent()

    # test_include_command

     


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

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

    def test_markdown_preprocessing_should_return_a_meta_dict(self):
        markdown_text = '---\nvar1: abc\nvar2: xyz\n---\n\nsome markdown text'
        g = Generator(self.config)
        meta, contents = g.preprocess_markdown(markdown_text)
        self.assertTrue(isinstance(meta,dict))

    def test_markdown_preprocessing_populates_instance_with_meta_data(self):
        markdown_text = '---\nvar1: abc\nvar2: xyz\n---\n\nsome markdown text'
        g = Generator(self.config)
        meta, contents = g.preprocess_markdown(markdown_text)
        self.assertEqual(meta['var1'], 'abc')
        self.assertEqual(meta['var2'], 'xyz')

    @mock.patch('tsk.generator.Generator.exec_command')
    def test_dollar_signed_commands_extracted_from_markdown(
            self, mock_exec_command):
        command = 'some_random_cmd'
        text = 'Lorem blabla \n$${}\nIpsum etc'.format(command)
        g = Generator(self.config)
        g.preprocess_markdown(text)
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
                contents_template='xyz', data='data', toc=None)

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

        meta = g.book.pop('somefile.html')
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
        html = g.render_markdown(uc_str)
        self.assertTrue('some unicode' in html)

    def test_markdown_render_should_work_with_utf8_strings(self):
        bin_str = u'some unicode string éà'.encode('utf8')
        g = Generator(self.config)
        html = g.render_markdown(bin_str)
        self.assertTrue('some unicode' in html)

    def test_markdown_render_should_raise_err_with_non_utf8_bin_strings(self):
        bin_str = u'some unicode string éà'.encode('latin1')
        g = Generator(self.config)
        with self.assertRaises(UnicodeDecodeError) as a:
            g.render_markdown(bin_str)
        err_msg = '{!r} codec can\'t'.format('utf8')
        self.assertTrue(str(a.exception).startswith(err_msg))

    def test_markdown_meta_tokenization(self):
        g = Generator(self.config)
        meta = "some tokens, in this, string"
        tokens = g._tokenize_meta(meta)
        self.assertEqual(tokens, ['some tokens', 'in this', 'string'])
        meta = "some \\ \\\\ \, tokens, in this, string"
        tokens = g._tokenize_meta(meta)
        self.assertEqual(tokens, ['some \\ \\\\ , tokens', 'in this', 'string'])

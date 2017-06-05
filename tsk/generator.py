# coding=utf8
import os
import shutil
import re
import StringIO

import markdown
from jinja2 import Environment, FileSystemLoader

from .utils import slugify, TskError, basename_no_ext
from .toc import TOC

"""
TODO:

handling navigation
-------------------
- navigation should be based on the presence of a file toc.md
- if the toc.md isn't present, skip navigation.
- a mapping of the toc should be created with slugified titles as keys
- if a file matching the key exists an url should be created

anchors
-------
- a command to add an anchor to headings should be created

"""

def bound_command(command):
    """
    add a flag to the user-defined command to specify if it should
    be executed as a generator-bound method or as a simple function.
    useful if the function expects the generator as `self` in its signature.
    """
    command.force_bound = True
    return command

@bound_command
def tsk_command_include(self, item):
    """
    include html partials in the markdown.
    e.g. for html graphs and tables.

        `$$ include distribution-chart.html` 

    """
    item_path = os.path.join(self.MARKDOWN_PATH, 'partials', item)
    partial_output_dir = os.path.join(self.TEMPLATE_PATH, 'partials')
    if not os.path.exists(partial_output_dir):
        os.makedirs(partial_output_dir)
    item_output_path = os.path.join(partial_output_dir, item)
    #TODO: copy item to the partials directory
    try:
        shutil.copy(item_path, item_output_path)
        return "{{% include 'partials/{item}' %}}".format(item=item)
    except:
        return "[ ... ]"

@bound_command
def tsk_command_anchor(self, *items):
    """
    include an anchor to the markdown template.
    e.g.

        `$$ anchor put an in-page anchor here` 

    """
    anchor = slugify(' '.join(items))
    return '<p><a id="{anchor}"></a></p>'.format(anchor=anchor)

class Generator(object):

    TSK_COMMAND_PREFIX = 'tsk_command_'

    def __init__(self, config):
        for k, v in config.iteritems():
            setattr(self, k, v)
        # check for must-have configs
        for c in ['TEMPLATE_PATH', 'MARKDOWN_PATH', 'DEFAULT_TEMPLATE',
                  'WEB_PAGES_PATH', 'MARKDOWN_OUTPUT_DIR']:
            try:
                a = getattr(self, c)
            except AttributeError as e:
                raise TskError('{} must be set.'.format(c))

        markdown_partials = os.path.join(self.MARKDOWN_PATH, 'partials')
        if not os.path.exists(markdown_partials):
            os.makedirs(os.path.join(self.MARKDOWN_PATH, 'partials'))

        self.jinja_environ = Environment(
            loader=FileSystemLoader(self.TEMPLATE_PATH),
            #lstrip_blocks=True,
            #trim_blocks=True
        )

        # registery linking input and output names for markdown files
        self.book = {}

    def _markdown_output_filename(self, meta):
        output_file = meta.get('output_file', None)
        if not output_file: 
            if meta.get('title', None):
                output_file = slugify(meta['title']) + '.html'
            else:
                output_file = basename_no_ext(meta['input_file']) + '.html'
        return output_file

    def traverse_markdown_dir(self):
        for f in os.listdir(self.MARKDOWN_PATH):
            f = os.path.join(self.MARKDOWN_PATH, f)
            if f!= self.TOC_FILE and f.endswith('.md') and os.path.isfile(f):
                yield f

    def write_output(self, file, data):
        try:
            data = data.encode('utf8')
        except UnicodeDecodeError as e:
            pass
        with open(file, 'w') as f:
            f.write(data)

    def process_markdown_file(self, filename):
        with open(filename, 'r') as f:
            meta, contents = self.preprocess_markdown(f.read())
            contents = self.render_markdown(contents)
            meta['input_file'] = os.path.basename(filename)
            meta['output_file'] = self._markdown_output_filename(meta)
            meta['output_path'] = os.path.join(self.MARKDOWN_OUTPUT_DIR, 
                                               meta['output_file'])
            self.write_output(meta['output_path'], contents)
            self.book[meta['output_file']] = meta

    # TODO: testing
    def preprocess_markdown(self, text):
        """
        receive custom/extended markdown, extract meta information, run
        user-defined commands and return meta dict and standard markdown.
        """
        meta = {}
        meta_mode = False
        comment_mode = False
        md = ''
        for line in StringIO.StringIO(text).readlines():
            l = line.strip()

            if l=='-/-':
                comment_mode = not comment_mode

            if comment_mode:
                # skip processing
                continue

            if l=='---': 
                # toggle meta_mode and move on to the next instruction
                meta_mode = not meta_mode
                continue

            if meta_mode:
                # process meta data
                meta_key, meta_value = self._process_meta_line(l)
                meta[meta_key] = meta_value

            elif l.startswith('$$'):
                args = l[2:].strip().split()
                command = args.pop(0)
                md += self.exec_command(command, args)
            else:
                md += line

        return meta, md 

    def _process_meta_line(self, line):
        # if in meta_mode we grab each key value pair
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip().split(',')
        if len(value)==1:
            value = value[0]
        try:
            # attempt int casting
            value = int(value)
        except ValueError:
            pass
        return key, value
    
    def register_command(self, command, name=None, bound=False):
        """
        extends markdown with user-defined commands.
        """
        if name is None:
            name = command.__name__
        if not name.startswith(self.TSK_COMMAND_PREFIX):
            name = self.TSK_COMMAND_PREFIX + name
        if hasattr(self, name):
            raise NameError('This command name is already in use. '
                                 'Register with a different name.')
        if bound or command.force_bound:
            command = command.__get__(self, type(self))
        setattr(self, name, command)

    def exec_command(self, command, args=None):
        """
        execute user-defined commands in markdown
        """
        if not command.startswith(self.TSK_COMMAND_PREFIX):
            command = self.TSK_COMMAND_PREFIX + command
        if args is None:
            args = []
        command = getattr(self, command)
        if command:
            return command(*args)
        raise NameError('No command registered with that name.')

    def render_markdown(self, text):
        try:
            text = text.decode('utf8')
        except UnicodeEncodeError as e: # in case string is already unicode
            pass
         
        # small hack to allow the meta extension to see the markers
        # text = re.sub(r'^\+\+\+\s*$', '---', text, flags=re.M)
        # end of hack
        md = markdown.Markdown(output_format='html5')
        html = md.convert(text)
        meta_dict = {k:v for k,v in md.Meta.iteritems() if v}
        meta = {}
        #meta = type('anon', (object,), {})
        for k,v in meta_dict.iteritems():
            if len(v)==1:
                meta[k] = v[0]
            else:
                meta[k] = v
        return html, meta

    def render_jinja_template(self, contents_template, template=None, 
                              data=None, toc=None):
        template = template or self.DEFAULT_TEMPLATE
        template = self.jinja_environ.get_template(template)
        rv = template.render(contents_template=contents_template, data=data,
                             toc=toc)
        return rv

    def process_markdown(self):
        """ 
        Process and output markdown 
        """
        for filename in self.traverse_markdown_dir():
            self.process_markdown_file(filename)

    @property
    def toc(self):
        if not getattr(self, '_toc', {}) and hasattr(self, 'TOC_FILE'):
            toc_file = os.path.join(self.MARKDOWN_PATH, self.TOC_FILE)
            t = TOC(toc_file, self.MARKDOWN_OUTPUT_DIR)
            t.generate()
            def _add_md_file(tocdata, bookdata):
                for p in tocdata['children']:
                    md_data = bookdata.get(p['url'], {})
                    md_file = md_data.get('input_file', None)
                    if md_file:
                        p['markdown'] = md_file
                    if p.get('children'):
                        _add_md_file(p, bookdata)
            if self.book:
                _add_md_file(t.toc, self.book)
            self._toc = t.toc
        return getattr(self, '_toc', {})

    def generate_webpages(self):
        """ 
        Insert book's content within template layout and generate static web
        pages. 
        """
        #if hasattr(self, 'TOC_FILE'):
        #    toc_file = os.path.join(self.MARKDOWN_PATH, self.TOC_FILE)
        #    toc = TOC(toc_file, self.MARKDOWN_OUTPUT_DIR)
        #    toc.generate()
        #    toc = toc.toc

        for k, page in self.book.iteritems():
            #with open(page['output_path'], 'r') as p:
            #    contents = p.read().decode('utf8')
            contents_template = 'pages/' + page['output_file']
            template = (page['template'] if page.get('template') 
                        else self.DEFAULT_TEMPLATE)
            output = self.render_jinja_template(
                contents_template=contents_template, 
                template=template, data=page, toc=self.toc)
            web_file = os.path.join(self.WEB_PAGES_PATH, page['output_file'])
            self.write_output(web_file, output)



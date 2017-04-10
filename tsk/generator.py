# coding=utf8
import os
import shutil
import re
import StringIO
import slugify as _slugify
import functools

import markdown
from jinja2 import Environment, FileSystemLoader

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

class TskError(Exception): pass

def basename_no_ext(file):
    return os.path.basename(os.path.splitext(file)[0])

def slugify(text):
    text = re.sub(r'&', 'and', text)
    return _slugify.slugify(text).lower()

def bound_command(command):
    command.force_bound = True
    return command

@bound_command
def tsk_command_include(self, item):
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
        raise
        return "[ ... ]"

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
        self.book = []

    def _markdown_output_filename(self, meta):
        output_file = meta.get('output_file', None)
        if not output_file: 
            if meta.get('title', None):
                output_file = slugify(meta['title']) + '.html'
            else:
                output_file = basename_no_ext(meta['input_file']) + '.html'
        #return os.path.join(self.MARKDOWN_OUTPUT_DIR, output_file)
        return output_file


    def traverse_markdown_dir(self):
        for f in os.listdir(self.MARKDOWN_PATH):
            f = os.path.join(self.MARKDOWN_PATH, f)
            if os.path.isfile(f) and f.endswith('.md'):
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
            contents = self.process_foreign_commands(f.read())
            contents, meta = self.render_markdown(contents)
            meta['input_file'] = filename
            meta['output_file'] = self._markdown_output_filename(meta)
            meta['output_path'] = os.path.join(self.MARKDOWN_OUTPUT_DIR, 
                                               meta['output_file'])
            self.write_output(meta['output_path'], contents)
            self.book.append(meta)
    
    def process_foreign_commands(self, text):
        rv = ''
        for line in StringIO.StringIO(text).readlines():
            l = line.strip()
            if l.startswith('$$'):
                args = l[2:].strip().split()
                command = args.pop(0)
                rv += self.exec_command(command, args)
            else:
                rv += line
        return rv

    def register_command(self, command, name=None, bound=False):
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
         
        md = markdown.Markdown(extensions=['meta'], output_format='html5')
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

    def generate_webpages(self):
        """ 
        Insert book's content within template layout and generate static web
        pages. 
        """
        if hasattr(self, 'TOC_FILE'):
            toc_file = os.path.join(self.MARKDOWN_PATH, self.TOC_FILE)
            toc = TOC(toc_file, self.MARKDOWN_OUTPUT_DIR)
            toc.generate()
            toc = toc.toc

        for page in self.book:
            #with open(page['output_path'], 'r') as p:
            #    contents = p.read().decode('utf8')
            contents_template = 'pages/' + page['output_file']
            template = (page['template'] if page.get('template') 
                        else self.DEFAULT_TEMPLATE)
            output = self.render_jinja_template(
                contents_template=contents_template, 
                template=template, data=page, toc=toc)
            web_file = os.path.join(self.WEB_PAGES_PATH, page['output_file'])
            self.write_output(web_file, output)

    def _page_exists(self, slug):
        filename = os.path.join(self.MARKDOWN_OUTPUT_DIR, slug+'.html')
        return os.path.isfile(filename)

    def toc_map(self, toc_content=None):
        """
        - navigation should be based on the presence of a file toc.md
        - if the toc.md isn't present, skip navigation.
        - a mapping of the toc should be created with slugified titles as keys
        - if a file matching the key exists an url should be created
        """
        toc = {}
        toc = []
        marker = '#' # heading_marker
        after_marker = re.compile(r'[^{}]'.format(marker))
        bookmark_level = 2
        page_url = '/'
        #levels = [marker * i for i in xrange(1, 6)]
        
        levels = [0 for i in xrange(5)]
        def _set_levels(current_level, levels):
            # increment current level
            levels[current_level] += 1
            # reset sublevels
            for i in xrange(len(levels)):
                if i > current_level:
                    levels[i] = 0

        for l in toc_content.splitlines():
            line = l.strip()
            if line.startswith(marker):
                match = after_marker.search(line)
                level = match.start()-1
                title = line[level+1:].strip()
                # first get the corresponding slug
                slug = slugify(title)
                chapter_toc = {} # toc.setdefault(slug, {})
                toc.append(chapter_toc)
                _set_levels(level, levels)
                chapter_toc['level'] = levels[:]
                chapter_toc['title'] = title.decode('utf8')
                chapter_toc['level_type'] = level
                # level 0 - 2 have a dedicated page
                if level >= bookmark_level:
                    if page_url:
                        chapter_toc['url'] = '#'.join([page_url, slug])
                    else:
                        chapter_toc['url'] = None
                else:
                    if self._page_exists(slug):
                        page_url = '{slug}.html'.format(slug=slug)
                    else:
                        page_url = None
                    chapter_toc['url'] = page_url
        return toc

class TOC(object):
    """
    - navigation should be based on the presence of a file toc.toc
    - a mapping of the toc should be created with slugified titles as keys
    - if a file matching the key exists an url should be created
    """

    def __init__(self, toc_file, page_dir):
        with open(toc_file) as f:
            self.toc_text = f.read()
        self.PAGE_DIR = page_dir
        self.meta = {}
        self.toc = []
        self.set_default_meta(self.meta)

    def set_default_meta(self, meta):
        meta.setdefault('indent_spacing', 4)
        meta.setdefault('bullet_characters', '-*+')
        meta.setdefault('page_level', 2)

    def page_exists(self, slug):
        filename = os.path.join(self.PAGE_DIR, slug+'.html')
        return os.path.isfile(filename)

    def process_meta(self, line):
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
        self.meta[key] = value

    def parse_line(self, line):
        space_indent = ' ' * self.meta['indent_spacing']
        m = re.search(r'[^\s\t]', line)
        text = line[m.start():] if m else line
        text = text.lstrip(self.meta['bullet_characters']).decode('utf8')
        indent = line[:m.start()] if m else ''
        indent = re.sub(r'\t', space_indent, indent)
        indent_level = len(re.findall(space_indent, indent))
        # new line with spaces instead of tabs at the beginning
        return indent_level, text

    def generate(self):
        meta_mode = False
        comment_mode = False
        hierarchy = [0 for i in xrange(5)]

        self.toc = root_entry = dict(children=[], level=-1, title='', url='',
                                     hierarchy=hierarchy[:], slug='')
        parent_entries = {root_entry['level']: root_entry}
        for line in self.toc_text.splitlines():
            if line.strip()=='-*-':
                comment_mode = not comment_mode

            if comment_mode:
                # skip processing
                continue

            if line.strip()=='---': 
                # toggle meta_mode and move on to the next instruction
                meta_mode = not meta_mode
                continue

            if meta_mode:
                # process meta data
                self.process_meta(line)
            else:
                # process toc entry
                level, title = self.parse_line(line)
                if not title: # skip line
                    continue
                entry = dict(level=level, title=title, children=[])
                self.process_entry(entry, hierarchy, parent_entries)

        self.toc['page_level'] = self.meta['page_level']

    def process_entry(self, entry, hierarchy, parent_entries):
        #def _empty_entry(level):
        #    h = hierarchy[:level] + [0 for xrange(level, len(hierarchy))]
        #    return dict(empty=True, level=level, children=[])
        def _set_hierarchy(entry, parent_entries, hierarchy):
            # increment current level
            current_level = entry['level']
            hierarchy[current_level] += 1
            parent_entries[current_level] = entry
            for i in xrange(-1, len(hierarchy)):
                # reset sublevels
                if i < current_level:
                    parent_entry = parent_entries[i]
                    if parent_entry is None:
                        raise TskError(
                            'Malformed TOC. Missing level to hierarchy.')
                        # parent_entry = parent_entry[i] = _empty_parent(i)
                if i > current_level:
                    hierarchy[i] = 0
                    parent_entries[i] = None

            return parent_entry, hierarchy[:]

        parent_entry, entry['hierarchy'] = _set_hierarchy(
            entry, parent_entries, hierarchy)

        parent_entry['children'].append(entry)
        # first get the corresponding slug
        entry['slug'] = slugify(entry['title'])

        if entry['level']<=self.meta['page_level']:
            if self.page_exists(entry['slug']):
                url = '{slug}.html'.format(slug=entry['slug'])
            else:
                url = None
            entry['url'] = url
        else:
            entry['url'] = parent_entry['url']

    # TODO: TEST
    def children(self, *tree):
        children = self.toc['children']
        for c in tree:
            child = children[c]
            children = child['children']
        return child

    def __call__(self, *args):
        return self.children(*args)

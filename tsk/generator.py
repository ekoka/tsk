# coding=utf8
import os
import re
import StringIO
import slugify

import markdown
from jinja2 import Environment, FileSystemLoader

# grab the markdown
# preprocess the markdown
# transform the markdown to html
# get the jinja template
# inject the html output in the template
# output the result to html
class TskError(Exception): pass

def basename_no_ext(file):
    return os.path.basename(os.path.splitext(file)[0])

class Generator(object):

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

        self.jinja_environ = Environment(
            loader=FileSystemLoader(self.TEMPLATE_PATH),
            #lstrip_blocks=True,
            #trim_blocks=True
        )

        self.book = []

    def process_markdown(self):
        for filename in self.traverse_markdown_dir():
            self.process_markdown_file(filename)

            # TODO: extract template name from meta
            # output = self.render_jinja_template(contents=contents, data=meta)
            #template = (meta['template_layout'] if meta.get('template_layout')
            #            else self.DEFAULT_TEMPLATE)
            #html_output = markdown.generate_html(template, contents, meta)

        # NOTE: do we want to be able to recursively get md files?
        #elif os.path.isdir(f):
        #    for inner_f in get_markdown(f):
        #        yield inner_f

    def _slugs_from_title(self, title):
        return slugify.slugify(title).lower()

    def _markdown_output_filename(self, meta):
        output_file = meta.get('output_file', None)
        if not output_file: 
            if meta.get('title', None):
                output_file = self._slugs_from_title(meta['title']) + '.html'
            else:
                output_file = basename_no_ext(meta['input_file']) + '.html'
        return os.path.join(self.MARKDOWN_OUTPUT_DIR, output_file)


    def traverse_markdown_dir(self):
        for f in os.listdir(self.MARKDOWN_PATH):
            f = os.path.join(self.MARKDOWN_PATH, f)
            if os.path.isfile(f) and f.endswith('.md'):
                yield f

    def write_output(self, file, data):
        with open(file, 'w') as f:
            f.write(data.encode('utf8'))

    def render_jinja_template(self, contents, template=None, data=None):
        template = template or self.DEFAULT_TEMPLATE
        template = self.jinja_environ.get_template(template)
        rv = template.render(contents=contents, data=data)
        return rv

    def process_markdown_file(self, filename):
        with open(filename, 'r') as f:
            contents = self.process_foreign_commands(f.read())
            contents, meta = self.render_markdown(contents)
            meta['input_file'] = filename
            meta['output_file'] = self._markdown_output_filename(meta)
            self.write_output(meta['output_file'], contents)
            self.book.append(meta)
    
    # --- markdown

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

    def exec_command(self, command, args):
        return getattr(self, command)(*args)

    def render_markdown(self, text):
        md = markdown.Markdown(extensions=['meta'], output_format='html5')
        html = md.convert(text.decode('utf8'))
        meta_dict = {k:v for k,v in md.Meta.iteritems() if v}
        meta = {}
        #meta = type('anon', (object,), {})
        for k,v in meta_dict.iteritems():
            if len(v)==1:
                meta[k] = v[0]
            else:
                meta[k] = v
        return html, meta

# coding=utf8
import os
import re

from .utils import slugify, TskError, basename_no_ext

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
        self.toc = {}
        self.set_default_meta(self.meta)

    def set_default_meta(self, meta):
        meta.setdefault('indent_spacing', 4)
        meta.setdefault('bullet_characters', '-*+')
        meta.setdefault('page_level', 1)

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
            if line.strip()=='+-+':
                comment_mode = not comment_mode

            if comment_mode:
                # skip processing
                continue

            if line.strip()=='+++': 
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

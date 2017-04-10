# Deprecated TOC logic
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

# TESTS
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

    


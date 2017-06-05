import os
import re

import slugify as _slugify

class TskError(Exception): pass

def slugify(text):
    text = re.sub(r'&', 'and', text)
    return _slugify.slugify(text).lower()

def basename_no_ext(file):
    return os.path.basename(os.path.splitext(file)[0])
